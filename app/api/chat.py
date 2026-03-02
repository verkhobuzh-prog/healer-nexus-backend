"""
Healer Nexus — Chat endpoint
Fixed: GEMINI_ENABLED guard, clean error handling
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator
import logging

from app.config import settings
from app.services.db_service import save_message, get_history
from app.database.connection import get_db
from app.resilience.safe_mode import (
    get_fallback_response,
    SafeModeContext,
    SafeModeReason,
    UserState,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    user_id: int
    role: str = "default"

    @field_validator("message")
    @classmethod
    def sanitize(cls, v):
        if len(v) > 1000:
            raise ValueError("Message too long (max 1000 chars)")
        forbidden = ["ignore previous", "system:", "<script>", "admin:"]
        for word in forbidden:
            if word in v.lower():
                raise ValueError("Suspicious input detected")
        return v


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Chat endpoint with Gemini AI, self-reflection and specialist search."""

    # --- GEMINI_ENABLED guard ---
    if not settings.GEMINI_ENABLED:
        return JSONResponse(
            status_code=503,
            content={
                "response": "AI тимчасово вимкнений. Спробуйте пізніше.",
                "status": "ai_disabled",
                "top_specialists": [],
                "show_buttons": False,
            },
        )

    try:
        # 1. Get conversation history
        history = await get_history(request.user_id, limit=10)

        # 2. Generate AI response (import here so module doesn't crash when Gemini disabled)
        from app.ai.providers import get_ai_provider
        from app.ai.prompts import ETHICAL_DISCLAIMER_FOR_RESPONSE

        ai = get_ai_provider()
        result = await ai.generate_response(
            message=request.message,
            history=history,
            role=request.role,
            user_id=request.user_id,
            db=db,
        )

        # 3. Save messages
        await save_message(request.user_id, "user", request.message)

        response_text = (result["text"] or "").rstrip()

        # Strip any disclaimer Gemini echoed (avoid duplicates), then add once
        disclaimer_text = ETHICAL_DISCLAIMER_FOR_RESPONSE.strip()
        if disclaimer_text:
            while response_text.endswith(disclaimer_text):
                response_text = response_text[: -len(disclaimer_text)].rstrip()
            response_text += ETHICAL_DISCLAIMER_FOR_RESPONSE

        await save_message(request.user_id, "assistant", response_text)

        # 4. Clean specialist names (encoding safety)
        specialists_clean = []
        for spec in result["metadata"].get("top_specialists", []):
            spec_copy = dict(spec)
            for key in ("name", "specialty"):
                val = spec_copy.get(key)
                if isinstance(val, bytes):
                    spec_copy[key] = val.decode("utf-8", errors="replace")
            specialists_clean.append(spec_copy)

        metadata = {**result["metadata"], "top_specialists": specialists_clean}
        return {
            "response": response_text,
            "status": "success",
            **metadata,
        }

    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)

        context = SafeModeContext(
            user_id=str(request.user_id),
            reason=SafeModeReason.ERROR,
            user_state=UserState.DEFAULT,
            error_details=str(e)[:200],
        )

        return {
            "response": get_fallback_response(context),
            "status": "critical_safe_mode",
            "detected_service": "unknown",
            "confidence": 0.0,
            "user_intent": "unknown",
            "anxiety_score": 0.0,
            "response_mode": "listening",
            "smart_link": "/",
            "top_specialists": [],
            "show_buttons": False,
        }