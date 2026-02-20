"""FastAPI dependencies for JWT authentication."""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database.connection import get_db
from app.models.practitioner_profile import PractitionerProfile
from app.models.specialist import Specialist
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate user from JWT access token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Attach extra info from token to user object for convenience
    user._role = payload.get("role", "user")
    user._specialist_id = payload.get("specialist_id")
    user._practitioner_id = payload.get("practitioner_id")
    user._project_id = payload.get("project_id", "healer_nexus")
    return user


async def get_current_practitioner(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PractitionerProfile:
    """Get practitioner profile for the current user. Raises 403 if not a practitioner."""
    practitioner_id = getattr(user, "_practitioner_id", None)
    if not practitioner_id:
        raise HTTPException(status_code=403, detail="Not a practitioner")

    profile = await db.get(PractitionerProfile, practitioner_id)
    if not profile:
        raise HTTPException(status_code=403, detail="Practitioner profile not found")
    return profile


async def get_current_specialist(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Specialist:
    """Get specialist for the current user. Raises 403 if not a specialist."""
    specialist_id = getattr(user, "_specialist_id", None)
    if not specialist_id:
        raise HTTPException(status_code=403, detail="Not a specialist")

    specialist = await db.get(Specialist, specialist_id)
    if not specialist:
        raise HTTPException(status_code=403, detail="Specialist profile not found")
    return specialist


def require_role(*roles: str):
    """Dependency factory: require user to have one of the given roles."""

    async def check_role(user: User = Depends(get_current_user)):
        if getattr(user, "_role", "user") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return user

    return check_role


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None if no token provided."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
