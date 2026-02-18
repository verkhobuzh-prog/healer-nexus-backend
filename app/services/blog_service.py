"""
Blog CRUD and slug generation. Async SQLAlchemy 2.0, multi-tenant by project_id.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blog_post import BlogPost, PostStatus


# Ukrainian Cyrillic -> Latin transliteration
UA_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ye", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "yi", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "yu", "я": "ya",
    "А": "A", "Б": "B", "В": "V", "Г": "H", "Ґ": "G", "Д": "D", "Е": "E",
    "Є": "Ye", "Ж": "Zh", "З": "Z", "И": "Y", "І": "I", "Ї": "Yi", "Й": "Y",
    "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R",
    "С": "S", "Т": "T", "У": "U", "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch",
    "Ш": "Sh", "Щ": "Shch", "Ь": "", "Ю": "Yu", "Я": "Ya",
}


def generate_slug(title: str) -> str:
    """Slug from title with Ukrainian transliteration."""
    if not title or not title.strip():
        return "post"
    slug = title.strip()
    result = []
    for char in slug:
        if char in UA_TRANSLIT:
            result.append(UA_TRANSLIT[char])
        elif char.isalnum() or char in " -_":
            result.append(char)
        else:
            try:
                n = unicodedata.name(char)
                if "LATIN" in n or "DIGIT" in n:
                    result.append(char)
                else:
                    result.append("")
            except ValueError:
                result.append("")
    slug = "".join(result)
    slug = re.sub(r"[-\s]+", "-", slug).strip("-").lower()
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug or "post"


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
        )
        self.session.add(post)
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
            .options(selectinload(BlogPost.practitioner))
        )
        return r.scalar_one_or_none()

    async def get_post_by_slug(self, slug: str) -> Optional[BlogPost]:
        r = await self.session.execute(
            select(BlogPost)
            .where(
                BlogPost.project_id == self.project_id,
                BlogPost.slug == slug,
            )
            .options(selectinload(BlogPost.practitioner))
        )
        return r.scalar_one_or_none()

    async def list_posts(
        self,
        practitioner_id: Optional[int] = None,
        status: Optional[str] = None,
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
        total_r = await self.session.execute(count_q)
        total = total_r.scalar() or 0
        q = (
            q.options(selectinload(BlogPost.practitioner))
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
    ) -> Optional[BlogPost]:
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return None
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
        return post

    async def unpublish_post(self, post_id: int, practitioner_id: int) -> Optional[BlogPost]:
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return None
        post.status = PostStatus.DRAFT.value
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def delete_post(self, post_id: int, practitioner_id: int) -> bool:
        post = await self.get_post_by_id(post_id)
        if not post or post.practitioner_id != practitioner_id:
            return False
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
