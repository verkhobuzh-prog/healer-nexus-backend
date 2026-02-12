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
    """
    Схема створення - ✅ ПОВНІСТЮ БЕЗ niche
    ✅ FIX #1: telegram_id тепер None за замовчуванням (не 0), щоб уникнути UNIQUE constraint
    """
    telegram_id: Optional[int] = Field(
        None,
        ge=1,
        examples=[123456789, None],
        description="Підтримує великі ID (BigInteger). Must be positive or null."
    )
    portfolio_url: Optional[str] = None
    is_ai_powered: bool = Field(default=False)
    ai_model: Optional[str] = None
    ai_capabilities: Optional[Dict[str, Any]] = None

class SpecialistResponse(SpecialistBase):
    """Схема відповіді"""
    id: int
    service_type: str
    service_types: Optional[List[str]] = None
    is_verified: bool
    is_active: bool
    telegram_id: Optional[int] = None
    portfolio_url: Optional[str] = None
    is_ai_powered: bool
    ai_model: Optional[str] = None
    ai_capabilities: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class SpecialistUpdate(BaseModel):
    """Схема оновлення — усі поля опційні; hourly_rate > 0 якщо передано."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    service_types: Optional[List[str]] = None
    hourly_rate: Optional[int] = Field(None, gt=0)
    bio: Optional[str] = None
    specialty: Optional[str] = Field(None, max_length=200)
    delivery_method: Optional[str] = Field(None, description="human | ai_assisted | fully_ai")

    model_config = ConfigDict(from_attributes=True)

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


@router.get("/specialists/{specialist_id}", response_model=SpecialistResponse)
async def get_specialist_by_id(
    specialist_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ FIX #3: Додано GET endpoint для отримання одного спеціаліста за ID
    Повертає 404 якщо спеціаліст не знайдений
    """
    result = await db.execute(
        select(Specialist).where(Specialist.id == specialist_id)
    )
    specialist = result.scalar_one_or_none()
    
    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")
    
    return specialist


@router.put("/specialists/{specialist_id}", response_model=SpecialistResponse)
async def update_specialist(
    specialist_id: int,
    data: SpecialistUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Оновлення спеціаліста (лише передані поля)."""
    result = await db.execute(select(Specialist).where(Specialist.id == specialist_id))
    specialist = result.scalar_one_or_none()
    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(specialist, key, value)
    await db.commit()
    await db.refresh(specialist)
    return specialist


@router.delete("/specialists/{specialist_id}")
async def delete_specialist(
    specialist_id: int,
    db: AsyncSession = Depends(get_db)
):
    """М'яке видалення: is_active = False."""
    result = await db.execute(select(Specialist).where(Specialist.id == specialist_id))
    specialist = result.scalar_one_or_none()
    if not specialist:
        raise HTTPException(status_code=404, detail="Specialist not found")
    specialist.is_active = False
    await db.commit()
    return {"message": "Specialist deactivated", "id": specialist_id}