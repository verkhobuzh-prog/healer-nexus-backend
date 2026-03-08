"""
Healer Nexus - AI Provider (google-genai v1.65+)
Migrated from deprecated google.generativeai to google.genai
Model: gemini-2.5-flash
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from google import genai
from google.genai import types

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

# --- Client init ---
client = None
try:
    if settings.GEMINI_API_KEY:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    else:
        logger.warning("GEMINI_API_KEY not set, AI features disabled")
except Exception as e:
    logger.warning("Failed to init Gemini client: %s", e)

MODEL_NAME = "gemini-2.5-flash"

# --- System prompts per role ---
ROLE_PROMPTS = {
    "default": (
        "You are a friendly AI assistant of the Healer Nexus platform. "
        "You help people find specialists: healers, psychologists, "
        "teachers, designers, coaches. Answer in Ukrainian. "
        "Be empathetic and attentive to people's needs."
    ),
    "healer": (
        "You are an AI assistant focused on healing and energy practices. "
        "Help find the right healer. Answer in Ukrainian."
    ),
    "psychologist": (
        "You are an AI assistant focused on psychological support. "
        "Help find a psychologist or coach. Answer in Ukrainian."
    ),
    "teacher": (
        "You are an AI assistant focused on education. "
        "Help find a teacher or tutor. Answer in Ukrainian."
    ),
    "designer": (
        "You are an AI assistant focused on design. "
        "Help find a designer. Answer in Ukrainian."
    ),
}


def _build_contents(message, history):
    """Convert chat history + new message to google.genai format."""
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])],
            )
        )
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)],
        )
    )
    return contents


def _build_tools():
    """Gemini function calling tools for specialist search and booking."""
    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="search_specialists",
                    description="Search specialists on the platform by keywords",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "query": types.Schema(
                                type=types.Type.STRING,
                                description="Search keywords",
                            ),
                            "specialty": types.Schema(
                                type=types.Type.STRING,
                                description="Specialist type",
                            ),
                        },
                        required=["query"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="get_specialist_details",
                    description="Get detailed info about a specialist by ID",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "specialist_id": types.Schema(
                                type=types.Type.INTEGER,
                                description="Specialist ID",
                            ),
                        },
                        required=["specialist_id"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="create_booking",
                    description="Create a booking with a specialist",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "specialist_id": types.Schema(
                                type=types.Type.INTEGER,
                                description="Specialist ID",
                            ),
                            "reason": types.Schema(
                                type=types.Type.STRING,
                                description="Reason for visit",
                            ),
                        },
                        required=["specialist_id"],
                    ),
                ),
            ]
        )
    ]


class GeminiProvider:
    """AI provider based on Gemini API (google-genai)."""

    def __init__(self):
        self.model = MODEL_NAME
        logger.info("GeminiProvider initialized: %s", self.model)

    async def generate_response(self, message, history, role="default", user_id=0, db=None):
        """Main entry: generate response with optional function calling."""
        if client is None:
            return {
                "text": "AI is temporarily unavailable (Gemini not configured).",
                "metadata": {
                    "detected_service": "general",
                    "confidence": 0.0,
                    "user_intent": "general",
                    "anxiety_score": 0.0,
                    "response_mode": "disabled",
                    "smart_link": "/specialists",
                    "top_specialists": [],
                    "show_buttons": False,
                },
            }
        detected_service = self._detect_service(message)

        top_specialists = []
        if db:
            try:
                top_specialists = await self._search_specialists_db(message, db)
            except Exception as e:
                logger.warning("Specialist search failed: %s", e)

        try:
            ai_text = await self._gemini_generate_with_tools(
                message, history, detected_service, top_specialists, db=db
            )
        except Exception as e:
            logger.warning("Tool generation failed: %s, falling back", e)
            try:
                ai_text = await self._gemini_generate(
                    message, history, detected_service, top_specialists, db=db
                )
            except Exception as e2:
                logger.error("Gemini generation failed: %s", e2)
                raise

        return {
            "text": ai_text,
            "metadata": {
                "detected_service": detected_service,
                "confidence": 0.8 if detected_service != "general" else 0.5,
                "user_intent": detected_service,
                "anxiety_score": 0.0,
                "response_mode": "empathetic",
                "smart_link": "/specialists?type=" + detected_service,
                "top_specialists": [
                    {"id": s.id, "name": s.name, "specialty": s.specialty, "hourly_rate": s.hourly_rate}
                    for s in top_specialists[:3]
                ],
                "show_buttons": len(top_specialists) > 0,
            },
        }

    async def _gemini_generate_with_tools(self, message, history, detected_service, top_specialists, db=None):
        """Generate with function calling tools."""
        system_prompt = ROLE_PROMPTS.get(detected_service, ROLE_PROMPTS["default"])

        if top_specialists:
            specs_info = "\n".join(
                "- {} ({}), {} grn/h, ID: {}".format(s.name, s.specialty, s.hourly_rate, s.id)
                for s in top_specialists[:5]
            )
            system_prompt += "\n\nAvailable specialists:\n" + specs_info + "\nRecommend suitable ones."

        contents = _build_contents(message, history)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=_build_tools(),
            temperature=0.7,
            max_output_tokens=1024,
        )

        if client is None:
            return "AI is temporarily unavailable (Gemini not configured)."
        response = await client.aio.models.generate_content(
            model=self.model, contents=contents, config=config,
        )

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    tool_result = await self._execute_tool(
                        part.function_call.name,
                        dict(part.function_call.args) if part.function_call.args else {},
                        db,
                    )
                    contents.append(response.candidates[0].content)
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_function_response(
                                name=part.function_call.name,
                                response={"result": tool_result},
                            )],
                        )
                    )
                    follow_up = await client.aio.models.generate_content(
                        model=self.model, contents=contents, config=config,
                    )
                    return follow_up.text or "Could not get response."

        return response.text or "Could not get response."

    async def _gemini_generate(self, message, history, detected_service, top_specialists, db=None):
        """Simple generation without tools."""
        system_prompt = ROLE_PROMPTS.get(detected_service, ROLE_PROMPTS["default"])

        if top_specialists:
            specs_info = "\n".join(
                "- {} ({}), {} grn/h, ID: {}".format(s.name, s.specialty, s.hourly_rate, s.id)
                for s in top_specialists[:5]
            )
            system_prompt += "\n\nAvailable specialists:\n" + specs_info + "\nRecommend suitable ones."

        contents = _build_contents(message, history)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=1024,
        )

        if client is None:
            return "AI is temporarily unavailable (Gemini not configured)."
        try:
            response = await client.aio.models.generate_content(
                model=self.model, contents=contents, config=config,
            )
            return response.text or "Could not get response."
        except Exception as e:
            error_msg = str(e)
            logger.error("Gemini Error: %s", error_msg[:200])
            raise Exception("Gemini Error: " + error_msg[:100])

    async def _execute_tool(self, tool_name, args, db):
        """Execute a function call from Gemini."""
        try:
            from app.services.chat_tool_executor import ChatToolExecutor
            executor = ChatToolExecutor(db)

            if tool_name == "search_specialists":
                result = await executor.search_specialists(query=args.get("query", ""), specialty=args.get("specialty"))
                return str(result)
            elif tool_name == "get_specialist_details":
                result = await executor.get_specialist_details(specialist_id=args.get("specialist_id", 0))
                return str(result)
            elif tool_name == "create_booking":
                result = await executor.create_booking(specialist_id=args.get("specialist_id", 0), reason=args.get("reason", ""))
                return str(result)
            return "Unknown tool: " + tool_name
        except Exception as e:
            logger.error("Tool error (%s): %s", tool_name, e)
            return "Tool error: " + str(e)[:100]

    async def _search_specialists_db(self, message, db):
        """Search specialists in DB by keywords."""
        try:
            from app.services.specialist_matcher import SpecialistMatcher
            matcher = SpecialistMatcher(db)
            return await matcher.search(message)
        except ImportError:
            from sqlalchemy import select, or_
            from app.models.specialist import Specialist
            keywords = message.lower().split()[:3]
            if not keywords:
                return []
            conditions = []
            for kw in keywords:
                conditions.extend([
                    Specialist.name.ilike("%" + kw + "%"),
                    Specialist.specialty.ilike("%" + kw + "%"),
                    Specialist.bio.ilike("%" + kw + "%"),
                ])
            result = await db.execute(
                select(Specialist).where(Specialist.is_active == True).where(or_(*conditions)).limit(5)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.warning("DB search failed: %s", e)
            return []

    def _detect_service(self, message):
        """Detect service type from message keywords."""
        msg = message.lower()
        kw = {
            "healer": ["healer", "energy", "reiki", "chakr",
                "\u0446\u0456\u043b\u0438\u0442\u0435\u043b\u044c", "\u0435\u043d\u0435\u0440\u0433\u0435\u0442\u0438\u043a",
                "\u0440\u0435\u0439\u043a\u0456", "\u0447\u0430\u043a\u0440", "\u0435\u043d\u0435\u0440\u0433\u0456",
                "\u0446\u0456\u043b\u0438\u0442\u0435\u043b\u044c\u0441\u0442\u0432", "\u0437\u0446\u0456\u043b\u0435\u043d"],
            "psychologist": ["psycholog", "anxiety", "depress", "stress",
                "\u043f\u0441\u0438\u0445\u043e\u043b\u043e\u0433", "\u0442\u0440\u0438\u0432\u043e\u0436\u043d",
                "\u0434\u0435\u043f\u0440\u0435\u0441", "\u0441\u0442\u0440\u0435\u0441", "\u0442\u0435\u0440\u0430\u043f",
                "\u043a\u043f\u0442", "\u0441\u0430\u043c\u043e\u043e\u0446\u0456\u043d\u043a", "\u0441\u0442\u0440\u0430\u0445"],
            "teacher": ["teacher", "math", "tutor", "lesson",
                "\u0432\u0447\u0438\u0442\u0435\u043b\u044c", "\u043c\u0430\u0442\u0435\u043c\u0430\u0442\u0438\u043a",
                "\u0437\u043d\u043e", "\u0440\u0435\u043f\u0435\u0442\u0438\u0442\u043e\u0440", "\u0443\u0440\u043e\u043a",
                "\u043e\u043b\u0456\u043c\u043f\u0456\u0430\u0434"],
            "designer": ["design", "ui", "ux", "brand", "logo",
                "\u0434\u0438\u0437\u0430\u0439\u043d", "\u0456\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441",
                "\u0431\u0440\u0435\u043d\u0434\u0438\u043d\u0433", "\u043b\u043e\u0433\u043e\u0442\u0438\u043f"],
            "coach": ["coach", "motivat", "goal",
                "\u043a\u043e\u0443\u0447", "\u043c\u043e\u0442\u0438\u0432\u0430\u0446",
                "\u0440\u043e\u0437\u0432\u0438\u0442\u043e\u043a", "\u0446\u0456\u043b\u0456"],
        }
        for service, words in kw.items():
            if any(w in msg for w in words):
                return service
        return "general"


def get_ai_provider():
    """AI provider factory."""
    return GeminiProvider()