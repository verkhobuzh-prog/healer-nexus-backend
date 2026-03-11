"""
Admin API: manage users, roles, specialist applications.
Only accessible by admin role.
"""
from __future__ import annotations
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_admin
from app.database.connection import get_db
from app.models.user import User
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.models.specialist_application import SpecialistApplication, ApplicationStatus
from app.models.refresh_token import RefreshToken
from app.models.message import Message
from app.models.booking import Booking
from app.models.specialist_recommendation import SpecialistRecommendation
from app.models.blog_post import BlogPost
from app.models.blog_post_view import BlogPostView
from app.models.blog_analytics_daily import BlogAnalyticsDaily
from app.models.blog_post_tag import BlogPostTag
from app.models.conversation import Conversation
from app.models.specialist_content import SpecialistContent
from app.schemas.specialist_application import (
    ApplicationResponse,
    ApplicationReview,
    RoleUpdate,
)
from app.schemas.auth import (
    AdminResetPasswordRequest,
    AdminCreateUserRequest,
    AdminUpdateEmailRequest,
)
from app.core.security import hash_password
from app.config import settings
from app.services.promoterx_service import PromoterXService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _generate_unique_slug(name: str, specialist_id: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        slug = "specialist"
    short_id = uuid.uuid4().hex[:6]
    return f"{slug}-{specialist_id}-{short_id}"


# --- Users ---
@router.post("/users/create", status_code=201)
async def admin_create_user(
    body: AdminCreateUserRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a user (client). Body: email, name, password, role (default user). Admin only."""
    r = await db.execute(select(User).where(User.email == body.email))
    if r.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=body.email,
        username=body.name,
        password_hash=hash_password(body.password),
        role=body.role,
        is_active=True,
        telegram_id=None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"message": "User created", "user_id": user.id, "email": user.email}


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional role filter."""
    query = select(User)
    if role:
        query = query.where(User.role == role)
    query = query.offset(skip).limit(limit)
    total_q = select(func.count(User.id))
    if role:
        total_q = total_q.where(User.role == role)
    result = await db.execute(query)
    users = result.scalars().all()
    total = (await db.execute(total_q)).scalar() or 0
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.username,
                "role": u.role,
                "created_at": str(u.created_at) if hasattr(u, "created_at") else None,
            }
            for u in users
        ],
        "total": total,
    }
async def _apply_role_update(user_id: int, role: str, db: AsyncSession) -> None:
    if role not in ("user", "practitioner", "admin"):
        raise HTTPException(400, "Invalid role. Use: user, practitioner, admin")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.role = role
    await db.commit()


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: RoleUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user (e.g. role). Body: { \"role\": \"user\" | \"practitioner\" | \"admin\" }. Admin only."""
    if user_id == admin.id:
        raise HTTPException(400, "Cannot change your own role")
    await _apply_role_update(user_id, body.role, db)
    return {"message": "Role updated", "user_id": user_id, "new_role": body.role}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    body: RoleUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change user role. Body: {\"role\": \"admin\" | \"practitioner\" | \"user\"}. Admin only; cannot change own role."""
    if user_id == admin.id:
        raise HTTPException(400, "Cannot change your own role")
    await _apply_role_update(user_id, body.role, db)
    return {"message": "Role updated", "user_id": user_id, "new_role": body.role}
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete user account. Admin only. Manually deletes all FK-related rows (no CASCADE)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "admin":
        raise HTTPException(400, "Cannot delete admin account")

    # Resolve specialist(s) and practitioner profile(s) for this user
    r_spec = await db.execute(select(Specialist).where(Specialist.user_id == user_id))
    specialist = r_spec.scalar_one_or_none()
    specialist_ids = []
    practitioner_ids = []
    if specialist:
        specialist_ids.append(specialist.id)
        r_prof = await db.execute(
            select(PractitionerProfile).where(
                PractitionerProfile.specialist_id == specialist.id
            )
        )
        for row in r_prof.scalars().all():
            practitioner_ids.append(row.id)

    # 1. Blog: views, analytics, tags, then posts (FK to practitioner_profiles)
    if practitioner_ids:
        r_posts = await db.execute(
            select(BlogPost.id).where(BlogPost.practitioner_id.in_(practitioner_ids))
        )
        post_ids = [row[0] for row in r_posts.fetchall()]
        if post_ids:
            await db.execute(delete(BlogPostView).where(BlogPostView.post_id.in_(post_ids)))
            await db.execute(
                delete(BlogAnalyticsDaily).where(BlogAnalyticsDaily.post_id.in_(post_ids))
            )
            await db.execute(
                delete(BlogPostTag).where(BlogPostTag.post_id.in_(post_ids))
            )
        await db.execute(
            delete(BlogPost).where(BlogPost.practitioner_id.in_(practitioner_ids))
        )

    # 2. Bookings (user as client or specialist)
    await db.execute(delete(Booking).where(Booking.user_id == user_id))
    if specialist_ids:
        await db.execute(
            delete(Booking).where(Booking.specialist_id.in_(specialist_ids))
        )

    # 3. Specialist recommendations
    await db.execute(
        delete(SpecialistRecommendation).where(SpecialistRecommendation.user_id == user_id)
    )
    if specialist_ids:
        await db.execute(
            delete(SpecialistRecommendation).where(
                SpecialistRecommendation.specialist_id.in_(specialist_ids)
            )
        )

    # 4. Practitioner profiles (FK specialists)
    if specialist_ids:
        await db.execute(
            delete(PractitionerProfile).where(
                PractitionerProfile.specialist_id.in_(specialist_ids)
            )
        )

    # 5. Specialist content (FK specialists)
    if specialist_ids:
        await db.execute(
            delete(SpecialistContent).where(
                SpecialistContent.specialist_id.in_(specialist_ids)
            )
        )

    # 6. Specialist (FK users)
    await db.execute(delete(Specialist).where(Specialist.user_id == user_id))

    # 7. Refresh tokens, applications, messages, conversations
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.execute(
        delete(SpecialistApplication).where(SpecialistApplication.user_id == user_id)
    )
    await db.execute(delete(Message).where(Message.user_id == user_id))
    await db.execute(delete(Conversation).where(Conversation.user_id == user_id))

    # 8. User
    await db.delete(user)
    await db.commit()
    return {"message": f"User {user_id} deleted"}


@router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: int,
    body: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Reset user password. Body: {"new_password": "string"} (min 6, max 128 chars)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    return {"message": "Password updated", "user_id": user_id}


@router.put("/users/{user_id}/email")
async def update_user_email(
    user_id: int,
    body: AdminUpdateEmailRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user email. Body: {"email": "new@example.com"}. Admin only."""
    r = await db.execute(select(User).where(User.id == user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = await db.execute(
        select(User).where(User.email == body.email, User.id != user_id)
    )
    if existing.scalars().first() is not None:
        raise HTTPException(status_code=400, detail="Email already exists")
    user.email = body.email
    await db.commit()
    return {
        "message": "Email updated",
        "user_id": user_id,
        "new_email": body.email,
    }


# --- Specialist Applications ---
@router.get("/applications", response_model=list[ApplicationResponse])
async def list_applications(
    status: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List specialist applications."""
    query = select(SpecialistApplication).order_by(SpecialistApplication.created_at.desc())
    if status:
        query = query.where(SpecialistApplication.status == status)
    result = await db.execute(query)
    return result.scalars().all()
@router.put("/applications/{app_id}")
async def review_application(
    app_id: int,
    body: ApplicationReview,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject specialist application."""
    application = await db.get(SpecialistApplication, app_id)
    if not application:
        raise HTTPException(404, "Application not found")
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(400, f"Application already {application.status.value}")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(400, "Status must be 'approved' or 'rejected'")
    application.status = ApplicationStatus(body.status)
    application.admin_comment = body.admin_comment
    application.reviewed_by = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    if body.status == "approved":
        user = await db.get(User, application.user_id)
        if not user:
            raise HTTPException(404, "User not found")
        specialist = Specialist(
            user_id=application.user_id,
            name=application.name,
            specialty=application.specialty,
            service_type=application.service_type,
            bio=application.bio,
            hourly_rate=application.hourly_rate,
            is_verified=True,
            is_active=True,
        )
        db.add(specialist)
        await db.flush()
        profile = PractitionerProfile(
            project_id="healer_nexus",
            specialist_id=specialist.id,
            slug=_generate_unique_slug(application.name, specialist.id),
            empathy_ratio=0.8,
            style="warm",
            preferences={},
            is_active=True,
            creator_signature=application.name,
            unique_story=(application.motivation or (application.bio[:200] if application.bio else None)) or None,
            social_links={"telegram": application.contact_telegram} if application.contact_telegram else None,
        )
        db.add(profile)
        await db.flush()
        user.role = "practitioner"
    await db.commit()
    return {
        "message": f"Application {body.status}",
        "application_id": app_id,
        "user_id": application.user_id,
        "status": body.status,
    }


@router.post("/promoterx/test-report")
async def promoterx_test_report(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger daily report now and return its text. Admin only."""
    report = await PromoterXService.generate_daily_report(db, settings.PROJECT_ID)
    return {"status": "sent", "report": report}
