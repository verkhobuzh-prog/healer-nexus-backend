"""Recommendation funnel stats API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_specialist, require_role
from app.config import settings
from app.database.connection import get_db
from app.models.specialist import Specialist
from app.schemas.recommendation import RecommendationStats, PlatformStats
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


def _project_id() -> str:
    return getattr(settings, "PROJECT_ID", "healer_nexus")


@router.get("/my-stats", response_model=RecommendationStats)
async def get_my_recommendation_stats(
    days: int | None = Query(None, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    specialist: Specialist = Depends(get_current_specialist),
):
    """Get recommendation funnel stats for the current specialist."""
    project_id = _project_id()
    rec_svc = RecommendationService(db, project_id)
    stats = await rec_svc.get_specialist_stats(specialist.id, days=days)
    return stats


@router.get("/platform-stats", response_model=PlatformStats)
async def get_platform_recommendation_stats(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Get overall platform recommendation stats (admin only)."""
    project_id = _project_id()
    rec_svc = RecommendationService(db, project_id)
    return await rec_svc.get_platform_stats(limit=limit)


@router.get("/specialist/{specialist_id}/stats", response_model=RecommendationStats)
async def get_specialist_recommendation_stats(
    specialist_id: int,
    days: int | None = Query(None, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Get recommendation stats for a specific specialist (admin only)."""
    project_id = _project_id()
    rec_svc = RecommendationService(db, project_id)
    stats = await rec_svc.get_specialist_stats(specialist_id, days=days)
    if not stats:
        raise HTTPException(status_code=404, detail="Specialist not found or no stats")
    return stats
