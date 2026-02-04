from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime

# ==========================================
# 1. Системні схеми (Resilience & Base)
# ==========================================

class BaseResponse(BaseModel):
    status: str = "success"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class HealthStatus(BaseModel):
    status: str  # healthy, degraded, down
    details: Optional[Dict[str, Any]] = None

class ChatResponse(BaseResponse):
    response: str
    is_safe_mode: bool = False
    model_used: Optional[str] = None
    suggestions: List[Any] = []  # str (legacy) or dict with id, name, role, specialization (fallback)

# ==========================================
# 2. Схеми Спеціалістів (Specialists)
# ==========================================

class SpecialistBase(BaseModel):
    """Base fields for specialist (Pydantic v2). Accepts 'specialty' (old) and 'specialization' (new)."""
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    specialization: Optional[str] = Field(
        None,
        max_length=255,
        validation_alias=AliasChoices("specialty", "specialization"),
    )
    bio: Optional[str] = None
    is_active: bool = True
    is_ai_powered: bool = False

    model_config = ConfigDict(populate_by_name=True)


class SpecialistCreate(SpecialistBase):
    """Schema for creating specialist (no id, project_id auto-assigned)."""
    pass


class SpecialistUpdate(BaseModel):
    """Schema for updating specialist (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    specialization: Optional[str] = Field(
        None,
        max_length=255,
        validation_alias=AliasChoices("specialty", "specialization"),
    )
    bio: Optional[str] = None
    is_active: Optional[bool] = None
    is_ai_powered: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)


class SpecialistOut(SpecialistBase):
    """Schema for specialist response (includes id, project_id, timestamps)."""
    id: int
    project_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpecialistShort(BaseModel):
    """Short schema for list view."""
    id: int
    name: str
    role: Optional[str] = None
    specialty: Optional[str] = None
    rate: Optional[int] = None
    delivery: Optional[str] = None
    is_ai: bool = False

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. Схеми Послуг (Services)
# ==========================================


class ServiceInfo(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    available_specialists: int = 0


class ServicesListResponse(BaseModel):
    services: List[ServiceInfo]
    total: int


# ==========================================
# 4. Deep Health (HealthChecker)
# ==========================================


class ComponentHealth(BaseModel):
    component: str = Field(..., example="postgresql")
    status: Literal["healthy", "degraded", "down", "not_configured"]
    latency_ms: float = Field(default=0.0, example=15.5)
    details: dict[str, Any] = Field(default_factory=dict)


class DeepHealthResponse(BaseModel):
    overall_status: Literal["healthy", "degraded", "down"]
    components: list[ComponentHealth]
    summary: dict[str, int | float]
    timestamp: str