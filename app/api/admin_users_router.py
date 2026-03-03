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
                "name": u.name,
                "role": u.role,
                "specialist_id": u.specialist_id,
                "practitioner_id": u.practitioner_id,
                "created_at": str(u.created_at) if hasattr(u, "created_at") else None,
            }
            for u in users
        ],
        "total": total,
    }
@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    body: RoleUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change user role. Admin only."""
    if body.role not in ("user", "practitioner", "admin"):
        raise HTTPException(400, "Invalid role. Use: user, practitioner, admin")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.role = body.role
    await db.commit()
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
            project_id="healer_nexus",
            name=application.name,
            specialty=application.specialty,
            service_type=application.service_type,
            service_types=[application.specialty],
            hourly_rate=application.hourly_rate,
            bio=application.bio,
            is_verified=True,
            is_active=True,
            delivery_method="human",
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
        user.specialist_id = specialist.id
        user.practitioner_id = profile.id
    await db.commit()
    return {
        "message": f"Application {body.status}",
        "application_id": app_id,
        "user_id": application.user_id,
        "status": body.status,
    }
