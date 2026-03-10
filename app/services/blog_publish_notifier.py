"""
Orchestrates notifications when a blog post is published.
Called from blog_service.py after publish and from blog_scheduler after auto-publish.
Never raises — all errors are logged and swallowed.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post import BlogPost
from app.models.practitioner_profile import PractitionerProfile
from app.services.blog_telegram_service import blog_telegram_service
from app.config import settings

logger = logging.getLogger(__name__)


async def notify_post_published(
    session: AsyncSession,
    post: BlogPost,
    base_url: str | None = None,
) -> None:
    """
    Send notifications for a newly published post.
    Currently: Telegram channel announcement.
    """
    try:
        r = await session.execute(
            select(PractitionerProfile).where(
                PractitionerProfile.id == post.practitioner_id
            )
        )
        profile = r.scalar_one_or_none()
        if not profile:
            logger.warning("No practitioner profile for post %d", post.id)
            return

        channel_id = getattr(profile, "telegram_channel_id", None)
        if not channel_id or not str(channel_id).strip():
            logger.debug("No Telegram channel for practitioner %d, skipping", profile.id)
            return

        site_url = base_url or getattr(settings, "BASE_URL", "http://localhost:8000")
        post_url = f"{site_url.rstrip('/')}/blog/{profile.id}/{post.slug}"

        author_name = getattr(profile, "display_name", None)
        if not author_name:
            try:
                from app.models.specialist import Specialist
                spec_r = await session.execute(
                    select(Specialist).where(
                        Specialist.id == getattr(profile, "specialist_id", 0)
                    )
                )
                spec = spec_r.scalar_one_or_none()
                author_name = getattr(spec, "name", None) if spec else None
            except Exception as e:
                logger.warning("blog_publish_notifier failed: %s", e)

        tag_names = [t.name for t in post.tags] if getattr(post, "tags", None) else []
        excerpt = (post.content or "")[:300]

        await blog_telegram_service.send_post_announcement(
            channel_id=str(channel_id).strip(),
            title=post.title,
            excerpt=excerpt,
            post_url=post_url,
            reading_time=post.reading_time_minutes,
            tags=tag_names,
            featured_image_url=post.featured_image_url,
            author_name=author_name,
        )
    except Exception as e:
        logger.error(
            "Failed to send publish notification for post %d: %s",
            post.id,
            e,
            exc_info=True,
        )
