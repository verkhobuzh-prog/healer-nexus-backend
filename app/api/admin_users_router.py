"""
Admin API: manage users, roles, specialist applications.
Only accessible by admin role.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_admin
from app.database.connection import get_db
from app.models.user import User
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile
from app.models.specialist_application import SpecialistApplication, ApplicationStatus
from app.schemas.specialist_application import (
    ApplicationResponse,
    ApplicationReview,
    RoleUpdate,
)
from app.core.security import hash_password
from app.config import settings
from app.services.promoterx_service import PromoterXService

router = APIRouter(prefix="/api/admin", tags=["Admin"])
# --- Users ---
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
    await _apply_role_update(user_id, body.role, db)
    return {"message": f"User {user_id} role updated to {body.role}", "user_id": user_id, "role": body.role}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    body: RoleUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change user role. Admin only."""
    await _apply_role_update(user_id, body.role, db)
    return {"message": f"User {user_id} role updated to {body.role}", "user_id": user_id, "role": body.role}
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete user account. Admin only."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "admin":
        raise HTTPException(400, "Cannot delete admin account")
    await db.delete(user)
    await db.commit()
    return {"message": f"User {user_id} deleted"}


@router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_password = body.get("password")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user.hashed_password = pwd_context.hash(new_password)
    await db.commit()

    return {"message": "Password updated", "user_id": user_id}


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
        slug = application.name.lower().replace(" ", "-").replace("'", "")
        profile = PractitionerProfile(
            project_id="healer_nexus",
            specialist_id=specialist.id,
            slug=slug,
            unique_story=application.motivation or application.bio[:200],
            empathy_ratio=0.8,
            style="warm",
            social_links={"telegram": application.contact_telegram} if application.contact_telegram else {},
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
