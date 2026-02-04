from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.database.connection import get_db
from app.models.specialist import Specialist

router = APIRouter(tags=["Specialists"])

class SpecialistBase(BaseModel):
    """Базова схема"""
    name: str = Field(..., min_length=1, max_length=255)
    service_type: str = Field(..., description="healer | coach | 3d_modeling etc.")
    delivery_method: str = Field(default="human", description="human | ai_assisted | fully_ai")
    specialty: str = Field(..., max_length=200)
    hourly_rate: int = Field(..., ge=0)
    bio: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Налаштування для Pydantic v2 (замість class Config)
    model_config = ConfigDict(from_attributes=True)

class SpecialistCreate(SpecialistBase):
    """Схема створення - ✅ ПОВНІСТЮ БЕЗ niche"""
    telegram_id: Optional[int] = Field(None, description="Підтримує великі ID (BigInteger)")
    portfolio_url: Optional[str] = None
    is_ai_powered: bool = Field(default=False)
    ai_model: Optional[str] = None
    ai_capabilities: Optional[Dict[str, Any]] = None

class SpecialistResponse(SpecialistBase):
    """Схема відповіді"""
    id: int
    is_verified: bool
    is_active: bool
    telegram_id: Optional[int] = None
    portfolio_url: Optional[str] = None
    is_ai_powered: bool
    ai_model: Optional[str] = None
    ai_capabilities: Optional[Dict[str, Any]] = None

# --- Ендпоінти ---

@router.post("/specialists", response_model=SpecialistResponse, status_code=201)
async def create_specialist(
    data: SpecialistCreate,
    db: AsyncSession = Depends(get_db)
):
    """Створення нового спеціаліста"""
    # .model_dump() замість .dict() для Pydantic v2
    new_specialist = Specialist(**data.model_dump())
    
    db.add(new_specialist)
    await db.commit()
    await db.refresh(new_specialist)
    return new_specialist

@router.get("/specialists", response_model=List[SpecialistResponse])
async def get_specialists(
    service_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Отримання списку з фільтром по service_type"""
    query = select(Specialist).where(Specialist.is_active == True)
    if service_type:
        query = query.where(Specialist.service_type == service_type)
    
    result = await db.execute(query)
    return result.scalars().all()
