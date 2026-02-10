"""Спільні хендлери та допоміжні функції для ботів (User, Specialist, БД)."""
from __future__ import annotations

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session_maker
from app.models.user import User
from app.models.specialist import Specialist
from app.config import settings

logger = logging.getLogger(__name__)


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None = None) -> User:
    """Отримати або створити користувача за telegram_id."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username, requests_left=5)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Створено користувача telegram_id=%s", telegram_id)
    return user


async def get_specialist_by_telegram_id(telegram_id: int) -> Specialist | None:
    """Отримати спеціаліста за telegram_id."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Specialist).where(Specialist.telegram_id == telegram_id, Specialist.is_active == True)
        )
        return result.scalar_one_or_none()
