"""
Blog analytics API: dashboard, post stats, popular/trending, aggregation trigger.
Prefix: /api/blog/analytics
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.api.deps import get_current_practitioner
from app.models.practitioner_profile import PractitionerProfile
from app.services.blog_service import BlogService
from app.services.blog_analytics_service import BlogAnalyticsService
from app.services.blog_analytics_aggregator import blog_analytics_aggregator
from app.schemas.blog_analytics import (
    PostAnalytics,
    DailyViewStats,
    ReferrerStats,
    BlogDashboardStats,
    BlogDashboardResponse,
    PopularPostItem,
    PopularPostsResponse,
    TrendingPostItem,
)
from app.config import settings

router = APIRouter(prefix="/api/blog/analytics", tags=["Blog Analytics"])


def _project_id() -> str:
    return getattr(settings, "PROJECT_ID", "healer_nexus")


# ─── Practitioner dashboard (auth required) ───


@router.get("/dashboard", response_model=BlogDashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Practitioner blog performance dashboard."""
    project_id = _project_id()
    svc = BlogAnalyticsService(db, project_id)
    stats = await svc.get_dashboard_stats(practitioner.id)
    popular_posts = await svc.get_popular_posts(
        practitioner_id=practitioner.id,
        period="30d",
        limit=10,
    )
    daily_views = await svc.get_dashboard_daily_views(
        practitioner_id=practitioner.id,
        days=30,
    )
    referrer_breakdown = await svc.get_referrer_breakdown(
        practitioner_id=practitioner.id,
        days=30,
    )
    return BlogDashboardResponse(
        stats=stats,
        popular_posts=popular_posts,
        daily_views=daily_views,
        referrer_breakdown=referrer_breakdown,
    )


@router.get("/dashboard/daily", response_model=list[DailyViewStats])
async def get_dashboard_daily(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Daily view totals for practitioner's posts (last N days)."""
    project_id = _project_id()
    svc = BlogAnalyticsService(db, project_id)
    return await svc.get_dashboard_daily_views(
        practitioner_id=practitioner.id,
        days=days,
    )


# ─── Single post analytics (auth required, ownership check) ───


async def _ensure_post_ownership(
    db: AsyncSession,
    project_id: str,
    post_id: int,
    practitioner_id: int,
) -> None:
    blog_svc = BlogService(db, project_id)
    post = await blog_svc.get_post_by_id(post_id)
    if not post or post.practitioner_id != practitioner_id:
        raise HTTPException(status_code=404, detail="Post not found or access denied")


@router.get("/posts/{post_id}/stats", response_model=PostAnalytics)
async def get_post_stats(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Analytics for a single post (ownership required)."""
    project_id = _project_id()
    await _ensure_post_ownership(db, project_id, post_id, practitioner.id)
    svc = BlogAnalyticsService(db, project_id)
    analytics = await svc.get_post_analytics(post_id, practitioner_id=practitioner.id)
    if not analytics:
        raise HTTPException(status_code=404, detail="Post not found")
    return analytics


@router.get("/posts/{post_id}/daily", response_model=list[DailyViewStats])
async def get_post_daily(
    post_id: int,
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Daily view breakdown for a post (ownership required)."""
    project_id = _project_id()
    await _ensure_post_ownership(db, project_id, post_id, practitioner.id)
    svc = BlogAnalyticsService(db, project_id)
    return await svc.get_post_daily_views(
        post_id, days=days, practitioner_id=practitioner.id
    )


@router.get("/posts/{post_id}/referrers", response_model=list[ReferrerStats])
async def get_post_referrers(
    post_id: int,
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Referrer breakdown for a post (ownership required)."""
    project_id = _project_id()
    await _ensure_post_ownership(db, project_id, post_id, practitioner.id)
    svc = BlogAnalyticsService(db, project_id)
    return await svc.get_post_referrers(
        post_id, days=days, practitioner_id=practitioner.id
    )


# ─── Public endpoints (no auth) ───


@router.get("/popular", response_model=PopularPostsResponse)
async def get_popular(
    period: str = Query("30d", description="7d, 30d, or all"),
    limit: int = Query(10, ge=1, le=50),
    practitioner_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Top posts by views in period (public)."""
    project_id = _project_id()
    svc = BlogAnalyticsService(db, project_id)
    items = await svc.get_popular_posts(
        practitioner_id=practitioner_id,
        period=period,
        limit=limit,
    )
    return PopularPostsResponse(items=items, period=period)


@router.get("/trending", response_model=list[TrendingPostItem])
async def get_trending(
    limit: int = Query(5, ge=1, le=20),
    practitioner_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Trending posts (highest growth last 7d vs previous 7d). Public."""
    project_id = _project_id()
    svc = BlogAnalyticsService(db, project_id)
    return await svc.get_trending_posts(
        practitioner_id=practitioner_id,
        limit=limit,
    )


# ─── Admin: manual aggregation (auth required) ───


@router.post("/aggregate")
async def trigger_aggregate(
    date_param: Optional[date] = Query(None, alias="date"),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Trigger daily aggregation for a given date (default: yesterday)."""
    target = date_param or (date.today() - timedelta(days=1))
    if isinstance(target, str):
        target = date.fromisoformat(target)
    # Ensure date object for PostgreSQL (no date = character varying)
    await blog_analytics_aggregator.aggregate_now(target_date=target)
    return {"status": "ok", "date": target.isoformat()}
