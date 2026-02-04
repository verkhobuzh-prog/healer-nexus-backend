from pydantic import BaseModel, Field
from typing import List, Optional

# ============================================
# 🏥 HEALTH CHECK SCHEMAS
# ============================================
class HealthResponse(BaseModel):
    """Відповідь на /api/health"""
    status: str = Field(..., example="healthy")
    database: str = Field(..., example="connected")
    ai_provider: str = Field(..., example="available")
    uptime_seconds: float = Field(..., example=3600.5)

# ============================================
# 🎯 SERVICES SCHEMAS
# ============================================
class ServiceInfo(BaseModel):
    """Інформація про один сервіс"""
    id: str = Field(..., example="healer")
    name: str = Field(..., example="Енергопрактики")
    description: str = Field(..., example="Духовні цілителі та майстри енергії")
    icon: str = Field(..., example="🧘‍♀️")
    available_specialists: int = Field(..., example=12)

class ServicesListResponse(BaseModel):
    """Список доступних сервісів"""
    services: List[ServiceInfo]
    total: int = Field(..., example=15)

# ============================================
# 👤 SPECIALIST SCHEMAS
# ============================================
class SpecialistBase(BaseModel):
    name: str = Field(..., example="Таня")
    specialty: str = Field(..., example="Рейкі майстер")
    service_type: str = Field(..., example="healer")
    hourly_rate: int = Field(..., example=500)
    delivery_method: str = Field(default="online", example="online")

class SpecialistCreate(SpecialistBase):
    """Схема для створення спеціаліста"""
    pass

class SpecialistUpdate(BaseModel):
    """Схема для оновлення спеціаліста (всі поля опціональні)"""
    name: Optional[str] = None
    specialty: Optional[str] = None
    service_type: Optional[str] = None
    hourly_rate: Optional[int] = None
    delivery_method: Optional[str] = None
    is_active: Optional[bool] = None

class SpecialistOut(SpecialistBase):
    """Повна інформація про спеціаліста (з ID та статусом)"""
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# ============================================
# 💬 CHAT SCHEMAS (Мапінг для фронтенду)
# ============================================
class SpecialistShort(BaseModel):
    """Скорочена інформація про спеціаліста для карток у чаті"""
    name: str = Field(..., example="Таня")
    specialty: str = Field(..., example="Рейкі майстер")
    rate: int = Field(..., example=500, description="Мапиться з hourly_rate")
    delivery: str = Field(..., example="online", description="Мапиться з delivery_method")
    is_ai: bool = Field(default=False, example=False)

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    """Відповідь від чат-бота з метаданими"""
    response: str = Field(..., example="Знайдено 3 спеціалісти для вас")
    status: str = Field(default="success", example="success")
    detected_service: Optional[str] = Field(None, example="healer")
    confidence: float = Field(default=0.0, example=0.92)
    user_intent: Optional[str] = Field(None, example="seeking_help")
    anxiety_score: int = Field(default=0, example=4)
    response_mode: Optional[str] = Field(None, example="empathetic")
    smart_link: Optional[str] = Field(None, example="/specialists/healer")
    top_specialists: List[SpecialistShort] = Field(default_factory=list)
    show_buttons: bool = Field(default=True, example=True)
    error: Optional[str] = Field(None, example=None)

# ============================================
# 📈 ANALYTICS SCHEMAS
# ============================================
class AnalyticsResponse(BaseModel):
    """Відповідь з аналітикою платформи"""
    total_chats: int = Field(..., example=1250)
    active_specialists: int = Field(..., example=45)
    most_requested_service: str = Field(..., example="healer")
    avg_response_time_ms: float = Field(..., example=250.5)
