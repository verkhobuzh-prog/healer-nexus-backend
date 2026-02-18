"""
Blog taxonomy API: categories and tags. Prefix /api/blog.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.api.deps import get_current_practitioner
from app.models.practitioner_profile import PractitionerProfile
from app.schemas.blog_taxonomy import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryTreeResponse,
    TagResponse,
    TagListResponse,
    TagCloudItem,
)
from app.schemas.blog import BlogPostListResponse, BlogPostListItem
from app.services.blog_taxonomy_service import BlogTaxonomyService
from app.services.blog_service import BlogService
from app.api.blog_router import _post_response
from app.config import settings

router = APIRouter(prefix="/api/blog", tags=["Blog"])


def _category_to_response(cat, post_count: int = 0, children: Optional[list] = None):
    return CategoryResponse(
        id=cat.id,
        project_id=cat.project_id,
        name=cat.name,
        slug=cat.slug,
        description=cat.description,
        parent_id=cat.parent_id,
        icon_emoji=cat.icon_emoji,
        sort_order=cat.sort_order,
        is_active=cat.is_active,
        post_count=post_count,
        children=children or [],
    )


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Create category (auth required)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    try:
        cat = await svc.create_category(
            name=body.name,
            description=body.description,
            parent_id=body.parent_id,
            icon_emoji=body.icon_emoji,
            sort_order=body.sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    count = await svc.get_category_post_count(cat.id)
    return _category_to_response(cat, post_count=count)


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
):
    """List all categories (flat, sorted by sort_order)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    cats = await svc.list_categories()
    out = []
    for c in cats:
        count = await svc.get_category_post_count(c.id)
        out.append(_category_to_response(c, post_count=count))
    return out


@router.get("/categories/tree", response_model=CategoryTreeResponse)
async def get_category_tree(
    db: AsyncSession = Depends(get_db),
):
    """Hierarchical category tree."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    roots = await svc.get_category_tree()

    async def build_resp_async(c):
        count = await svc.get_category_post_count(c.id)
        children = [await build_resp_async(ch) for ch in getattr(c, "children", [])]
        return _category_to_response(c, post_count=count, children=children)

    categories = []
    for r in roots:
        categories.append(await build_resp_async(r))
    return CategoryTreeResponse(categories=categories)


@router.get("/categories/{id}", response_model=CategoryResponse)
async def get_category(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Single category."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    cat = await svc.get_category(id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    count = await svc.get_category_post_count(cat.id)
    return _category_to_response(cat, post_count=count)


@router.put("/categories/{id}", response_model=CategoryResponse)
async def update_category(
    id: int,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Update category (auth required)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    kwargs = body.model_dump(exclude_unset=True)
    cat = await svc.update_category(id, **kwargs)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    count = await svc.get_category_post_count(cat.id)
    return _category_to_response(cat, post_count=count)


@router.delete("/categories/{id}", status_code=204)
async def delete_category(
    id: int,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Delete category only if no posts use it (auth required)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    ok = await svc.delete_category(id)
    if not ok:
        raise HTTPException(status_code=400, detail="Category has posts or not found")


@router.get("/tags", response_model=TagListResponse)
async def list_tags(
    min_usage: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List tags sorted by usage."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    tags = await svc.list_tags(min_usage=min_usage)
    return TagListResponse(
        items=[TagResponse.model_validate(t) for t in tags],
        total=len(tags),
    )


@router.get("/tags/cloud", response_model=list[TagCloudItem])
async def get_tag_cloud(
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Tag cloud (top tags with weight 1-5)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    items = await svc.get_tag_cloud(limit=limit)
    return [TagCloudItem.model_validate(i) for i in items]


@router.get("/tags/search", response_model=list[TagResponse])
async def search_tags(
    q: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Autocomplete search by name prefix."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    tags = await svc.search_tags(query=q, limit=limit)
    return [TagResponse.model_validate(t) for t in tags]


@router.delete("/tags/{id}", status_code=204)
async def delete_tag(
    id: int,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Delete tag and all post associations (auth required)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogTaxonomyService(db, project_id)
    ok = await svc.delete_tag(id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tag not found")


@router.get("/posts/by-category/{slug}", response_model=BlogPostListResponse)
async def list_posts_by_category(
    slug: str,
    practitioner_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Published posts in category."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    posts, total = await svc.list_posts_by_category_slug(
        category_slug=slug,
        practitioner_id=practitioner_id,
        page=max(1, page),
        page_size=min(50, max(1, page_size)),
    )
    items = [BlogPostListItem(**_post_response(p, include_content=False)) for p in posts]
    return BlogPostListResponse(
        items=items,
        total=total,
        page=max(1, page),
        page_size=min(50, max(1, page_size)),
        has_next=(page * page_size) < total,
    )


@router.get("/posts/by-tag/{slug}", response_model=BlogPostListResponse)
async def list_posts_by_tag(
    slug: str,
    practitioner_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Published posts with tag."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    posts, total = await svc.list_posts_by_tag_slug(
        tag_slug=slug,
        practitioner_id=practitioner_id,
        page=max(1, page),
        page_size=min(50, max(1, page_size)),
    )
    items = [BlogPostListItem(**_post_response(p, include_content=False)) for p in posts]
    return BlogPostListResponse(
        items=items,
        total=total,
        page=max(1, page),
        page_size=min(50, max(1, page_size)),
        has_next=(page * page_size) < total,
    )
