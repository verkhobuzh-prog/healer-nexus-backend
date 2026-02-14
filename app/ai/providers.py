import asyncio
import google.generativeai as genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.config import settings
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.ai.self_reflection import reflection_engine
from app.ai.prompts import EMPATHY_RULE, ETHICAL_INSTRUCTION

logger = logging.getLogger(__name__)

class GeminiProvider:
    def __init__(self):
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')  # ✅ FIXED: was gemini-2.5-flash
            logger.info("✅ Gemini client initialized")
        except Exception as e:
            logger.error(f"❌ Gemini init failed: {e}")
            raise
    
    async def generate_response(
        self,
        message: str,
        history: list,
        role: str = "default",
        user_id: int = 0,
        db: AsyncSession = None  # ✅ Передаємо AsyncSession
    ) -> dict:
        """
        Генерація відповіді з self-reflection та пошуком спеціалістів
        """
        
        # 1. Self-reflection analysis
        detected_service, confidence = reflection_engine.detect_service(message)
        user_intent = reflection_engine.classify_intent(message)
        anxiety_score = reflection_engine.calculate_anxiety_score(message)
        
        logger.info(
            f"🧠 Analysis: service={detected_service}({confidence:.2f}), "
            f"intent={user_intent.value}, anxiety={anxiety_score:.2f}"
        )
        
        response_mode = reflection_engine.get_response_mode(user_intent, anxiety_score)
        
        # 2. Пошук спеціалістів з БД (якщо передано db)
        top_specialists = []
        if db:
            try:
                # ✅ Коректний асинхронний запит
                result = await db.execute(
                    select(Specialist)
                    .where(
                        Specialist.service_type == detected_service,
                        Specialist.is_active == True
                    )
                    .order_by(Specialist.hourly_rate)  # Від дешевших до дорожчих
                    .limit(3)
                )
                specialists = result.scalars().all()  # ✅ .all() синхронний після execute
                
                top_specialists = [
                    {
                        "id": s.id,
                        "name": s.name,
                        "specialty": s.specialty,
                        "rate": s.hourly_rate,
                        "delivery": s.delivery_method,
                        "is_ai": s.is_ai_powered
                    }
                    for s in specialists
                ]
                
                logger.info(f"🔍 Found {len(top_specialists)} specialists for {detected_service}")
                
            except Exception as e:
                logger.error(f"❌ DB query failed: {e}")
        
        # 3. AI текст генерація (з practitioner profile якщо є)
        ai_text = await self._gemini_generate(
            message,
            history,
            detected_service,
            top_specialists,
            db=db,
        )
        
        # 4. Smart link
        smart_link = reflection_engine.generate_smart_link(
            detected_service,
            top_specialists[0]["name"] if top_specialists else None,
            response_mode
        )
        
        return {
            "text": ai_text,
            "metadata": {
                "detected_service": detected_service,
                "confidence": confidence,
                "user_intent": user_intent.value,
                "anxiety_score": anxiety_score,
                "response_mode": response_mode.value,
                "smart_link": smart_link,
                "top_specialists": top_specialists,
                "show_buttons": response_mode.value != "listening"
            }
        }
    
    async def _gemini_generate(
        self,
        message: str,
        history: list,
        service_type: str,
        specialists: list,
        db: AsyncSession = None,
    ) -> str:
        """Генерація тексту через Gemini з опційним practitioner profile."""
        
        # 🔍 DEBUG: Вхідні параметри
        logger.info(f"🔍 _gemini_generate START: db={db is not None}, specialists_count={len(specialists) if specialists else 0}")
        if specialists:
            logger.info(f"🔍 First specialist: {specialists[0]}")
        
        role_prompts = {
            "healer": "Ти - духовний цілитель 🧘. Допомагаєш з медитацією.",
            "coach": "Ти - коуч 💎. Працюєш з розвитком.",
            "teacher_math": "Ти - вчитель математики 📐.",
            "teacher_ukrainian": "Ти - вчитель української 📚.",
            "interior_designer": "Ти - дизайнер інтер'єрів 🛋️.",
            "3d_modeling": "Ти - 3D спеціаліст 🎨.",
            "web_development": "Ти - веб-розробник 💻.",
            "default": "Ти - AI асистент Healer Nexus 🌟."
        }
        system_prompt = role_prompts.get(service_type, role_prompts["default"])
        system_prompt += f"\n\n{EMPATHY_RULE}"
        system_prompt += f"\n\n{ETHICAL_INSTRUCTION}"

        # Practitioner personalization: fetch profile by specialist_id, build empathy_prompt
        if db and specialists:
            first_specialist_id = specialists[0].get("id") if specialists else None
            logger.info(f"🔍 Looking for profile: specialist_id={first_specialist_id}")
            
            if first_specialist_id is not None:
                try:
                    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
                    logger.info(f"🔍 Query params: specialist_id={first_specialist_id}, project_id={project_id}")
                    
                    result = await db.execute(
                        select(PractitionerProfile).where(
                            PractitionerProfile.specialist_id == first_specialist_id,
                            PractitionerProfile.project_id == project_id,
                            PractitionerProfile.is_active == True,
                        ).limit(1)
                    )
                    profile = result.scalar_one_or_none()
                    
                    logger.info(f"🔍 Profile found: {profile is not None}")
                    
                    if profile:
                        logger.info(f"🔍 Profile data: story={profile.unique_story[:50] if profile.unique_story else None}..., cta={profile.soft_cta_text}, link={profile.contact_link}, signature={profile.creator_signature}")
                        
                        parts = []
                        if profile.unique_story:
                            parts.append(f"Історія практика (використовуй для тонгу): {profile.unique_story}")
                        if profile.soft_cta_text:
                            parts.append(f"М'який заклик до дії: {profile.soft_cta_text}")
                        if profile.contact_link:
                            parts.append(f"Посилання для контакту: {profile.contact_link}")
                        if parts:
                            empathy_prompt = "\n".join(parts)
                            if profile.creator_signature:
                                empathy_prompt += f"\n{profile.creator_signature}"
                            system_prompt += f"\n\nПерсоналізація практика:\n{empathy_prompt}"
                            logger.info(f"✅ Personalization added to prompt! Length: {len(empathy_prompt)} chars")
                        else:
                            logger.warning("⚠️ Profile exists but all fields are empty")
                    else:
                        logger.warning(f"⚠️ No profile found for specialist_id={first_specialist_id}, project_id={project_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Practitioner profile fetch failed: {e}", exc_info=True)
        else:
            logger.info(f"🔍 Skipping profile: db={db is not None}, specialists={len(specialists) if specialists else 0}")

        # Додаємо інформацію про спеціалістів
        if specialists:
            system_prompt += f"\n\nДоступні спеціалісти:\n"
            for spec in specialists:
                method_emoji = "🤖" if spec["is_ai"] else "👤"
                system_prompt += (
                    f"{method_emoji} {spec['name']} - {spec['specialty']} "
                    f"({spec['rate']}₴/год, {spec['delivery']})\n"
                )
        
        # 🔍 DEBUG: Фінальний prompt
        logger.info(f"🔍 Final system_prompt length: {len(system_prompt)} chars")
        logger.info(f"🔍 System prompt preview: {system_prompt[:200]}...")
        
        # Формуємо контекст
        context = f"{system_prompt}\n\nІсторія:\n"
        for msg in history[-5:]:
            context += f"{msg['role']}: {msg['content']}\n"
        context += f"user: {message}\nassistant:"
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, context)
            text = response.text or ""
            # Disclaimer added by chat.py response assembly, not here
            return text
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