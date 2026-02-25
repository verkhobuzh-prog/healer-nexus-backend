"""
Background task that auto-publishes scheduled blog posts.
Runs every 60 seconds as an asyncio task tied to app lifespan.
"""
from __future__ import annotations

import asyncio
import logging

from app.database.connection import async_session_maker
from app.services.blog_service import BlogService
from app.config import settings

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60


class BlogScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Blog scheduler started (interval: %ds)", CHECK_INTERVAL_SECONDS)

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Blog scheduler stopped")

    async def _run_loop(self) -> None:
        """Main loop: check for scheduled posts every interval."""
        while self._running:
            try:
                await self._check_and_publish()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler error: %s", e, exc_info=True)
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def _check_and_publish(self) -> None:
        """Find and publish all posts whose scheduled_at has passed."""
        project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
        async with async_session_maker() as session:
            try:
                svc = BlogService(session, project_id)
                count = await svc.publish_scheduled_posts()
                if count > 0:
                    logger.info("Auto-published %d scheduled post(s)", count)
            except Exception as e:
                logger.error("Blog scheduler error (non-fatal): %s", e)


blog_scheduler = BlogScheduler()
