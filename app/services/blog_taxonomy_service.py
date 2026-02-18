"""
Blog categories and tags: CRUD, tree, tag cloud, slug generation.
Uses generate_slug() from blog_service for Ukrainian transliteration.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_category import BlogCategory
from app.models.blog_tag import BlogTag
from app.models.blog_post import BlogPost
from app.models.blog_post_tag import BlogPostTag
from app.services.blog_slug import generate_slug


async def _ensure_unique_category_slug(
    session: AsyncSession,
    project_id: str,
    slug: str,
    exclude_id: Optional[int] = None,
) -> str:
    base = slug
    candidate = base
    n = 1
    while True:
        q = select(BlogCategory.id).where(
            BlogCategory.project_id == project_id,
            BlogCategory.slug == candidate,
        )
        if exclude_id is not None:
            q = q.where(BlogCategory.id != exclude_id)
        r = await session.execute(q)
        if r.scalar_one_or_none() is None:
            return candidate
        n += 1
        candidate = f"{base}-{n}"


async def _ensure_unique_tag_slug(
    session: AsyncSession,
    project_id: str,
    slug: str,
    exclude_id: Optional[int] = None,
) -> str:
    base = slug
    candidate = base
    n = 1
    while True:
        q = select(BlogTag.id).where(
            BlogTag.project_id == project_id,
            BlogTag.slug == candidate,
        )
        if exclude_id is not None:
            q = q.where(BlogTag.id != exclude_id)
        r = await session.execute(q)
        if r.scalar_one_or_none() is None:
            return candidate
        n += 1
        candidate = f"{base}-{n}"


class BlogTaxonomyService:
    def __init__(self, session: AsyncSession, project_id: str):
        self.session = session
        self.project_id = project_id

    # --- Categories ---
    async def create_category(
        self,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        icon_emoji: Optional[str] = None,
        sort_order: int = 0,
    ) -> BlogCategory:
        if parent_id is not None:
            parent = await self.get_category(parent_id)
            if not parent:
                raise ValueError("Parent category not found")
        slug = generate_slug(name)
        slug = await _ensure_unique_category_slug(self.session, self.project_id, slug)
        cat = BlogCategory(
            project_id=self.project_id,
            name=name,
            slug=slug,
            description=description,
            parent_id=parent_id,
            icon_emoji=icon_emoji,
            sort_order=sort_order,
        )
        self.session.add(cat)
        await self.session.commit()
        await self.session.refresh(cat)
        return cat

    async def update_category(
        self,
        category_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        icon_emoji: Optional[str] = None,
        sort_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[BlogCategory]:
        cat = await self.get_category(category_id)
        if not cat:
            return None
        if name is not None:
            cat.name = name
            cat.slug = await _ensure_unique_category_slug(
                self.session, self.project_id, generate_slug(name), exclude_id=category_id
            )
        if description is not None:
            cat.description = description
        if parent_id is not None:
            if parent_id:
                parent = await self.get_category(parent_id)
                if not parent:
                    return None
                cat.parent_id = parent_id
            else:
                cat.parent_id = None
        if icon_emoji is not None:
            cat.icon_emoji = icon_emoji
        if sort_order is not None:
            cat.sort_order = sort_order
        if is_active is not None:
            cat.is_active = is_active
        await self.session.commit()
        await self.session.refresh(cat)
        return cat

    async def delete_category(self, category_id: int) -> bool:
        count = await self.get_category_post_count(category_id)
        if count > 0:
            return False
        cat = await self.get_category(category_id)
        if not cat:
            return False
        await self.session.delete(cat)
        await self.session.commit()
        return True

    async def get_category(self, category_id: int) -> Optional[BlogCategory]:
        r = await self.session.execute(
            select(BlogCategory).where(
                BlogCategory.id == category_id,
                BlogCategory.project_id == self.project_id,
            )
        )
        return r.scalar_one_or_none()

    async def list_categories(self) -> list[BlogCategory]:
        r = await self.session.execute(
            select(BlogCategory)
            .where(BlogCategory.project_id == self.project_id)
            .order_by(BlogCategory.sort_order, BlogCategory.name)
        )
        return list(r.scalars().all())

    async def get_category_tree(self) -> list[BlogCategory]:
        all_cats = await self.list_categories()
        by_id = {c.id: c for c in all_cats}
        for c in all_cats:
            c.children = []
        roots = []
        for c in all_cats:
            if c.parent_id is None:
                roots.append(c)
            else:
                parent = by_id.get(c.parent_id)
                if parent:
                    parent.children.append(c)
        return sorted(roots, key=lambda x: (x.sort_order, x.name))

    async def get_category_post_count(self, category_id: int) -> int:
        r = await self.session.execute(
            select(func.count(BlogPost.id)).where(
                BlogPost.project_id == self.project_id,
                BlogPost.category_id == category_id,
            )
        )
        return r.scalar() or 0

    # --- Tags ---
    async def get_or_create_tag(self, name: str) -> BlogTag:
        slug = generate_slug(name.strip())
        if not slug:
            slug = "tag"
        slug = await _ensure_unique_tag_slug(self.session, self.project_id, slug)
        r = await self.session.execute(
            select(BlogTag).where(
                BlogTag.project_id == self.project_id,
                BlogTag.slug == slug,
            )
        )
        tag = r.scalar_one_or_none()
        if tag:
            return tag
        tag = BlogTag(
            project_id=self.project_id,
            name=name.strip(),
            slug=slug,
        )
        self.session.add(tag)
        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def get_or_create_tags(self, names: list[str]) -> list[BlogTag]:
        result = []
        seen_slugs = set()
        for name in names:
            n = (name or "").strip()
            if not n:
                continue
            slug = generate_slug(n)
            if not slug:
                slug = "tag"
            if slug in seen_slugs:
                r = await self.session.execute(
                    select(BlogTag).where(
                        BlogTag.project_id == self.project_id,
                        BlogTag.slug == slug,
                    )
                )
                t = r.scalar_one_or_none()
                if t:
                    result.append(t)
                continue
            seen_slugs.add(slug)
            tag = await self.get_or_create_tag(n)
            result.append(tag)
        return result

    async def list_tags(self, min_usage: int = 0, limit: Optional[int] = None) -> list[BlogTag]:
        q = (
            select(BlogTag)
            .where(BlogTag.project_id == self.project_id)
            .where(BlogTag.usage_count >= min_usage)
            .order_by(BlogTag.usage_count.desc(), BlogTag.name)
        )
        if limit is not None:
            q = q.limit(limit)
        r = await self.session.execute(q)
        return list(r.scalars().all())

    async def get_tag_cloud(self, limit: int = 30) -> list[dict]:
        tags = await self.list_tags(limit=limit)
        if not tags:
            return []
        counts = [t.usage_count for t in tags]
        max_c = max(counts) or 1
        min_c = min(counts)
        out = []
        for t in tags:
            if max_c == min_c:
                weight = 3
            else:
                norm = (t.usage_count - min_c) / (max_c - min_c) if max_c > min_c else 0
                weight = min(5, max(1, int(norm * 4) + 1))
            out.append({"name": t.name, "slug": t.slug, "usage_count": t.usage_count, "weight": weight})
        return out

    async def delete_tag(self, tag_id: int) -> bool:
        tag = await self.session.get(BlogTag, tag_id)
        if not tag or tag.project_id != self.project_id:
            return False
        await self.session.execute(delete(BlogPostTag).where(BlogPostTag.tag_id == tag_id))
        await self.session.delete(tag)
        await self.session.commit()
        return True

    async def increment_tag_usage(self, tag_id: int, *, commit: bool = True) -> None:
        await self.session.execute(
            update(BlogTag)
            .where(BlogTag.id == tag_id, BlogTag.project_id == self.project_id)
            .values(usage_count=BlogTag.usage_count + 1)
        )
        if commit:
            await self.session.commit()

    async def decrement_tag_usage(self, tag_id: int, *, commit: bool = True) -> None:
        await self.session.execute(
            update(BlogTag)
            .where(BlogTag.id == tag_id, BlogTag.project_id == self.project_id)
            .values(usage_count=func.greatest(BlogTag.usage_count - 1, 0))
        )
        if commit:
            await self.session.commit()

    async def search_tags(self, query: str, limit: int = 10) -> list[BlogTag]:
        q = (
            select(BlogTag)
            .where(BlogTag.project_id == self.project_id)
            .where(BlogTag.name.ilike(f"{query.strip()}%"))
            .order_by(BlogTag.usage_count.desc())
            .limit(limit)
        )
        r = await self.session.execute(q)
        return list(r.scalars().all())
