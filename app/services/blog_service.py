"""
Blog CRUD and slug generation. Async SQLAlchemy 2.0, multi-tenant by project_id.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blog_post import BlogPost, PostStatus
from app.models.blog_post_tag import BlogPostTag
from app.models.blog_tag import BlogTag
from app.services.blog_slug import generate_slug
from app.services.blog_taxonomy_service import BlogTaxonomyService

logger = logging.getLogger(__name__)


async def ensure_unique_slug(
    session: AsyncSession,
    project_id: str,
    slug: str,
    exclude_post_id: Optional[int] = None,
) -> str:
    """Append -2, -3, ... if slug exists within project."""
    base = slug
    candidate = base
    n = 1
    while True:
        q = select(BlogPost.id).where(
            BlogPost.project_id == project_id,
            BlogPost.slug == candidate,
        )
        if exclude_post_id is not None:
            q = q.where(BlogPost.id != exclude_post_id)
        r = await session.execute(q)
        if r.scalar_one_or_none() is None:
            return candidate
        n += 1
        candidate = f"{base}-{n}"


class BlogService:
    def __init__(self, session: AsyncSession, project_id: str):
        self.session = session
        self.project_id = project_id

    async def create_post(
        self,
        practitioner_id: int,
        title: str,
        content: str = "",
        editor_type: str = "markdown",
        featured_image_url: Optional[str] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        telegram_discussion_url: Optional[str] = None,
        category_id: Optional[int] = None,
        tag_names: Optional[list[str]] = None,
    ) -> BlogPost:
        slug = generate_slug(title)
        slug = await ensure_unique_slug(self.session, self.project_id, slug)
        post = BlogPost(
            project_id=self.project_id,
            practitioner_id=practitioner_id,
            title=title,
            slug=slug,
            content=content,
            editor_type=editor_type,
            status=PostStatus.DRAFT.value,
            featured_image_url=featured_image_url,
            meta_title=meta_title,
            meta_description=meta_description,
            telegram_discussion_url=telegram_discussion_url,
            category_id=category_id,
        )
        self.session.add(post)
        await self.session.flush()
        if tag_names:
            tax = BlogTaxonomyService(self.session, self.project_id)
            tags = await tax.get_or_create_tags(tag_names)
            for tag in tags:
                self.session.add(BlogPostTag(post_id=post.id, tag_id=tag.id))
            for tag in tags:
                await tax.increment_tag_usage(tag.id, commit=False)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def create_ai_draft(
        self,
        practitioner_id: int,
        title: str,
        content: str,
        editor_type: str = "markdown",
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        ai_prompt_topic: Optional[str] = None,
    ) -> BlogPost:
        slug = generate_slug(title)
        slug = await ensure_unique_slug(self.session, self.project_id, slug)
        post = BlogPost(
            project_id=self.project_id,
            practitioner_id=practitioner_id,
            title=title,
            slug=slug,
            content=content,
            editor_type=editor_type,
            status=PostStatus.DRAFT.value,
            meta_title=meta_title,
            meta_description=meta_description,
            ai_generated=True,
            ai_prompt_topic=ai_prompt_topic,
        )
        self.session.add(post)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def get_post_by_id(self, post_id: int) -> Optional[BlogPost]:
        r = await self.session.execute(
            select(BlogPost)
            .where(BlogPost.id == post_id, BlogPost.project_id == self.project_id)
            .options(
                selectinload(BlogPost.practitioner),
                selectinload(BlogPost.category),
                selectinload(BlogPost.tags),
            )
        )
        return r.scalar_one_or_none()

    async def get_post_by_slug(self, slug: str) -> Optional[BlogPost]:
        r = await self.session.execute(
            select(BlogPost)
            .where(
                BlogPost.project_id == self.project_id,
                BlogPost.slug == slug,
            )
            .options(
                selectinload(BlogPost.practitioner),
                selectinload(BlogPost.category),
                selectinload(BlogPost.tags),
            )
        )
        return r.scalar_one_or_none()

    async def list_posts(
        self,
        practitioner_id: Optional[int] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BlogPost], int]:
        q = select(BlogPost).where(BlogPost.project_id == self.project_id)
        count_q = select(func.count(BlogPost.id)).where(
            BlogPost.project_id == self.project_id
        )
        if practitioner_id is not None:
            q = q.where(BlogPost.practitioner_id == practitioner_id)
            count_q = count_q.where(BlogPost.practitioner_id == practitioner_id)
        if status is not None:
            q = q.where(BlogPost.status == status)
            count_q = count_q.where(BlogPost.status == status)
        if category_id is not None:
            q = q.where(BlogPost.category_id == category_id)
            count_q = count_q.where(BlogPost.category_id == category_id)
        total_r = await self.session.execute(count_q)
        total = total_r.scalar() or 0
        q = (
            q.options(
                selectinload(BlogPost.practitioner),
                selectinload(BlogPost.category),
                selectinload(BlogPost.tags),
            )
            .order_by(BlogPost.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        r = await self.session.execute(q)
        posts = list(r.scalars().all())
        return posts, total

    async def list_public_posts(
        self,
        practitioner_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BlogPost], int]:
        return await self.list_posts(
            practitioner_id=practitioner_id,
            status=PostStatus.PUBLISHED.value,
            page=page,
            page_size=page_size,
        )

    async def list_posts_by_category_slug(
        self,
        category_slug: str,
        practitioner_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BlogPost], int]:
        from app.models.blog_category import BlogCategory
        r = await self.session.execute(
            select(BlogCategory.id).where(
                BlogCategory.project_id == self.project_id,
                BlogCategory.slug == category_slug,
                BlogCategory.is_active == True,
            )
        )
        cat_id = r.scalar_one_or_none()
        if cat_id is None:
            return [], 0
        return await self.list_posts(
            practitioner_id=practitioner_id,
            status=PostStatus.PUBLISHED.value,
            category_id=cat_id,
            page=page,
            page_size=page_size,
        )

    async def list_posts_by_tag_slug(
        self,
        tag_slug: str,
        practitioner_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BlogPost], int]:
        r = await self.session.execute(
            select(BlogTag.id).where(
                BlogTag.project_id == self.project_id,
                BlogTag.slug == tag_slug,
            )
        )
        tag_id = r.scalar_one_or_none()
        if tag_id is None:
            return [], 0
        q = (
            select(BlogPost)
            .where(BlogPost.project_id == self.project_id, BlogPost.status == PostStatus.PUBLISHED.value)
            .where(BlogPost.id.in_(select(BlogPostTag.post_id).where(BlogPostTag.tag_id == tag_id)))
        )
        count_q = (
            select(func.count(BlogPost.id))
            .where(BlogPost.project_id == self.project_id, BlogPost.status == PostStatus.PUBLISHED.value)
            .where(BlogPost.id.in_(select(BlogPostTag.post_id).where(BlogPostTag.tag_id == tag_id)))
        )
        if practitioner_id is not None:
            q = q.where(BlogPost.practitioner_id == practitioner_id)
            count_q = count_q.where(BlogPost.practitioner_id == practitioner_id)
        total_r = await self.session.execute(count_q)
        total = total_r.scalar() or 0
        q = (
            q.options(
                selectinload(BlogPost.practitioner),
                selectinload(BlogPost.category),
                selectinload(BlogPost.tags),
            )
            .order_by(BlogPost.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        r = await self.session.execute(q)
        return list(r.scalars().all()), total

    async def update_post(
        self,
        post_id: int,
        practitioner_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        editor_type: Optional[str] = None,
        featured_image_url: Optional[str] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        telegram_discussion_url: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        tag_names: Optional[list[str]] = None,
    ) -> Optional[BlogPost]:
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return None
        tax = BlogTaxonomyService(self.session, self.project_id)
        if tag_names is not None:
            old_tag_ids = {t.id for t in post.tags}
            new_tags = await tax.get_or_create_tags(tag_names)
            new_tag_ids = {t.id for t in new_tags}
            for tag_id in old_tag_ids - new_tag_ids:
                await tax.decrement_tag_usage(tag_id, commit=False)
            for tag in new_tags:
                if tag.id not in old_tag_ids:
                    await tax.increment_tag_usage(tag.id, commit=False)
            await self.session.execute(delete(BlogPostTag).where(BlogPostTag.post_id == post_id))
            for tag in new_tags:
                self.session.add(BlogPostTag(post_id=post_id, tag_id=tag.id))
        if title is not None:
            post.title = title
            new_slug = generate_slug(title)
            post.slug = await ensure_unique_slug(
                self.session, self.project_id, new_slug, exclude_post_id=post_id
            )
        if content is not None:
            post.content = content
        if editor_type is not None:
            post.editor_type = editor_type
        if featured_image_url is not None:
            post.featured_image_url = featured_image_url
        if meta_title is not None:
            post.meta_title = meta_title
        if meta_description is not None:
            post.meta_description = meta_description
        if telegram_discussion_url is not None:
            post.telegram_discussion_url = telegram_discussion_url
        if status is not None:
            post.status = status
        if category_id is not None:
            post.category_id = category_id
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def publish_post(
        self,
        post_id: int,
        practitioner_id: int,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
    ) -> Optional[BlogPost]:
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return None
        if not (post.content and post.content.strip()):
            return None
        post.status = PostStatus.PUBLISHED.value
        post.published_at = post.published_at or datetime.now(timezone.utc)
        if meta_title is not None:
            post.meta_title = meta_title
        if meta_description is not None:
            post.meta_description = meta_description
        if not post.meta_description or not post.meta_description.strip():
            plain = re.sub(r"<[^>]+>", "", post.content)
            plain = re.sub(r"\s+", " ", plain).strip()
            post.meta_description = (plain[:497] + "…") if len(plain) > 500 else plain
        await self.session.commit()
        await self.session.refresh(post)
        try:
            from app.services.blog_publish_notifier import notify_post_published
            await notify_post_published(self.session, post)
        except Exception as e:
            logger.warning("notify_post_published failed: %s", e)
        return post

    async def unpublish_post(self, post_id: int, practitioner_id: int) -> Optional[BlogPost]:
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return None
        post.status = PostStatus.DRAFT.value
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def schedule_post(
        self,
        post_id: int,
        practitioner_id: int,
        scheduled_at: datetime,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
    ) -> Optional[BlogPost]:
        """Schedule post for future publish. scheduled_at must be at least 5 minutes in the future (UTC)."""
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return None
        if not (post.content and post.content.strip()):
            return None
        now = datetime.now(timezone.utc)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        min_future = now.timestamp() + 5 * 60
        if scheduled_at.timestamp() < min_future:
            return None
        post.status = PostStatus.SCHEDULED.value
        post.scheduled_at = scheduled_at
        if meta_title is not None:
            post.meta_title = meta_title
        if meta_description is not None:
            post.meta_description = meta_description
        if not post.meta_description or not post.meta_description.strip():
            plain = re.sub(r"<[^>]+>", "", post.content)
            plain = re.sub(r"\s+", " ", plain).strip()
            post.meta_description = (plain[:497] + "…") if len(plain) > 500 else plain
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def unschedule_post(self, post_id: int, practitioner_id: int) -> Optional[BlogPost]:
        """Revert scheduled post back to draft and clear scheduled_at."""
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return None
        post.status = PostStatus.DRAFT.value
        post.scheduled_at = None
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def publish_scheduled_posts(self) -> int:
        """Find posts where status=SCHEDULED and scheduled_at <= now(), publish each. Commits per post."""
        now = datetime.now(timezone.utc)
        r = await self.session.execute(
            select(BlogPost)
            .where(
                BlogPost.project_id == self.project_id,
                BlogPost.status == PostStatus.SCHEDULED.value,
                BlogPost.scheduled_at <= now,
            )
            .options(selectinload(BlogPost.tags))
        )
        posts = list(r.scalars().all())
        count = 0
        for post in posts:
            try:
                post.status = PostStatus.PUBLISHED.value
                post.published_at = now
                post.scheduled_at = None
                await self.session.commit()
                count += 1
                try:
                    from app.services.blog_publish_notifier import notify_post_published
                    await notify_post_published(self.session, post)
                except Exception as e:
                    logger.warning("notify_post_published failed: %s", e)
            except Exception as e:
                logger.error("publish_scheduled_posts failed: %s", e, exc_info=True)
                await self.session.rollback()
        return count

    async def delete_post(self, post_id: int, practitioner_id: int) -> bool:
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return False
        tax = BlogTaxonomyService(self.session, self.project_id)
        for tag in post.tags:
            await tax.decrement_tag_usage(tag.id, commit=False)
        await self.session.execute(delete(BlogPostTag).where(BlogPostTag.post_id == post_id))
        await self.session.delete(post)
        await self.session.commit()
        return True

    async def increment_views(self, post_id: int) -> None:
        await self.session.execute(
            update(BlogPost)
            .where(BlogPost.id == post_id, BlogPost.project_id == self.project_id)
            .values(views_count=BlogPost.views_count + 1)
        )
        await self.session.commit()
