"""
Content management: блоги, портфоліо, продукти (SpecialistContent).
POST /api/content/create, GET /api/content/feed, GET /api/content/{id}.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.specialist_content import SpecialistContent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content"])


class ContentCreate(BaseModel):
    """Тіло для створення контенту."""
    specialist_id: int = Field(..., ge=1)
    content_type: str = Field(..., description="blog | portfolio_item | product_sale | video")
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    media_urls: list[str] = Field(default_factory=list)
    price: Optional[int] = Field(None, ge=0)
    is_for_sale: bool = False
    target_audience: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ContentResponse(BaseModel):
    """Відповідь з контентом."""
    id: int
    specialist_id: int
    content_type: str
    title: str
    description: Optional[str] = None
    media_urls: list[Any] = Field(default_factory=list)
    price: Optional[int] = None
    is_for_sale: bool = False
    sold: bool = False
    views: int = 0
    likes: int = 0
    leads_generated: int = 0
    ai_promoted: bool = False
    promotion_score: float = 0.0
    target_audience: list[Any] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


@router.post("/create", response_model=ContentResponse, status_code=201)
async def create_content(
    data: ContentCreate,
    db: AsyncSession = Depends(get_db),
) -> SpecialistContent:
    """Створення контенту (блог, портфоліо, продукт)."""
    allowed = ("blog", "portfolio_item", "product_sale", "video")
    if data.content_type not in allowed:
        raise HTTPException(400, detail=f"content_type має бути один з: {allowed}")
    row = SpecialistContent(
        specialist_id=data.specialist_id,
        content_type=data.content_type,
        title=data.title,
        description=data.description,
        media_urls=data.media_urls,
        price=data.price,
        is_for_sale=data.is_for_sale,
        target_audience=data.target_audience,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("Content created id=%s type=%s specialist_id=%s", row.id, row.content_type, row.specialist_id)
    return row


@router.get("/feed", response_model=list[ContentResponse])
async def get_content_feed(
    content_type: Optional[str] = None,
    specialist_id: Optional[int] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[SpecialistContent]:
    """Стрічка контенту з опційними фільтрами."""
    q = select(SpecialistContent).order_by(desc(SpecialistContent.id)).limit(min(limit, 100))
    if content_type:
        q = q.where(SpecialistContent.content_type == content_type)
    if specialist_id is not None:
        q = q.where(SpecialistContent.specialist_id == specialist_id)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{id}", response_model=ContentResponse)
async def get_content_by_id(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> SpecialistContent:
    """Отримати контент за id."""
    result = await db.execute(select(SpecialistContent).where(SpecialistContent.id == id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, detail="Content not found")
    return row
