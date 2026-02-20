"""Password hashing (bcrypt) and JWT token utilities."""
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


def create_access_token(
    user_id: int,
    role: str,
    specialist_id: Optional[int] = None,
    practitioner_id: Optional[int] = None,
    project_id: str = "healer_nexus",
) -> str:
    """Create a short-lived JWT access token (30 min default)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    )
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
    return jwt.encode(
        payload,
        getattr(settings, "JWT_SECRET_KEY", "dev-secret-change-me"),
        algorithm=getattr(settings, "JWT_ALGORITHM", "HS256"),
    )


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived JWT refresh token (7 days default)."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7)
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        getattr(settings, "JWT_SECRET_KEY", "dev-secret-change-me"),
        algorithm=getattr(settings, "JWT_ALGORITHM", "HS256"),
    )


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns payload dict or None."""
    try:
        payload = jwt.decode(
            token,
            getattr(settings, "JWT_SECRET_KEY", "dev-secret-change-me"),
            algorithms=[getattr(settings, "JWT_ALGORITHM", "HS256")],
        )
        if payload.get("type") not in ("access", "refresh"):
            return None
        return payload
    except JWTError:
        return None