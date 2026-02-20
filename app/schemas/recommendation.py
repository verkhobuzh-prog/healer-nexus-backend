"""Recommendation funnel schemas."""
from __future__ import annotations

from pydantic import BaseModel


class RecommendationEvent(BaseModel):
    specialist_id: int
    source: str = "chat"  # chat | search | popular | blog
    conversation_id: int | None = None


class RecommendationStats(BaseModel):
    specialist_id: int
    specialist_name: str
    total_recommendations: int
    details_viewed: int
    bookings_created: int
    links_revealed: int
    total_link_clicks: int
    click_breakdown: dict  # {"telegram": 5, "instagram": 3}
    conversion_rate: float  # bookings / recommendations * 100


class PlatformStats(BaseModel):
    total_specialists: int
    total_recommendations: int
    total_bookings: int
    total_link_reveals: int
    avg_conversion_rate: float
    top_specialists: list[RecommendationStats]


class LinkAccessResponse(BaseModel):
    """Returned when user requests social links."""

    accessible: bool
    reason: str | None = None
    links: list[dict] | None = None
