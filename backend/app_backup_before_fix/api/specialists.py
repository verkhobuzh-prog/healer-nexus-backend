from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.database.connection import get_db
from app.models.specialist import Specialist
from app.schemas.responses import SpecialistOut, SpecialistShort, SpecialistCreate, SpecialistUpdate

# Створюємо роутер. Переконайтеся, що в main.py ви НЕ дублюєте prefix та tags.
router = APIRouter(prefix="/specialists", tags=["Specialists"])

# --- CREATE ---
@router.post("/", response_model=SpecialistOut, status_code=status.HTTP_201_CREATED, summary="Створити спеціаліста")
async def create_specialist(data: SpecialistCreate, db: AsyncSession = Depends(get_db)):
    """Додає нового спеціаліста в базу даних"""
    new_spec = Specialist(**data.model_dump())
    db.add(new_spec)
    await db.commit()
    await db.refresh(new_spec)
    return new_spec

# --- GET ALL (З мапінгом для фронтенду) ---
@router.get("/", response_model=List[SpecialistShort], summary="Отримати список спеціалістів")
async def get_specialists(
    service_type: Optional[str] = None, 
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Отримує список активних спеціалістів. 
    Автоматично мапить hourly_rate -> rate та delivery_method -> delivery.
    """
    query = select(Specialist).where(Specialist.is_active == True)
    
    if service_type:
        query = query.where(Specialist.service_type == service_type)
    
    result = await db.execute(query.order_by(Specialist.id.desc()).limit(limit))
    specs = result.scalars().all()
    
    # Використовуємо SpecialistShort для мапінгу полів під потреби фронтенду
    return [
        SpecialistShort(
            name=s.name,
            specialty=s.specialty,
            rate=s.hourly_rate,
            delivery=s.delivery_method,
            is_ai=getattr(s, "is_ai_powered", False)
        )
        for s in specs
    ]

# --- UPDATE ---
@router.patch("/{spec_id}", response_model=SpecialistOut, summary="Оновити дані спеціаліста")
async def update_specialist(spec_id: int, data: SpecialistUpdate, db: AsyncSession = Depends(get_db)):
    """Часткове оновлення полів спеціаліста"""
    result = await db.execute(select(Specialist).where(Specialist.id == spec_id))
    spec = result.scalar_one_or_none()
    
    if not spec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Specialist not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(spec, key, value)
    
    await db.commit()
    await db.refresh(spec)
    return spec

# --- DELETE (Виправлений для Swagger) ---
@router.delete("/{spec_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Видалити спеціаліста")
async def delete_specialist(spec_id: int, db: AsyncSession = Depends(get_db)):
    """
    Видаляє спеціаліста з бази даних.
    Повертає порожню відповідь (204 No Content), щоб уникнути помилок схеми в Swagger.
    """
    # Перевірка наявності
    result = await db.execute(select(Specialist).where(Specialist.id == spec_id))
    spec = result.scalar_one_or_none()
    
    if not spec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Specialist not found")
    
    # Виконуємо видалення
    await db.execute(delete(Specialist).where(Specialist.id == spec_id))
    await db.commit()
    
    # КРИТИЧНО: Повертаємо чистий Response без тіла
    return Response(status_code=status.HTTP_204_NO_CONTENT)
