from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator # У Pydantic v2 використовується field_validator
import logging

from app.ai.providers import get_ai_provider
from app.services.db_service import save_message, get_history
from app.database.connection import get_db
from app.resilience.safe_mode import (
    get_fallback_response,
    SafeModeContext,
    SafeModeReason,
    UserState
)

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    user_id: int
    role: str = "default"

    @field_validator('message')
    @classmethod
    def sanitize(cls, v):
        if len(v) > 1000:
            raise ValueError("Message too long (max 1000 chars)")

        forbidden = ['ignore previous', 'system:', '<script>', 'admin:']
        for word in forbidden:
            if word in v.lower():
                raise ValueError("Suspicious input detected")

        return v

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Чат endpoint з інтеграцією self-reflection та DB lookup
    """
    try:
        # 1. Отримуємо історію повідомлень з БД
        history = await get_history(request.user_id, limit=10)

        # 2. Отримуємо провайдера та генеруємо відповідь
        ai = get_ai_provider()
        result = await ai.generate_response(
            message=request.message,
            history=history,
            role=request.role,
            user_id=request.user_id,
            db=db  # Передаємо сесію для пошуку спеціалістів
        )
        
        # 3. Зберігаємо листування
        await save_message(request.user_id, "user", request.message)
        await save_message(request.user_id, "assistant", result["text"])
        
        # 4. Повертаємо результат з розпакованими метаданими (success)
        return {
            "response": result["text"],
            "status": "success",
            **result["metadata"]
        }
        
    except Exception as e:
        logger.error(f"🔴 Chat error: {e}", exc_info=True)
        
        # Формуємо контекст для SafeMode
        context = SafeModeContext(
            user_id=str(request.user_id),
            reason=SafeModeReason.ERROR,
            user_state=UserState.DEFAULT,
            error_details=str(e)[:200]
        )
        
        # 5. Повертаємо структуру SafeMode (ідентична до успішної за ключами)
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
            "error_detail": str(e)[:100]
        }
