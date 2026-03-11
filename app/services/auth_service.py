"""Auth service: register, login, refresh, logout, change password."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    hash_ip,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.specialist import Specialist
from app.models.practitioner_profile import PractitionerProfile


def _generate_unique_slug(name: str, specialist_id: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        slug = "specialist"
    short_id = uuid.uuid4().hex[:6]
    return f"{slug}-{specialist_id}-{short_id}"


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(
        self,
        email: str,
        password: str,
        name: str,
        role: str = "user",
    ) -> tuple[User, str, str]:
        # Validate email not taken
        r = await self.session.execute(select(User).where(User.email == email))
        if r.scalar_one_or_none():
            raise ValueError("Email already registered")

        password_hash = hash_password(password)
        user = User(
            email=email,
            password_hash=password_hash,
            username=name,
            role=role,
            is_active=True,
            telegram_id=None,
        )
        self.session.add(user)
        await self.session.flush()

        specialist_id: int | None = None
        practitioner_id: int | None = None

        # Specialist + PractitionerProfile тільки для role == "practitioner".
        # Для role "user" та "admin" нічого не створюємо.
        if role == "practitioner":
            specialist = Specialist(
                user_id=user.id,
                name=name,
                service_type="healer",
                specialty="General",
                delivery_method="human",
            )
            self.session.add(specialist)
            await self.session.flush()
            specialist_id = specialist.id
            profile = PractitionerProfile(
                project_id=settings.PROJECT_ID or "healer_nexus",
                specialist_id=specialist.id,
                slug=_generate_unique_slug(name, specialist.id),
                empathy_ratio=0.8,
                style="warm",
                preferences={},
                is_active=True,
                creator_signature=name,
            )
            self.session.add(profile)
            await self.session.flush()
            practitioner_id = profile.id

        access_token = create_access_token(
            user_id=user.id,
            role=role,
            specialist_id=specialist_id,
            practitioner_id=practitioner_id,
            project_id=settings.PROJECT_ID,
        )
        refresh_token = create_refresh_token(user_id=user.id)
        await self._store_refresh_token(user.id, refresh_token)
        await self.session.commit()
        await self.session.refresh(user)
        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        r = await self.session.execute(select(User).where(User.email == email))
        user = r.scalar_one_or_none()
        if not user:
            raise ValueError("Invalid email or password")
        if not user.password_hash or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        if not getattr(user, "is_active", True):
            raise ValueError("Account is inactive")

        user.last_login_at = datetime.now(timezone.utc)
        specialist_id, practitioner_id = await self._get_user_ids(user)
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            specialist_id=specialist_id,
            practitioner_id=practitioner_id,
            project_id=settings.PROJECT_ID,
        )
        refresh_token = create_refresh_token(user.id)
        await self._store_refresh_token(user.id, refresh_token)
        await self.session.commit()
        await self.session.refresh(user)
        return user, access_token, refresh_token

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> tuple[str, str]:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid or expired refresh token")
        user_id = int(payload["sub"])
        token_hash = hash_token(refresh_token)

        r = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
            )
        )
        rt = r.scalar_one_or_none()
        if not rt or rt.user_id != user_id:
            raise ValueError("Invalid or expired refresh token")
        exp = rt.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise ValueError("Refresh token expired")

        rt.revoked = True
        rt.revoked_at = datetime.now(timezone.utc)

        r = await self.session.execute(select(User).where(User.id == user_id))
        user = r.scalar_one_or_none()
        if not user or not getattr(user, "is_active", True):
            raise ValueError("User not found or inactive")

        specialist_id, practitioner_id = await self._get_user_ids(user)
        new_access = create_access_token(
            user_id=user.id,
            role=user.role,
            specialist_id=specialist_id,
            practitioner_id=practitioner_id,
            project_id=settings.PROJECT_ID,
        )
        new_refresh = create_refresh_token(user.id)
        await self._store_refresh_token(user.id, new_refresh, user_agent=user_agent, ip=ip)
        await self.session.commit()
        return new_access, new_refresh

    async def logout(self, refresh_token: str) -> bool:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return False
        token_hash = hash_token(refresh_token)
        r = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        rt = r.scalar_one_or_none()
        if not rt:
            return False
        rt.revoked = True
        rt.revoked_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    async def logout_all(self, user_id: int) -> int:
        r = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            )
        )
        tokens = list(r.scalars().all())
        now = datetime.now(timezone.utc)
        for rt in tokens:
            rt.revoked = True
            rt.revoked_at = now
        await self.session.commit()
        return len(tokens)

    async def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> bool:
        r = await self.session.execute(select(User).where(User.id == user_id))
        user = r.scalar_one_or_none()
        if not user or not user.password_hash:
            raise ValueError("User not found")
        if not verify_password(old_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        user.password_hash = hash_password(new_password)
        await self.logout_all(user_id)
        await self.session.commit()
        return True

    async def _store_refresh_token(
        self,
        user_id: int,
        token: str,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> None:
        token_hash = hash_token(token)
        expires_at = datetime.now(timezone.utc)
        from datetime import timedelta
        expires_at = expires_at + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        ip_hash = hash_ip(ip) if ip else None
        rt = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_hash=ip_hash,
        )
        self.session.add(rt)

    async def _get_user_ids(
        self,
        user: User,
        project_id: str | None = None,
    ) -> tuple[int | None, int | None]:
        project_id = project_id or settings.PROJECT_ID
        r = await self.session.execute(
            select(Specialist).where(Specialist.user_id == user.id)
        )
        specialist = r.scalars().first()
        if not specialist:
            return None, None
        r2 = await self.session.execute(
            select(PractitionerProfile).where(
                PractitionerProfile.specialist_id == specialist.id,
                PractitionerProfile.project_id == project_id,
            )
        )
        profile = r2.scalars().first()
        practitioner_id = profile.id if profile else None
        return specialist.id, practitioner_id
