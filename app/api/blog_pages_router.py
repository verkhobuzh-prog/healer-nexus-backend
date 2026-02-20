"""
Public blog pages: HTML listing and post detail. Prefix /blog.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.models.practitioner_profile import PractitionerProfile
from app.models.specialist import Specialist
from app.models.blog_post import BlogPost, PostStatus
from app.services.blog_service import BlogService
from app.services.blog_taxonomy_service import BlogTaxonomyService
from app.services.blog_analytics_service import BlogAnalyticsService
from app.services.social_links import build_all_social_urls
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Blog Pages"])

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


async def _resolve_practitioner(
    db: AsyncSession,
    practitioner_slug: str,
    project_id: str,
) -> Optional[PractitionerProfile]:
    """
    Resolve practitioner by slug. PractitionerProfile has no slug;
    use id when practitioner_slug is numeric.
    """
    try:
        pid = int(practitioner_slug.strip())
    except ValueError:
        return None
    r = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.id == pid,
            PractitionerProfile.project_id == project_id,
            PractitionerProfile.is_active == True,
        )
    )
    return r.scalar_one_or_none()


async def _get_specialist_name(db: AsyncSession, profile: Optional[PractitionerProfile]) -> str:
    if not profile or not getattr(profile, "specialist_id", None):
        return ""
    r = await db.execute(select(Specialist).where(Specialist.id == profile.specialist_id))
    spec = r.scalar_one_or_none()
    return getattr(spec, "name", "") if spec else ""


async def _get_categories_and_tag_cloud(db: AsyncSession, project_id: str, tag_cloud_limit: int = 20):
    tax = BlogTaxonomyService(db, project_id)
    categories = await tax.list_categories()
    tag_cloud = await tax.get_tag_cloud(limit=tag_cloud_limit)
    return categories, tag_cloud


@router.get("/blog/{practitioner_slug}", response_class=HTMLResponse)
async def blog_list_page(
    request: Request,
    practitioner_slug: str,
    page: int = 1,
    page_size: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """HTML listing page for a practitioner's published posts."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    practitioner = await _resolve_practitioner(db, practitioner_slug, project_id)
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    svc = BlogService(db, project_id)
    posts, total = await svc.list_public_posts(
        practitioner_id=practitioner.id,
        page=page,
        page_size=page_size,
    )
    display_name = await _get_specialist_name(db, practitioner)
    categories, tag_cloud = await _get_categories_and_tag_cloud(db, project_id)
    social_links = build_all_social_urls(getattr(practitioner, "social_links", None))
    return templates.TemplateResponse(
        "blog/post_list.html",
        {
            "request": request,
            "practitioner": practitioner,
            "display_name": display_name,
            "posts": posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
            "categories": categories,
            "tag_cloud": tag_cloud,
            "current_category_slug": None,
            "current_tag_slug": None,
            "social_links": social_links,
        },
    )


@router.get("/blog/{practitioner_slug}/category/{category_slug}", response_class=HTMLResponse)
async def blog_list_by_category_page(
    request: Request,
    practitioner_slug: str,
    category_slug: str,
    page: int = 1,
    page_size: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """HTML listing filtered by category."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    practitioner = await _resolve_practitioner(db, practitioner_slug, project_id)
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    svc = BlogService(db, project_id)
    posts, total = await svc.list_posts_by_category_slug(
        category_slug=category_slug,
        practitioner_id=practitioner.id,
        page=page,
        page_size=page_size,
    )
    display_name = await _get_specialist_name(db, practitioner)
    categories, tag_cloud = await _get_categories_and_tag_cloud(db, project_id)
    social_links = build_all_social_urls(getattr(practitioner, "social_links", None))
    return templates.TemplateResponse(
        "blog/post_list.html",
        {
            "request": request,
            "practitioner": practitioner,
            "display_name": display_name,
            "posts": posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
            "categories": categories,
            "tag_cloud": tag_cloud,
            "current_category_slug": category_slug,
            "current_tag_slug": None,
            "social_links": social_links,
        },
    )


@router.get("/blog/{practitioner_slug}/tag/{tag_slug}", response_class=HTMLResponse)
async def blog_list_by_tag_page(
    request: Request,
    practitioner_slug: str,
    tag_slug: str,
    page: int = 1,
    page_size: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """HTML listing filtered by tag."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    practitioner = await _resolve_practitioner(db, practitioner_slug, project_id)
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    svc = BlogService(db, project_id)
    posts, total = await svc.list_posts_by_tag_slug(
        tag_slug=tag_slug,
        practitioner_id=practitioner.id,
        page=page,
        page_size=page_size,
    )
    display_name = await _get_specialist_name(db, practitioner)
    categories, tag_cloud = await _get_categories_and_tag_cloud(db, project_id)
    social_links = build_all_social_urls(getattr(practitioner, "social_links", None))
    return templates.TemplateResponse(
        "blog/post_list.html",
        {
            "request": request,
            "practitioner": practitioner,
            "display_name": display_name,
            "posts": posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
            "categories": categories,
            "tag_cloud": tag_cloud,
            "current_category_slug": None,
            "current_tag_slug": tag_slug,
            "social_links": social_links,
        },
    )


@router.get("/blog/{practitioner_slug}/{post_slug}", response_class=HTMLResponse)
async def blog_detail_page(
    request: Request,
    practitioner_slug: str,
    post_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """HTML post detail; increments views."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    practitioner = await _resolve_practitioner(db, practitioner_slug, project_id)
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    svc = BlogService(db, project_id)
    post = await svc.get_post_by_slug(post_slug)
    if not post or post.practitioner_id != practitioner.id:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status != PostStatus.PUBLISHED.value:
        raise HTTPException(status_code=404, detail="Post not found")
    try:
        analytics_svc = BlogAnalyticsService(db, project_id)
        referrer_url = request.headers.get("referer")
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None
        session_id = request.cookies.get("blog_session")
        await analytics_svc.record_view(
            post_id=post.id,
            referrer_url=referrer_url,
            user_agent=user_agent,
            ip_address=ip_address,
            session_id=session_id,
        )
        post = await svc.get_post_by_id(post.id) or post
    except Exception:
        logger.exception("View tracking failed (non-blocking)")
    display_name = await _get_specialist_name(db, practitioner)
    related = await svc.list_public_posts(
        practitioner_id=practitioner.id,
        page=1,
        page_size=4,
    )
    related_posts = [p for p in related[0] if p.id != post.id][:3]
    social_links = build_all_social_urls(getattr(practitioner, "social_links", None))
    return templates.TemplateResponse(
        "blog/post_detail.html",
        {
            "request": request,
            "practitioner": practitioner,
            "display_name": display_name,
            "post": post,
            "related_posts": related_posts,
            "social_links": social_links,
        },
    )
