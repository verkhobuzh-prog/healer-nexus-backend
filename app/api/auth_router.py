"""Auth API: register, login, refresh, logout, change-password, me."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.models.specialist_application import SpecialistApplication, ApplicationStatus
from app.schemas.specialist_application import ApplicationCreate, ApplicationResponse
from app.config import settings
from app.database.connection import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserBrief,
    MessageResponse,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _expires_in_seconds() -> int:
    return settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


async def _user_brief_from_user(
    session: AsyncSession,
    user,
    specialist_id: int | None = None,
    practitioner_id: int | None = None,
) -> UserBrief:
    if specialist_id is not None or practitioner_id is not None:
        return UserBrief(
            id=user.id,
            email=user.email or "",
            name=user.username,
            role=user.role,
            specialist_id=specialist_id,
            practitioner_id=practitioner_id,
        )
    svc = AuthService(session)
    sid, pid = await svc._get_user_ids(user)
    return UserBrief(
        id=user.id,
        email=user.email or "",
        name=user.username,
        role=user.role,
        specialist_id=sid,
        practitioner_id=pid,
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user. Returns access and refresh tokens."""
    svc = AuthService(db)
    try:
        user, access_token, refresh_token = await svc.register(
            email=body.email,
            password=body.password,
            name=body.name,
            role=body.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Register failed for {body.email}: {e}")
        raise HTTPException(status_code=500, detail="Registration error")

    try:
        sid, pid = await svc._get_user_ids(user)
        user_brief = UserBrief(
            id=user.id,
            email=user.email or "",
            name=user.username,
            role=user.role,
            specialist_id=sid,
            practitioner_id=pid,
        )
    except Exception as e:
        logger.exception(f"Register post-processing failed for user {user.id}: {e}")
        user_brief = UserBrief(
            id=user.id,
            email=user.email or "",
            name=user.username or "",
            role=user.role or "user",
            specialist_id=None,
            practitioner_id=None,
        )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=_expires_in_seconds(),
        user=user_brief,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password. Returns access and refresh tokens."""
    svc = AuthService(db)
    try:
        user, access_token, refresh_token = await svc.login(
            email=body.email,
            password=body.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.exception(f"Login failed for {body.email}: {e}")
        raise HTTPException(status_code=500, detail="Login error")

    try:
        sid, pid = await svc._get_user_ids(user)
        user_brief = UserBrief(
            id=user.id,
            email=user.email or "",
            name=user.username,
            role=user.role,
            specialist_id=sid,
            practitioner_id=pid,
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=_expires_in_seconds(),
            user=user_brief,
        )
    except Exception as e:
        logger.exception(f"Login post-processing failed for user {user.id}: {e}")
        # Повернути токен навіть якщо UserBrief не створився
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=_expires_in_seconds(),
            user=UserBrief(
                id=user.id,
                email=user.email or "",
                name=user.username or "",
                role=user.role or "user",
                specialist_id=None,
                practitioner_id=None,
            ),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get new access and refresh tokens using a valid refresh token."""
    svc = AuthService(db)
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None
    try:
        new_access, new_refresh = await svc.refresh_tokens(
            body.refresh_token,
            user_agent=user_agent,
            ip=client_host,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    payload = decode_token(new_access)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = int(payload["sub"])
    r = await db.execute(select(User).where(User.id == user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    sid, pid = await svc._get_user_ids(user)
    user_brief = UserBrief(
        id=user.id,
        email=user.email or "",
        name=user.username,
        role=user.role,
        specialist_id=sid,
        practitioner_id=pid,
    )
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=_expires_in_seconds(),
        user=user_brief,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Revoke the given refresh token (logout this session)."""
    svc = AuthService(db)
    ok = await svc.logout(body.refresh_token)
    return MessageResponse(message="Logged out" if ok else "Token was already invalid")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all refresh tokens for the current user (logout all sessions)."""
    svc = AuthService(db)
    count = await svc.logout_all(user.id)
    return MessageResponse(message=f"Revoked {count} session(s)")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the current user. All sessions are revoked."""
    svc = AuthService(db)
    try:
        await svc.change_password(user.id, body.old_password, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MessageResponse(message="Password changed. Please log in again.")


@router.get("/me", response_model=UserBrief)
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current user info from JWT."""
    brief = await _user_brief_from_user(db, user)
    return brief
# --- Specialist Application Extension ---
@router.post("/apply-specialist", response_model=ApplicationResponse, status_code=201)
async def apply_specialist(
    body: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User applies to become a specialist. Admin reviews later."""
    if user.role == "practitioner":
        raise HTTPException(400, "You are already a practitioner")
    # Check no pending application
    existing = await db.execute(
        select(SpecialistApplication)
        .where(SpecialistApplication.user_id == user.id)
        .where(SpecialistApplication.status == ApplicationStatus.PENDING)
    )
    if existing.scalars().first():
        raise HTTPException(400, "You already have a pending application")
    application = SpecialistApplication(
        user_id=user.id,
        name=body.name,
        specialty=body.specialty,
        service_type=body.service_type,
        bio=body.bio,
        experience_years=body.experience_years,
        motivation=body.motivation,
        hourly_rate=body.hourly_rate,
        contact_telegram=body.contact_telegram,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application
