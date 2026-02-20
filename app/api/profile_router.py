"""Profile API: social links management (practitioner), gated specialist links, public practitioner links."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_practitioner, get_current_user
from app.config import settings
from app.database.connection import get_db
from app.models.practitioner_profile import PractitionerProfile
from app.models.specialist import Specialist
from app.models.user import User
from app.schemas.recommendation import LinkAccessResponse
from app.schemas.social import (
    SocialLinksResponse,
    SocialLinksUpdate,
    SocialLinkItem,
)
from app.services.social_links import (
    build_all_social_urls,
    build_social_url,
    validate_social_links,
    SUPPORTED_PLATFORMS,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api", tags=["Profile"])


@router.put("/profile/social-links", response_model=SocialLinksResponse)
async def update_social_links(
    body: SocialLinksUpdate,
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
    db: AsyncSession = Depends(get_db),
):
    """Update social links (partial merge with existing). Practitioner only."""
    # Convert Pydantic model to dict, drop None values
    raw = body.model_dump(exclude_unset=True)
    if not raw:
        # Return current state
        links = build_all_social_urls(practitioner.social_links)
        return SocialLinksResponse(
            links=[SocialLinkItem(**x) for x in links],
            supported_platforms=SUPPORTED_PLATFORMS,
        )
    cleaned = validate_social_links(raw)
    existing = dict(practitioner.social_links or {})
    existing.update(cleaned)
    practitioner.social_links = existing
    await db.commit()
    await db.refresh(practitioner)
    links = build_all_social_urls(practitioner.social_links)
    return SocialLinksResponse(
        links=[SocialLinkItem(**x) for x in links],
        supported_platforms=SUPPORTED_PLATFORMS,
    )


@router.get("/profile/social-links", response_model=SocialLinksResponse)
async def get_my_social_links(
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
):
    """Get current practitioner's social links (with full URLs)."""
    links = build_all_social_urls(practitioner.social_links)
    return SocialLinksResponse(
        links=[SocialLinkItem(**x) for x in links],
        supported_platforms=SUPPORTED_PLATFORMS,
    )


@router.delete("/profile/social-links/{platform}")
async def delete_social_link(
    platform: str,
    practitioner: PractitionerProfile = Depends(get_current_practitioner),
    db: AsyncSession = Depends(get_db),
):
    """Remove one platform from current practitioner's social links."""
    platform_lower = platform.lower().strip()
    if platform_lower not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")
    existing = dict(practitioner.social_links or {})
    if platform_lower not in existing:
        return {"message": "Platform was not set", "platform": platform_lower}
    del existing[platform_lower]
    practitioner.social_links = existing if existing else None
    await db.commit()
    return {"message": "Removed", "platform": platform_lower}


@router.get("/practitioners/{practitioner_id}/social-links", response_model=SocialLinksResponse)
async def get_practitioner_social_links_public(
    practitioner_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a practitioner's social links by profile id (public, e.g. for blog sidebar)."""
    profile = await db.get(PractitionerProfile, practitioner_id)
    if not profile or not getattr(profile, "is_active", True):
        raise HTTPException(status_code=404, detail="Practitioner not found")
    links = build_all_social_urls(profile.social_links)
    return SocialLinksResponse(
        links=[SocialLinkItem(**x) for x in links],
        supported_platforms=SUPPORTED_PLATFORMS,
    )


def _project_id() -> str:
    return getattr(settings, "PROJECT_ID", "healer_nexus")


@router.get("/specialists/{specialist_id}/social-links", response_model=LinkAccessResponse)
async def get_specialist_social_links_gated(
    specialist_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get specialist's social links. Only accessible after a confirmed/completed booking."""
    project_id = _project_id()
    rec_svc = RecommendationService(db, project_id)
    can_access = await rec_svc.can_access_links(specialist_id, user.id)
    if not can_access:
        return LinkAccessResponse(
            accessible=False,
            reason="Запишіться до спеціаліста щоб отримати контакти",
            links=None,
        )
    await rec_svc.record_links_revealed(specialist_id, user.id)
    r = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.specialist_id == specialist_id,
            PractitionerProfile.project_id == project_id,
            PractitionerProfile.is_active == True,
        ).limit(1)
    )
    profile = r.scalar_one_or_none()
    if not profile:
        return LinkAccessResponse(accessible=True, reason=None, links=[])
    links = build_all_social_urls(getattr(profile, "social_links", None))
    await db.commit()
    return LinkAccessResponse(accessible=True, reason=None, links=links)


@router.post("/specialists/{specialist_id}/social-links/{platform}/click")
async def record_social_link_click(
    specialist_id: int,
    platform: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a social link click and return the URL (for redirect). Requires confirmed booking."""
    platform_lower = platform.lower().strip()
    if platform_lower not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")
    project_id = _project_id()
    rec_svc = RecommendationService(db, project_id)
    can_access = await rec_svc.can_access_links(specialist_id, user.id)
    if not can_access:
        raise HTTPException(
            status_code=403,
            detail="Запишіться до спеціаліста щоб отримати контакти",
        )
    r = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.specialist_id == specialist_id,
            PractitionerProfile.project_id == project_id,
        ).limit(1)
    )
    profile = r.scalar_one_or_none()
    if not profile or not getattr(profile, "social_links", None):
        raise HTTPException(status_code=404, detail="Social links not set")
    username = (profile.social_links or {}).get(platform_lower)
    if not username:
        raise HTTPException(status_code=404, detail=f"Platform {platform} not set")
    url = build_social_url(platform_lower, username)
    if not url:
        raise HTTPException(status_code=400, detail="Invalid link")
    await rec_svc.record_link_click(specialist_id, user.id, platform_lower)
    await db.commit()
    return {"url": url, "platform": platform_lower}
