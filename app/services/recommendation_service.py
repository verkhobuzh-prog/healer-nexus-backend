"""Recommendation funnel: record events and compute stats."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.specialist_recommendation import SpecialistRecommendation
from app.models.specialist import Specialist
from app.models.booking import Booking
from app.schemas.recommendation import RecommendationStats, PlatformStats


class RecommendationService:
    def __init__(self, session: AsyncSession, project_id: str):
        self.session = session
        self.project_id = project_id

    async def record_recommendation(
        self,
        specialist_id: int,
        user_id: int | None,
        source: str = "chat",
        conversation_id: int | None = None,
    ) -> SpecialistRecommendation:
        rec = SpecialistRecommendation(
            project_id=self.project_id,
            specialist_id=specialist_id,
            user_id=user_id,
            conversation_id=conversation_id,
            source=source,
            recommended_at=datetime.now(timezone.utc),
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def record_details_viewed(self, specialist_id: int, user_id: int) -> None:
        rec = await self._find_latest(specialist_id, user_id)
        if rec and not rec.details_viewed:
            rec.details_viewed = True
            rec.details_viewed_at = datetime.now(timezone.utc)

    async def record_booked(
        self, specialist_id: int, user_id: int, booking_id: int
    ) -> None:
        rec = await self._find_latest(specialist_id, user_id)
        if rec:
            rec.booked = True
            rec.booked_at = datetime.now(timezone.utc)
            rec.booking_id = booking_id

    async def record_links_revealed(self, specialist_id: int, user_id: int) -> None:
        rec = await self._find_latest(specialist_id, user_id)
        if rec and not rec.links_revealed:
            rec.links_revealed = True
            rec.links_revealed_at = datetime.now(timezone.utc)

    async def record_link_click(
        self, specialist_id: int, user_id: int, platform: str
    ) -> None:
        rec = await self._find_latest(specialist_id, user_id)
        if rec:
            clicks = dict(rec.link_clicks or {})
            clicks[platform] = clicks.get(platform, 0) + 1
            rec.link_clicks = clicks
            flag_modified(rec, "link_clicks")

    async def can_access_links(self, specialist_id: int, user_id: int) -> bool:
        r = await self.session.execute(
            select(Booking).where(
                Booking.specialist_id == specialist_id,
                Booking.user_id == user_id,
                Booking.status.in_(["confirmed", "completed"]),
            )
        )
        return r.scalar_one_or_none() is not None

    async def get_specialist_stats(
        self, specialist_id: int, days: int | None = None
    ) -> RecommendationStats | None:
        q = select(SpecialistRecommendation).where(
            SpecialistRecommendation.project_id == self.project_id,
            SpecialistRecommendation.specialist_id == specialist_id,
        )
        if days is not None:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            q = q.where(SpecialistRecommendation.recommended_at >= since)
        r = await self.session.execute(q)
        rows = list(r.scalars().all())
        if not rows:
            spec = await self.session.get(Specialist, specialist_id)
            name = spec.name if spec else ""
            return RecommendationStats(
                specialist_id=specialist_id,
                specialist_name=name,
                total_recommendations=0,
                details_viewed=0,
                bookings_created=0,
                links_revealed=0,
                total_link_clicks=0,
                click_breakdown={},
                conversion_rate=0.0,
            )
        total = len(rows)
        details_viewed = sum(1 for x in rows if x.details_viewed)
        booked = sum(1 for x in rows if x.booked)
        links_revealed = sum(1 for x in rows if x.links_revealed)
        click_breakdown: dict = {}
        for row in rows:
            for k, v in (row.link_clicks or {}).items():
                click_breakdown[k] = click_breakdown.get(k, 0) + v
        total_clicks = sum(click_breakdown.values())
        spec = await self.session.get(Specialist, specialist_id)
        name = spec.name if spec else ""
        conversion = (booked / total * 100) if total else 0.0
        return RecommendationStats(
            specialist_id=specialist_id,
            specialist_name=name,
            total_recommendations=total,
            details_viewed=details_viewed,
            bookings_created=booked,
            links_revealed=links_revealed,
            total_link_clicks=total_clicks,
            click_breakdown=click_breakdown,
            conversion_rate=round(conversion, 2),
        )

    async def get_platform_stats(self, limit: int = 10) -> PlatformStats:
        q = select(SpecialistRecommendation).where(
            SpecialistRecommendation.project_id == self.project_id
        )
        r = await self.session.execute(q)
        rows = list(r.scalars().all())
        by_specialist: dict[int, list] = {}
        for row in rows:
            by_specialist.setdefault(row.specialist_id, []).append(row)
        top: list[RecommendationStats] = []
        for sid, recs in sorted(
            by_specialist.items(), key=lambda x: -len(x[1])
        )[:limit]:
            stats = await self.get_specialist_stats(sid, days=None)
            if stats:
                top.append(stats)
        total_specialists = len(by_specialist)
        total_recs = len(rows)
        total_bookings = sum(1 for x in rows if x.booked)
        total_reveals = sum(1 for x in rows if x.links_revealed)
        avg_conversion = (
            sum(s.conversion_rate for s in top) / len(top) if top else 0.0
        )
        return PlatformStats(
            total_specialists=total_specialists,
            total_recommendations=total_recs,
            total_bookings=total_bookings,
            total_link_reveals=total_reveals,
            avg_conversion_rate=round(avg_conversion, 2),
            top_specialists=top,
        )

    async def _find_latest(
        self, specialist_id: int, user_id: int
    ) -> SpecialistRecommendation | None:
        r = await self.session.execute(
            select(SpecialistRecommendation)
            .where(
                SpecialistRecommendation.specialist_id == specialist_id,
                SpecialistRecommendation.user_id == user_id,
                SpecialistRecommendation.project_id == self.project_id,
            )
            .order_by(SpecialistRecommendation.recommended_at.desc())
            .limit(1)
        )
        return r.scalar_one_or_none()
