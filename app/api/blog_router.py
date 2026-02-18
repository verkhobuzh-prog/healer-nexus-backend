"""
Blog API: CRUD, publish, AI draft, image upload. Prefix /api/blog.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.api.deps import get_current_practitioner
from app.models.practitioner_profile import PractitionerProfile
from app.models.blog_post import BlogPost, PostStatus
from app.schemas.blog import (
    BlogPostCreate,
    BlogPostUpdate,
    BlogPostResponse,
    BlogPostListItem,
    BlogPostListResponse,
    AIGenerateDraftRequest,
    BlogPostPublish,
    SchedulePostRequest,
    PractitionerBrief,
)
from app.schemas.blog_taxonomy import CategoryResponse, TagResponse
from app.services.blog_service import BlogService
from app.services.ai_blog_generator import generate_blog_draft
from app.services.cloudinary_service import upload_image
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/blog", tags=["Blog"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB


def _practitioner_brief(profile: Optional[PractitionerProfile], specialist=None) -> Optional[PractitionerBrief]:
    if not profile:
        return None
    name = getattr(specialist, "name", None) if specialist else None
    return PractitionerBrief(
        id=profile.id,
        display_name=name,
        avatar_url=None,
        unique_story=profile.unique_story,
    )


def _post_response(post: BlogPost, include_content: bool = True) -> dict:
    practitioner = getattr(post, "practitioner", None)
    specialist = getattr(practitioner, "specialist", None) if practitioner else None
    brief = _practitioner_brief(practitioner, specialist)
    category = getattr(post, "category", None)
    tags = getattr(post, "tags", []) or []
    category_resp = CategoryResponse.model_validate(category) if category else None
    tags_resp = [TagResponse.model_validate(t) for t in tags]
    data = {
        "id": post.id,
        "project_id": post.project_id,
        "practitioner_id": post.practitioner_id,
        "title": post.title,
        "slug": post.slug,
        "editor_type": post.editor_type,
        "status": post.status,
        "published_at": post.published_at,
        "scheduled_at": getattr(post, "scheduled_at", None),
        "featured_image_url": post.featured_image_url,
        "meta_title": post.meta_title,
        "meta_description": post.meta_description,
        "views_count": post.views_count,
        "telegram_discussion_url": post.telegram_discussion_url,
        "ai_generated": post.ai_generated,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "practitioner": brief,
        "reading_time_minutes": post.reading_time_minutes,
        "category": category_resp,
        "tags": tags_resp,
        "category_name": category.name if category else None,
        "tag_count": len(tags),
    }
    if include_content:
        data["content"] = post.content
        data["ai_prompt_topic"] = post.ai_prompt_topic
    return data


@router.post("/posts", response_model=BlogPostResponse, status_code=201)
async def create_post(
    body: BlogPostCreate,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Create a draft post (auth required)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    post = await svc.create_post(
        practitioner_id=practitioner.id,
        title=body.title,
        content=body.content,
        editor_type=body.editor_type,
        featured_image_url=body.featured_image_url,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        telegram_discussion_url=body.telegram_discussion_url,
        category_id=body.category_id,
        tag_names=body.tag_names or [],
    )
    return _post_response(post)


@router.get("/posts", response_model=BlogPostListResponse)
async def list_posts(
    status: Optional[str] = None,
    practitioner_id: Optional[int] = None,
    category_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """List posts with filters (auth required)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    posts, total = await svc.list_posts(
        practitioner_id=practitioner_id or practitioner.id,
        status=status,
        category_id=category_id,
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


@router.get("/posts/public", response_model=BlogPostListResponse)
async def list_public_posts(
    practitioner_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List published posts only (no auth)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    posts, total = await svc.list_public_posts(
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


@router.get("/posts/{slug}", response_model=BlogPostResponse)
async def get_post_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Public view by slug; increments views if published."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    post = await svc.get_post_by_slug(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status == PostStatus.PUBLISHED.value:
        await svc.increment_views(post.id)
        post = await svc.get_post_by_id(post.id) or post
    return _post_response(post)


@router.put("/posts/{id}", response_model=BlogPostResponse)
async def update_post(
    id: int,
    body: BlogPostUpdate,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Update post (ownership check)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    kwargs = body.model_dump(exclude_unset=True)
    post = await svc.update_post(
        post_id=id,
        practitioner_id=practitioner.id,
        **kwargs,
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or access denied")
    return _post_response(post)


@router.delete("/posts/{id}", status_code=204)
async def delete_post(
    id: int,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Delete post (ownership check)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    ok = await svc.delete_post(post_id=id, practitioner_id=practitioner.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Post not found or access denied")


@router.post("/posts/{id}/publish", response_model=BlogPostResponse)
async def publish_post(
    id: int,
    body: Optional[BlogPostPublish] = None,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Publish post (validates content not empty)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    meta_title = body.meta_title if body else None
    meta_description = body.meta_description if body else None
    post = await svc.publish_post(
        post_id=id,
        practitioner_id=practitioner.id,
        meta_title=meta_title,
        meta_description=meta_description,
    )
    if not post:
        raise HTTPException(
            status_code=400,
            detail="Post not found, access denied, or content is empty",
        )
    return _post_response(post)


@router.post("/posts/{id}/unpublish", response_model=BlogPostResponse)
async def unpublish_post(
    id: int,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Revert post to draft."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    post = await svc.unpublish_post(post_id=id, practitioner_id=practitioner.id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or access denied")
    return _post_response(post)


@router.post("/posts/{id}/schedule", response_model=BlogPostResponse)
async def schedule_post(
    id: int,
    body: SchedulePostRequest,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Schedule post for future publish. scheduled_at must be at least 5 minutes in the future (UTC)."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    post = await svc.schedule_post(
        post_id=id,
        practitioner_id=practitioner.id,
        scheduled_at=body.scheduled_at,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
    )
    if not post:
        raise HTTPException(
            status_code=400,
            detail="Post not found, access denied, content empty, or scheduled_at must be at least 5 minutes in the future",
        )
    return _post_response(post)


@router.post("/posts/{id}/unschedule", response_model=BlogPostResponse)
async def unschedule_post(
    id: int,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Remove schedule: set post back to draft and clear scheduled_at."""
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    post = await svc.unschedule_post(post_id=id, practitioner_id=practitioner.id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or access denied")
    return _post_response(post)


@router.post("/posts/ai/generate-draft", response_model=BlogPostResponse, status_code=201)
async def ai_generate_draft(
    body: AIGenerateDraftRequest,
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """AI generates markdown draft and saves as BlogPost."""
    from sqlalchemy import select
    from app.models.specialist import Specialist

    practitioner_name = ""
    specialties = ""
    unique_story = getattr(practitioner, "unique_story", "") or ""
    if getattr(practitioner, "specialist_id", None):
        r = await db.execute(
            select(Specialist).where(Specialist.id == practitioner.specialist_id)
        )
        spec = r.scalar_one_or_none()
        if spec:
            practitioner_name = getattr(spec, "name", "") or ""
            specialties = getattr(spec, "specialty", "") or ""

    result = await generate_blog_draft(
        topic=body.topic,
        word_count=body.word_count,
        language=body.language,
        tone=body.tone,
        practitioner_name=practitioner_name,
        unique_story=unique_story,
        specialties=specialties,
    )
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    post = await svc.create_ai_draft(
        practitioner_id=practitioner.id,
        title=result["title"],
        content=result["content"],
        meta_title=result.get("meta_title"),
        meta_description=result.get("meta_description"),
        ai_prompt_topic=body.topic,
    )
    return _post_response(post)


@router.post("/posts/{id}/upload-image", response_model=BlogPostResponse)
async def upload_post_image(
    id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Upload image to Cloudinary and set featured_image_url (max 5MB, jpeg/png/webp/gif)."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Allowed types: jpeg, png, webp, gif",
        )
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    project_id = getattr(settings, "PROJECT_ID", "healer_nexus")
    svc = BlogService(db, project_id)
    post = await svc.get_post_by_id(id)
    if not post or post.practitioner_id != practitioner.id:
        raise HTTPException(status_code=404, detail="Post not found or access denied")
    try:
        upload_result = upload_image(data, folder="healer-nexus/blog", max_width=1200)
        url = upload_result.get("secure_url") or upload_result.get("url")
    except Exception as e:
        logger.exception("Cloudinary upload failed: %s", e)
        raise HTTPException(status_code=502, detail="Image upload failed")
    await svc.update_post(
        post_id=id,
        practitioner_id=practitioner.id,
        featured_image_url=url,
    )
    post = await svc.get_post_by_id(id) or post
    return _post_response(post)
