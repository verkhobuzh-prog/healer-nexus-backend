from google import genai
from google.genai.types import GenerateContentConfig, SafetySetting, HarmCategory, HarmBlockThreshold
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.config import settings
from app.models.specialist import Specialist
from app.ai.self_reflection import reflection_engine  # FIXED: Import

logger = logging.getLogger(__name__)

class GeminiProvider:
    def __init__(self):
        try:
            # FIXED: Gemini 2.0 Flash compatibility
            self.client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options={'api_version': 'v1'}  # FIXED: v1 для Gemini 2.0
            )
            logger.info("✅ Gemini client initialized (v1 API)")
        except Exception as e:
            logger.error(f"❌ Gemini init failed: {e}")
            raise
    
    async def generate_response(
        self,
        message: str,
        history: list,
        role: str = "default",
        user_id: int = 0,
        db: AsyncSession = None
    ) -> dict:
        """
        Генерація відповіді з self-reflection та пошуком спеціалістів
        
        Returns:
            dict: Відповідь у форматі Swagger ChatResponse schema
        """
        
        # FIXED: detect_niche -> detect_service
        detected_service, confidence = reflection_engine.detect_service(message)
        user_intent = reflection_engine.classify_intent(message)
        anxiety_score = reflection_engine.calculate_anxiety_score(message)
        
        logger.info(
            f"🧠 Analysis: service={detected_service}({confidence:.2f}), "
            f"intent={user_intent.value}, anxiety={anxiety_score:.2f}"
        )
        
        response_mode = reflection_engine.get_response_mode(user_intent, anxiety_score)
        
        # Пошук спеціалістів
        top_specialists = []
        if db:
            try:
                # FIXED: Support energy_practitioner as alias for healer
                search_service = detected_service
                if detected_service == "energy_practitioner":
                    search_service = "healer"
                
                result = await db.execute(
                    select(Specialist)
                    .where(
                        Specialist.service_type == search_service,
                        Specialist.is_active == True
                    )
                    .order_by(Specialist.hourly_rate)
                    .limit(3)
                )
                specialists = result.scalars().all()
                
                # FIXED: Використовуємо правильні імена полів з alias для фронтенду
                top_specialists = [
                    {
                        "name": s.name,
                        "specialty": s.specialty,
                        "rate": s.hourly_rate,  # FIXED: Alias для hourly_rate
                        "delivery": s.delivery_method,  # FIXED: Alias для delivery_method
                        "is_ai": s.is_ai_powered
                    }
                    for s in specialists
                ]
                
                logger.info(f"🔍 Found {len(top_specialists)} specialists for {detected_service}")
                
            except Exception as e:
                logger.error(f"❌ DB query failed: {e}")
        
        # AI текст генерація
        ai_text = await self._gemini_generate(
            message, 
            history, 
            detected_service,
            top_specialists
        )
        
        # Smart link
        smart_link = reflection_engine.generate_smart_link(
            detected_service,
            top_specialists[0]["name"] if top_specialists else None,
            response_mode
        )
        
        # FIXED: Повертаємо точно по Swagger schema
        return {
            "response": ai_text,  # FIXED: Використовуємо "response" для AI тексту
            "status": "success",
            "detected_service": detected_service,
            "confidence": confidence,
            "user_intent": user_intent.value,
            "anxiety_score": anxiety_score,
            "response_mode": response_mode.value,
            "smart_link": smart_link,
            "top_specialists": top_specialists,
            "show_buttons": response_mode.value != "listening"
        }
    
    async def _gemini_generate(
        self,
        message: str,
        history: list,
        service_type: str,
        specialists: list
    ) -> str:
        """Генерація тексту через Gemini"""
        
        role_prompts = {
            "healer": "Ти - духовний цілитель 🧘.Кармолог.Регресолог.Допомагаєш з медитацією.",
            "energy_practitioner": "Ти - енергопрактик 🌟. Працюєш з енергіями.",  # FIXED: Додано
            "coach": "Ти - коуч 💎. Працюєш з розвитком.",
            "teacher_math": "Ти - вчитель математики 📐.",
            "teacher_ukrainian": "Ти - вчитель української 📚.",
            "interior_designer": "Ти - дизайнер інтер'єрів 🛋️.",
            "3d_modeling": "Ти - 3D спеціаліст 🎨.",
            "web_development": "Ти - веб-розробник 💻.",
            "default": "Ти - AI асистент Healer Nexus 🌟."
        }
        
        system_prompt = role_prompts.get(service_type, role_prompts["default"])
        
        if specialists:
            system_prompt += f"\n\nДоступні спеціалісти:\n"
            for spec in specialists:
                method_emoji = "🤖" if spec["is_ai"] else "👤"
                system_prompt += (
                    f"{method_emoji} {spec['name']} - {spec['specialty']} "
                    f"({spec['rate']}₴/год, {spec['delivery']})\n"
                )
        
        context = f"{system_prompt}\n\nІсторія:\n"
        for msg in history[-5:]:
            context += f"{msg['role']}: {msg['content']}\n"
        context += f"user: {message}\nassistant:"
        
        safety_settings = [
            SafetySetting(category=cat, threshold=HarmBlockThreshold.BLOCK_NONE)
            for cat in [
                HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                HarmCategory.HARM_CATEGORY_HARASSMENT,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT
            ]
        ]
        
        config = GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=500,
            safety_settings=safety_settings
        )
        
        try:
            response = await self.client.aio.models.generate_content(
                model='gemini-2.0-flash-exp',  # FIXED: Gemini 2.0 Flash
                contents=context,
                config=config
            )
            
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                raise ValueError("Empty Gemini response")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ GEMINI API ERROR: {error_msg}")
            
            if "403" in error_msg or "Forbidden" in error_msg:
                logger.error("🚫 Region block detected")
            elif "429" in error_msg:
                logger.error("⏳ Rate limit exceeded")
            
            raise Exception(f"Gemini Error: {error_msg[:100]}")

def get_ai_provider():
    return GeminiProvider()
