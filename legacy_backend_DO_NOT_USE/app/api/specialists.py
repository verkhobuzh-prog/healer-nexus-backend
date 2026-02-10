"""Specialists API endpoints with proper error handling and 404/500 behavior."""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.connection import get_db
from app.models.specialist import Specialist
from app.schemas.responses import (
    SpecialistCreate,
    SpecialistOut,
    SpecialistShort,
    SpecialistUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/specialists",
    response_model=SpecialistOut,
    status_code=status.HTTP_201_CREATED,
    summary="Створити спеціаліста",
)
async def create_specialist(
    data: SpecialistCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create new specialist; map schema (specialization) to model (specialty)."""
    try:
        new_spec = Specialist(
            project_id=settings.PROJECT_ID,
            name=data.name,
            role=data.role,
            service_type="general",
            delivery_method="human",
            specialty=data.specialization or "",
            hourly_rate=0,
            bio=data.bio,
            is_active=data.is_active,
            is_ai_powered=data.is_ai_powered,
        )
        db.add(new_spec)
        await db.commit()
        await db.refresh(new_spec)
        logger.info("Created specialist: %s (id=%d)", new_spec.name, new_spec.id)
        return new_spec
    except Exception:
        await db.rollback()
        logger.exception("Failed to create specialist")
        raise HTTPException(
            status_code=500,
            detail="Failed to create specialist",
        )


@router.get(
    "/specialists",
    response_model=List[SpecialistShort],
    summary="Отримати список спеціалістів",
)
async def get_specialists(
    service_type: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List all active specialists for current project."""
    try:
        query = select(Specialist).where(
            Specialist.project_id == settings.PROJECT_ID,
            Specialist.is_active == True,
        )
        if service_type:
            query = query.where(Specialist.service_type == service_type)
        result = await db.execute(query.order_by(Specialist.id.desc()).limit(limit))
        specs = result.scalars().all()
        return [
            SpecialistShort(
                id=s.id,
                name=s.name,
                role=s.role,
                specialty=s.specialty,
                rate=s.hourly_rate,
                delivery=s.delivery_method,
                is_ai=getattr(s, "is_ai_powered", False),
            )
            for s in specs
        ]
    except Exception:
        logger.exception("Failed to list specialists")
        raise HTTPException(status_code=500, detail="Failed to list specialists")


@router.get(
    "/specialists/{spec_id}",
    response_model=SpecialistOut,
    summary="Отримати одного спеціаліста",
)
async def get_specialist(
    spec_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get specialist by ID; returns 404 if not found."""
    try:
        result = await db.execute(
            select(Specialist).where(
                Specialist.id == spec_id,
                Specialist.project_id == settings.PROJECT_ID,
            )
        )
        spec = result.scalar_one_or_none()
        if not spec:
            raise HTTPException(
                status_code=404,
                detail=f"Specialist {spec_id} not found",
            )
        return spec
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get specialist %d", spec_id)
        raise HTTPException(status_code=500, detail="Failed to get specialist")


@router.patch(
    "/specialists/{spec_id}",
    response_model=SpecialistOut,
    summary="Оновити спеціаліста",
)
async def update_specialist(
    spec_id: int,
    data: SpecialistUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update specialist; returns 404 if not found. Maps specialization -> specialty."""
    try:
        result = await db.execute(
            select(Specialist).where(
                Specialist.id == spec_id,
                Specialist.project_id == settings.PROJECT_ID,
            )
        )
        spec = result.scalar_one_or_none()
        if not spec:
            raise HTTPException(
                status_code=404,
                detail=f"Specialist {spec_id} not found",
            )
        update_data = data.model_dump(exclude_unset=True)
        if "specialization" in update_data:
            update_data["specialty"] = update_data.pop("specialization")
        for key, value in update_data.items():
            if hasattr(spec, key):
                setattr(spec, key, value)
        await db.commit()
        await db.refresh(spec)
        logger.info("Updated specialist %d", spec_id)
        return spec
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Failed to update specialist %d", spec_id)
        raise HTTPException(status_code=500, detail="Failed to update specialist")


@router.delete(
    "/specialists/{spec_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити спеціаліста (soft delete)",
)
async def delete_specialist(
    spec_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete (set is_active=False); returns 404 if not found."""
    try:
        result = await db.execute(
            select(Specialist).where(
                Specialist.id == spec_id,
                Specialist.project_id == settings.PROJECT_ID,
            )
        )
        spec = result.scalar_one_or_none()
        if not spec:
            raise HTTPException(
                status_code=404,
                detail=f"Specialist {spec_id} not found",
            )
        spec.is_active = False
        await db.commit()
        logger.info("Soft deleted specialist %d", spec_id)
        return None
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Failed to delete specialist %d", spec_id)
        raise HTTPException(status_code=500, detail="Failed to delete specialist")
