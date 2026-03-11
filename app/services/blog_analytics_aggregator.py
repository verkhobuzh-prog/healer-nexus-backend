"""
Background task to aggregate blog_post_views into blog_analytics_daily.
Runs once daily (or on demand). Aggregates the given date (default: yesterday).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta, timezone, datetime

from app.database.connection import async_session_maker
from app.services.blog_analytics_service import BlogAnalyticsService
from app.config import settings

logger = logging.getLogger(__name__)

AGGREGATION_HOUR = 2  # Run at 2 AM UTC


class BlogAnalyticsAggregator:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Blog analytics aggregator started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Blog analytics aggregator stopped")

    async def _run_loop(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc)
            if now.hour == AGGREGATION_HOUR:
                yesterday = date.today() - timedelta(days=1)
                await self._aggregate_for_date(yesterday)
                await asyncio.sleep(3600)
            else:
                await asyncio.sleep(1800)

    async def _aggregate_for_date(self, target_date: date) -> None:
        project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
        try:
            async with async_session_maker() as session:
                svc = BlogAnalyticsService(session, project_id)
                await svc.aggregate_daily(target_date)
                await session.commit()
            logger.info("Aggregated analytics for %s", target_date)
        except Exception as e:
            logger.error(
                "Analytics aggregation failed for %s: %s",
                target_date,
                e,
                exc_info=True,
            )

    async def aggregate_now(self, target_date: date | str | None = None) -> None:
        """Manual trigger for aggregation (e.g., backfill)."""
        target = target_date or (date.today() - timedelta(days=1))
        if isinstance(target, str):
            target = date.fromisoformat(target)
        await self._aggregate_for_date(target)


blog_analytics_aggregator = BlogAnalyticsAggregator()
