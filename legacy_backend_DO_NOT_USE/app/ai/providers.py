from google import genai
from google.genai.types import GenerateContentConfig, SafetySetting, HarmCategory, HarmBlockThreshold
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.config import settings
from app.models.specialist import Specialist
from app.ai.self_reflection import reflection_engine

logger = logging.getLogger(__name__)

class GeminiProvider:
    def __init__(self):
        try:
            # Універсальний підхід для уникнення помилок з HttpOptions
            self.client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options={'api_version': 'v1'}
            )
            self.gemini_available = True
            logger.info("✅ Gemini client initialized successfully")
        except Exception as e:
            self.gemini_available = False
            logger.error(f"❌ Gemini initialization failed: {e}")
            raise

    async def generate_response(
        self,
        message: str,
        history: list,
        role: str = "default",
        user_id: int = 0,
        db: AsyncSession = None
    ) -> dict:
        """Генерація відповіді з пошуком спеціалістів у БД"""

        # 1. AI Аналіз запиту
        # ✅ ВИПРАВЛЕНО: detect_niche → detect_service
        detected_service, confidence = reflection_engine.detect_service(message)
        user_intent = reflection_engine.classify_intent(message)
        anxiety_score = reflection_engine.calculate_anxiety_score(message)

        logger.info(f"🧠 AI Analysis: service={detected_service}, intent={user_intent.value}")
        response_mode = reflection_engine.get_response_mode(user_intent, anxiety_score)

        # 2. Пошук спеціалістів у базі даних
        top_specialists = []
        if db:
            try:
                result = await db.execute(
                    select(Specialist)
                    .where(
                        Specialist.project_id == settings.PROJECT_ID,
                        Specialist.service_type == detected_service,
                        Specialist.is_active == True,
                    )
                    .limit(3)
                )
                specs = result.scalars().all()
                
                # ✅ ВИПРАВЛЕНО: Мапінг полів для фронтенду
                # hourly_rate → rate, delivery_method → delivery
                top_specialists = [
                    {
                        "name": s.name,
                        "specialty": s.specialty,
                        "rate": s.hourly_rate,  # ✅ Ключ "rate" замість hourly_rate
                        "delivery": s.delivery_method,  # ✅ Ключ "delivery" замість delivery_method
                        "is_ai": getattr(s, "is_ai_powered", False)
                    }
                    for s in specs
                ]
            except Exception as e:
                logger.error(f"❌ DB search error: {e}")

        # 3. Генерація тексту через Gemini
        ai_text = await self._gemini_generate(
            message=message,
            history=history,
            service_type=detected_service,
            specialists=top_specialists
        )

        # 4. Формування смарт-лінка
        first_spec_name = top_specialists[0]["name"] if top_specialists else None
        smart_link = reflection_engine.generate_smart_link(
            detected_service,
            first_spec_name,
            response_mode
        )

        return {
            "text": ai_text,
            "status": "success",
            "metadata": {
                "detected_service": detected_service,
                "confidence": confidence,
                "user_intent": user_intent.value,
                "anxiety_score": anxiety_score,
                "response_mode": response_mode.value,
                "smart_link": smart_link,
                "top_specialists": top_specialists,
                "show_buttons": bool(top_specialists)
            }
        }

    async def _gemini_generate(self, message: str, history: list, service_type: str, specialists: list) -> str:
        """Внутрішній метод генерації тексту"""

        service_names = {
            "healer": "енергопрактиків та цілителів",
            "coach": "коучів",
            "3d_modeling": "3D-моделерів",
            "interior_design": "дизайнерів інтер'єрів",
            "graphic_design": "графічних дизайнерів",
            "ui_ux_design": "UI/UX-дизайнерів",
            "web_development": "веб-розробників",
            "ai_automation": "експертів з AI",
            "mobile_development": "розробників мобільних додатків",
            "teacher_math": "вчителів математики",
            "teacher_ukrainian": "вчителів української мови",
            "teacher_english": "репетиторів англійської мови",
            "smm": "SMM-спеціалістів",
            "copywriting": "копірайтерів",
            "seo": "SEO-експертів",
            "video_editing": "відеомонтажерів",
            "photo_editing": "ретушерів фото"
        }
        readable_service = service_names.get(service_type, "фахівців")

        role_prompts = {
            "healer": "Ти — емпатичний духовний цілитель🧘‍♀️. Твоя мова спокійна, тепла.",
            "coach": "Ти — досвідчений коуч 🌱. Допомагай ставити цілі.",
            "teacher_math": "Ти — терплячий вчитель математики 📐. Пояснюй складне просто.",
            "teacher_ukrainian": "Ти — вишуканий вчитель української мови ✍️.",
            "teacher_english": "Ти — професійний викладач англійської мови 🇬🇧.",
            "ai_automation": "Ти — технічний архітектор AI-рішень 🤖.",
            "web_development": "Ти — досвідчений веб-розробник 💻.",
            "3d_modeling": "Ти — креативний 3D-художник 🎨.",
            "interior_design": "Ти — талановитий дизайнер інтер'єрів 🏡.",
            "smm": "Ти — експерт з SMM 📱.",
            "copywriting": "Ти — майстер текстів ✍️.",
            "default": "Ти — дружній асистент платформи Healer Nexus 🌟."
        }
        system_instruction = role_prompts.get(service_type, role_prompts["default"])

        safety_settings = [
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
        ]

        # Build Gemini contents: support both "content" (DB) and "text" (API) fields
        contents = []
        if history:
            for msg in history[-8:]:
                if not isinstance(msg, dict):
                    continue
                text = msg.get("text") or msg.get("content") or ""
                raw_role = (msg.get("role") or "").lower()
                role = "model" if raw_role in ("assistant", "bot") else "user"
                contents.append({"role": role, "parts": [{"text": text}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-1.5-flash",
                contents=contents,
                config=GenerateContentConfig(
                    system_instruction=system_instruction,
                    safety_settings=safety_settings,
                    temperature=0.75,
                    max_output_tokens=600,
                )
            )
            return response.text.strip() if response.text else f"Я знайшов для вас {readable_service}."
        except Exception as e:
            logger.error(f"❌ Gemini Error: {e}")
            return f"Ось найкращі {readable_service} для вашого запиту 👇"

def get_ai_provider():
    return GeminiProvider()
