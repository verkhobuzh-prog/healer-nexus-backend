"""
Pydantic schemas for blog analytics and dashboard.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TrackViewRequest(BaseModel):
    referrer_url: str | None = None
    user_agent: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PostAnalytics(BaseModel):
    post_id: int
    post_title: str
    post_slug: str
    total_views: int
    unique_views: int
    views_today: int
    views_7d: int
    views_30d: int
    avg_daily_views: float
    top_referrer: str
    trend: str
    trend_percent: float

    model_config = ConfigDict(from_attributes=True)


class DailyViewStats(BaseModel):
    date: date
    views_total: int
    views_unique: int

    model_config = ConfigDict(from_attributes=True)


class ReferrerStats(BaseModel):
    source: str
    count: int
    percent: float

    model_config = ConfigDict(from_attributes=True)


class BlogDashboardStats(BaseModel):
    total_posts: int
    published_posts: int
    draft_posts: int
    scheduled_posts: int
    total_views: int
    total_unique_views: int
    views_today: int
    views_7d: int
    views_30d: int
    avg_daily_views: float

    model_config = ConfigDict(from_attributes=True)


class PopularPostItem(BaseModel):
    post_id: int
    title: str
    slug: str
    views: int
    unique_views: int
    published_at: datetime | None
    featured_image_url: str | None
    category_name: str | None

    model_config = ConfigDict(from_attributes=True)


class PopularPostsResponse(BaseModel):
    items: list[PopularPostItem]
    period: str

    model_config = ConfigDict(from_attributes=True)


class BlogDashboardResponse(BaseModel):
    stats: BlogDashboardStats
    popular_posts: list[PopularPostItem]
    daily_views: list[DailyViewStats]
    referrer_breakdown: list[ReferrerStats]

    model_config = ConfigDict(from_attributes=True)


class TrendingPostItem(BaseModel):
    post_id: int
    title: str
    slug: str
    views_current_period: int
    views_previous_period: int
    growth_percent: float
    featured_image_url: str | None

    model_config = ConfigDict(from_attributes=True)
