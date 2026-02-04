from enum import Enum
from dataclasses import dataclass
from typing import Optional

class SafeModeReason(Enum):
    OUTAGE = "api_offline"
    RATE_LIMIT = "rate_limit_hit"
    TIMEOUT = "request_timeout"
    ERROR = "internal_error"

class UserState(Enum):
    DEFAULT = "default"
    PREMIUM = "premium"
    ADMIN = "admin"

@dataclass
class SafeModeContext:
    user_id: str
    reason: SafeModeReason
    user_state: UserState = UserState.DEFAULT
    error_details: Optional[str] = None

def get_fallback_response(context: SafeModeContext) -> str:
    """Розумні fallback відповіді"""
    
    responses = {
        SafeModeReason.OUTAGE: {
            UserState.DEFAULT: "🛡️ AI асистент тимчасово недоступний. Спробуйте через 1-2 хвилини.",
            UserState.ADMIN: f"🔴 OUTAGE: {context.error_details}"
        },
        SafeModeReason.RATE_LIMIT: {
            UserState.DEFAULT: "⏳ Ви надіслали забагато запитів. Зачекайте 1 хвилину."
        },
        SafeModeReason.TIMEOUT: {
            UserState.DEFAULT: "⏱️ Запит триває довше, ніж зазвичай. Спробуйте коротше."
        },
        SafeModeReason.ERROR: {
            UserState.DEFAULT: "❌ Виникла технічна помилка. Спробуйте ще раз."
        }
    }
    
    reason_responses = responses.get(context.reason, {})
    return reason_responses.get(
        context.user_state,
        reason_responses.get(UserState.DEFAULT, "Сервіс тимчасово недоступний")
    )
