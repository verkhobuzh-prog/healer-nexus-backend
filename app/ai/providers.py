"""
Healer Nexus — AI Provider (Gemini)
Fixed: GeminiProvider as proper class, genai.configure(), model gemini-2.0-flash
"""

import asyncio
import logging
from typing import Optional

import google.generativeai as genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.ai.self_reflection import reflection_engine
from app.ai.prompts import EMPATHY_RULE, ETHICAL_INSTRUCTION
from app.services.chat_tools import CHAT_TOOLS, TOOL_SYSTEM_PROMPT_ADDITION
from app.services.chat_tool_executor import ChatToolExecutor

logger = logging.getLogger(__name__)

# --- Configure Gemini API key at module level ---
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    logger.info("Gemini API configured")
else:
    logger.warning("GEMINI_API_KEY not set — GeminiProvider will fail on use")


# --- Helper (module-level function, NOT a method) ---
def _contents_from_history(history: list, system_prompt: str, last_message: str):
    """Build Gemini contents: system + history + user message."""
    contents = []
    if system_prompt:
        contents.append(
            genai.protos.Content(
                role="user",
                parts=[genai.protos.Part(text=system_prompt)],
            )
        )
    for msg in (history or [])[-10:]:
        role = "user" if msg.get("role") == "user" else "model"
        text = (msg.get("content") or "").strip()
        if text:
            contents.append(
                genai.protos.Content(role=role, parts=[genai.protos.Part(text=text)])
            )
    if last_message:
        contents.append(
            genai.protos.Content(
                role="user",
                parts=[genai.protos.Part(text=last_message)],
            )
        )
    return contents


# --- Role prompts ---
ROLE_PROMPTS = {
    "healer": "Ти - духовний цілитель 🧘. Допомагаєш з медитацією.",
    "coach": "Ти - коуч 👋. Працюєш з розвитком.",
    "teacher_math": "Ти - вчитель математики 📐.",
    "teacher_ukrainian": "Ти - вчитель української 📚.",
    "interior_designer": "Ти - дизайнер інтер'єрів 🛋️.",
    "3d_modeling": "Ти - 3D спеціаліст 🎨.",
    "web_development": "Ти - веб-розробник 💻.",
    "default": "Ти - AI асистент Healer Nexus 🌟.",
}


class GeminiProvider:
    """Gemini-based AI provider with function calling support."""

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    async def generate_response(
        self,
        message: str,
        history: list,
        role: str = "default",
        user_id: int = 0,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """Generate response with self-reflection and specialist search."""

        # 1. Self-reflection analysis
        detected_service, confidence = reflection_engine.detect_service(message)
        user_intent = reflection_engine.classify_intent(message)
        anxiety_score = reflection_engine.calculate_anxiety_score(message)

        logger.info(
            "Analysis: service=%s(%.2f), intent=%s, anxiety=%.2f",
            detected_service, confidence, user_intent.value, anxiety_score,
        )

        response_mode = reflection_engine.get_response_mode(user_intent, anxiety_score)

        # 2. Search specialists from DB (fallback when not using tools)
        top_specialists = []
        if db:
            try:
                result = await db.execute(
                    select(Specialist)
                    .where(
                        Specialist.service_type == detected_service,
                        Specialist.is_active == True,
                    )
                    .order_by(Specialist.hourly_rate)
                    .limit(3)
                )
                specialists = result.scalars().all()
                top_specialists = [
                    {
                        "id": s.id,
                        "name": s.name,
                        "specialty": s.specialty,
                        "rate": s.hourly_rate,
                        "delivery": s.delivery_method,
                        "is_ai": s.is_ai_powered,
                    }
                    for s in specialists
                ]
                logger.info("Found %d specialists for %s", len(top_specialists), detected_service)
            except Exception as e:
                logger.error("DB query failed: %s", e)

        # 3. AI text: tool-based flow when db available
        ai_text = ""
        if db and user_id:
            try:
                ai_text, tool_specialists = await self._gemini_generate_with_tools(
                    message, history, detected_service, db, user_id
                )
                if tool_specialists:
                    top_specialists = tool_specialists
            except Exception as e:
                logger.warning("Tool-based generation failed, falling back: %s", e)

        if not ai_text:
            ai_text = await self._gemini_generate(
                message, history, detected_service, top_specialists, db=db
            )

        # 4. Smart link
        smart_link = reflection_engine.generate_smart_link(
            detected_service,
            top_specialists[0]["name"] if top_specialists else None,
            response_mode,
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
                "show_buttons": response_mode.value != "listening",
            },
        }

    async def _gemini_generate_with_tools(
        self,
        message: str,
        history: list,
        service_type: str,
        db: AsyncSession,
        user_id: int,
    ) -> tuple[str, list]:
        """Generate with tool loop; returns (text, top_specialists)."""
        system_prompt = ROLE_PROMPTS.get(service_type, ROLE_PROMPTS["default"])
        system_prompt += f"\n\n{EMPATHY_RULE}\n\n{ETHICAL_INSTRUCTION}\n\n{TOOL_SYSTEM_PROMPT_ADDITION}"

        project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
        executor = ChatToolExecutor(db, project_id, user_id, conversation_id=None)

        try:
            model_with_tools = genai.GenerativeModel("gemini-2.0-flash", tools=CHAT_TOOLS)
        except Exception:
            model_with_tools = genai.GenerativeModel("gemini-2.0-flash", tools=[CHAT_TOOLS])

        contents = _contents_from_history(history, system_prompt, message)
        top_specialists = []
        max_tool_rounds = 5

        while max_tool_rounds > 0:
            max_tool_rounds -= 1
            response = await asyncio.to_thread(model_with_tools.generate_content, contents)

            if not response.candidates or not response.candidates[0].content.parts:
                return (getattr(response, "text", None) or "", top_specialists)

            parts = response.candidates[0].content.parts
            function_calls = []
            text_parts = []

            for part in parts:
                if getattr(part, "function_call", None):
                    fc = part.function_call
                    name = getattr(fc, "name", None) or ""
                    args = dict(getattr(fc, "args", None) or {})
                    if not hasattr(args, "items"):
                        args = {}
                    function_calls.append((part, name, args))
                elif getattr(part, "text", None):
                    text_parts.append(part.text)

            if function_calls:
                model_content = genai.protos.Content(
                    role="model",
                    parts=[p for p, _, _ in function_calls],
                )
                contents.append(model_content)

                response_parts = []
                for _, fc_name, fc_args in function_calls:
                    result = await executor.execute_tool_call(fc_name, fc_args)
                    if fc_name == "search_specialists" and isinstance(
                        result.get("specialists"), list
                    ):
                        top_specialists = [
                            {
                                "id": s.get("id"),
                                "name": s.get("name"),
                                "specialty": s.get("specialty"),
                                "rate": s.get("hourly_rate", 0),
                                "delivery": s.get("delivery_method", "human"),
                                "is_ai": False,
                            }
                            for s in result["specialists"]
                        ]
                    response_parts.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fc_name,
                                response={"result": result},
                            )
                        )
                    )
                contents.append(genai.protos.Content(role="user", parts=response_parts))
                continue

            return ("".join(text_parts).strip(), top_specialists)

        return ("", top_specialists)

    async def _gemini_generate(
        self,
        message: str,
        history: list,
        service_type: str,
        specialists: list,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """Generate text via Gemini with optional practitioner profile personalization."""
        system_prompt = ROLE_PROMPTS.get(service_type, ROLE_PROMPTS["default"])
        system_prompt += f"\n\n{EMPATHY_RULE}"
        system_prompt += f"\n\n{ETHICAL_INSTRUCTION}"

        # Practitioner personalization
        if db and specialists:
            first_specialist_id = specialists[0].get("id") if specialists else None
            if first_specialist_id is not None:
                try:
                    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
                    result = await db.execute(
                        select(PractitionerProfile)
                        .where(
                            PractitionerProfile.specialist_id == first_specialist_id,
                            PractitionerProfile.project_id == project_id,
                            PractitionerProfile.is_active == True,
                        )
                        .limit(1)
                    )
                    profile = result.scalar_one_or_none()
                    if profile:
                        parts = []
                        if profile.unique_story:
                            parts.append(f"Історія практика: {profile.unique_story}")
                        if profile.soft_cta_text:
                            parts.append(f"М'який заклик до дії: {profile.soft_cta_text}")
                        if profile.contact_link:
                            parts.append(f"Посилання для контакту: {profile.contact_link}")
                        if parts:
                            empathy_prompt = "\n".join(parts)
                            if profile.creator_signature:
                                empathy_prompt += f"\n{profile.creator_signature}"
                            system_prompt += f"\n\nПерсоналізація практика:\n{empathy_prompt}"
                except Exception as e:
                    logger.error("Practitioner profile fetch failed: %s", e)

        # Add specialists info to prompt
        if specialists:
            system_prompt += "\n\nДоступні спеціалісти:\n"
            for spec in specialists:
                method_emoji = "🤖" if spec.get("is_ai") else "👤"
                system_prompt += (
                    f"{method_emoji} {spec['name']} - {spec['specialty']} "
                    f"({spec['rate']}₴/год, {spec['delivery']})\n"
                )

        # Build context
        context = f"{system_prompt}\n\nІсторія:\n"
        for msg in history[-5:]:
            context += f"{msg['role']}: {msg['content']}\n"
        context += f"user: {message}\nassistant:"

        try:
            response = await asyncio.to_thread(self.model.generate_content, context)
            return response.text or ""
        except Exception as e:
            error_msg = str(e)
            logger.error("Gemini API error: %s", error_msg[:200])
            raise Exception(f"Gemini Error: {error_msg[:100]}")


def get_ai_provider():
    """Factory function — returns GeminiProvider instance."""
    return GeminiProvider()