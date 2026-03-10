"""
Healer Nexus — Password hashing (bcrypt) and JWT token utilities.
Fixed: Removed "dev-secret-change-me" fallback. Uses settings.JWT_SECRET_KEY directly.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def hash_token(token: str) -> str:
    """SHA256 hash a token for storage (never store raw tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_ip(ip: str) -> str:
    """SHA256 hash an IP address."""
    return hashlib.sha256(ip.encode()).hexdigest()


def _get_secret_key() -> str:
    """Get JWT secret key. Raises if not configured."""
    key = settings.JWT_SECRET_KEY
    if not key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")
    return key


def _get_algorithm() -> str:
    return settings.JWT_ALGORITHM or "HS256"


def create_access_token(
    user_id: int,
    role: str,
    specialist_id: Optional[int] = None,
    practitioner_id: Optional[int] = None,
    project_id: str = "healer_nexus",
) -> str:
    """Create JWT access token. Admin: 8 hours; others: 30 min default."""
    if role == "admin":
        expire_delta = timedelta(minutes=480)  # 8 hours for admin
    else:
        expire_delta = timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES or 30
        )
    expire = datetime.now(timezone.utc) + expire_delta
    payload = {
        "sub": str(user_id),
        "role": role,
        "project_id": project_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if specialist_id is not None:
        payload["specialist_id"] = specialist_id
    if practitioner_id is not None:
        payload["practitioner_id"] = practitioner_id
    return jwt.encode(payload, _get_secret_key(), algorithm=_get_algorithm())


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived JWT refresh token (7 days default)."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS or 7
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=_get_algorithm())


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns payload dict or None."""
    try:
        payload = jwt.decode(
            token,
            _get_secret_key(),
            algorithms=[_get_algorithm()],
        )
        if payload.get("type") not in ("access", "refresh"):
            return None
        return payload
    except JWTError:
        return None