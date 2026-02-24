"""Public specialist profile pages (HTML, no auth)."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.models.blog_post import BlogPost
from app.services.social_links import build_all_social_urls

router = APIRouter(tags=["Specialist Pages"])
templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


async def _resolve_specialist(
    db: AsyncSession,
    slug_or_id: str,
) -> Specialist | None:
    """Resolve specialist by slug (PractitionerProfile.slug) or numeric ID."""
    slug_clean = slug_or_id.strip()
    # 1. Try numeric ID
    try:
        sid = int(slug_clean)
        specialist = await db.get(Specialist, sid)
        if specialist:
            return specialist
    except ValueError:
        pass
    # 2. Try by practitioner slug
    r = await db.execute(
        select(PractitionerProfile).where(PractitionerProfile.slug == slug_clean)
    )
    profile = r.scalar_one_or_none()
    if not profile:
        return None
    return await db.get(Specialist, profile.specialist_id)


@router.get("/specialists/{slug_or_id}", response_class=HTMLResponse)
async def specialist_profile_page(
    slug_or_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public profile page for a specialist. Accepts slug or numeric ID."""
    specialist = await _resolve_specialist(db, slug_or_id)
    if not specialist:
        return HTMLResponse("<h1>Спеціаліст не знайдений</h1>", status_code=404)

    specialist_id = specialist.id
    r = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.specialist_id == specialist_id
        )
    )
    practitioner = r.scalar_one_or_none()

    blog_posts = []
    if practitioner:
        r = await db.execute(
            select(BlogPost)
            .where(
                BlogPost.practitioner_id == practitioner.id,
                BlogPost.status == "published",
            )
            .order_by(BlogPost.published_at.desc())
            .limit(5)
        )
        blog_posts = list(r.scalars().all())

    social_links = []
    if practitioner and practitioner.social_links:
        social_links = build_all_social_urls(practitioner.social_links)

    unique_story = getattr(practitioner, "unique_story", None) if practitioner else None
    soft_cta = getattr(practitioner, "soft_cta_text", None) if practitioner else None
    creator_signature = getattr(practitioner, "creator_signature", None) if practitioner else None
    service_types = specialist.service_types if getattr(specialist, "service_types", None) else []
    avatar_url = getattr(specialist, "portfolio_url", None)
    bio_excerpt = (specialist.bio or "")[:160]
    practitioner_id = practitioner.id if practitioner else specialist_id

    return templates.TemplateResponse(
        "specialist/profile.html",
        {
            "request": request,
            "specialist": specialist,
            "unique_story": unique_story,
            "service_types": service_types,
            "blog_posts": blog_posts,
            "social_links": social_links,
            "soft_cta": soft_cta,
            "creator_signature": creator_signature,
            "avatar_url": avatar_url,
            "bio_excerpt": bio_excerpt,
            "practitioner_id": practitioner_id,
            "rating": None,
        },
    )
