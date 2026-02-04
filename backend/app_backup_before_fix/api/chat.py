from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator
import logging

# Імпорт логіки
from app.ai.providers import get_ai_provider
from app.services.db_service import save_message, get_history
from app.database.connection import get_db
from app.services.simple_analytics import analytics

# Імпорт глобальних схем (щоб не дублювати SpecialistCard та ChatResponse)
from app.schemas.responses import ChatResponse

# Резильєнтність
from app.resilience.safe_mode import (
    get_fallback_response,
    SafeModeContext,
    SafeModeReason,
    UserState
)

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    user_id: int
    role: str = "default"

    @field_validator('message')
    @classmethod
    def sanitize(cls, v: str) -> str:
        if len(v) > 1000:
            raise ValueError("Message too long (max 1000 chars)")
        
        forbidden = ['ignore previous', 'system:', '<script>', 'admin:']
        for word in forbidden:
            if word in v.lower():
                raise ValueError("Suspicious input detected")
        return v

@router.post("/", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Чат endpoint: AI відповідь + Аналітика + Safe Mode
    """
    try:
        # 1. Історія повідомлень
        history = await get_history(request.user_id, limit=10)
        
        # 2. Генерація відповіді
        ai = get_ai_provider()
        # Очікуємо структуру: {"text": "...", "status": "...", "metadata": {...}}
        result = await ai.generate_response(
            request.message,
            history,
            request.role,
            request.user_id,
            db=db
        )
        
        metadata = result.get("metadata", {})
        
        # 3. Логування аналітики (Demand Signal)
        detected_service = metadata.get("detected_service")
        if detected_service and detected_service != "unknown":
            analytics.log_search(
                service_type=detected_service,
                user_id=request.user_id
            )
        
        # 4. Збереження в БД
        await save_message(request.user_id, "user", request.message)
        await save_message(request.user_id, "assistant", result.get("text", ""))
        
        # 5. Мапінг на схему ChatResponse
        # Це гарантує, що фронтенд отримає всі потрібні поля
        return ChatResponse(
            response=result.get("text", ""),
            status=result.get("status", "success"),
            detected_service=metadata.get("detected_service", "unknown"),
            confidence=metadata.get("confidence", 0.0),
            user_intent=metadata.get("user_intent", "unknown"),
            anxiety_score=metadata.get("anxiety_score", 0.0),
            response_mode=metadata.get("response_mode", "neutral"),
            smart_link=metadata.get("smart_link", "/"),
            top_specialists=metadata.get("top_specialists", []),
            show_buttons=metadata.get("show_buttons", True)
        )
    
    except Exception as e:
        logger.error(f"🔴 Chat error: {e}", exc_info=True)
        context = SafeModeContext(
            user_id=str(request.user_id),
            reason=SafeModeReason.ERROR,
            user_state=UserState.DEFAULT,
            error_details=str(e)[:200]
        )
        return ChatResponse(
            response=get_fallback_response(context),
            status="critical_safe_mode",
            detected_service="unknown",
            confidence=0.0,
            user_intent="unknown",
            anxiety_score=0.0,
            response_mode="listening",
            smart_link="/",
            top_specialists=[],
            show_buttons=False,
            error=str(e)[:100]
        )
