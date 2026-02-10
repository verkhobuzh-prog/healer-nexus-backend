"""
Single source of database connection logic.
Registry Pattern, async-first. Used by API, modules, and Telegram bots.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from app.config import settings
from app.models.base import Base

logger = logging.getLogger(__name__)

# ── Single engine (no duplicates) ───────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# ── Single session maker (no duplicates) ────────────────────────────────────
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Lifecycle ───────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Create tables and verify connection. Called from main.py lifespan."""
    try:
        # Import models so Base.metadata knows all tables (avoid circular imports)
        from app.models.user import User  # noqa: F401
        from app.models.message import Message  # noqa: F401
        from app.models.specialist import Specialist  # noqa: F401
        from app.models.healer import Healer  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database engine initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed: %s", e, exc_info=True)
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one async session per request."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error: %s", e, exc_info=True)
            raise


# ── Health check (Registry / monitoring) ─────────────────────────────────────
async def check_db_health() -> dict:
    """Connection pooling health check for ModuleRegistry / health endpoints."""
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        pool_size_attr = getattr(engine.pool, "size", None)
        pool_size = pool_size_attr() if callable(pool_size_attr) else pool_size_attr
        return {"status": "healthy", "pool_size": pool_size}
    except Exception as e:
        logger.error("Database health check failed: %s", e, exc_info=True)
        return {"status": "down", "error": str(e)}


# ── ModuleRegistry / EventBus placeholder ───────────────────────────────────
async def emit_event(
    project_id: str,
    event_type: str,
    module_name: str,
    data: dict,
    severity: str = "info",
) -> None:
    """Placeholder for EventBus integration (Phase 2)."""
    logger.info(
        "Event: %s:%s:%s",
        project_id,
        event_type,
        module_name,
        extra={"severity": severity, "data": data},
    )


# ── Helpers (moved from db_service) ─────────────────────────────────────────
async def save_message(user_id: int, role: str, content: str) -> None:
    """Persist one message to history (project_id from settings)."""
    from app.models.message import Message

    async with async_session_maker() as session:
        async with session.begin():
            session.add(
                Message(
                    project_id=settings.PROJECT_ID,
                    user_id=user_id,
                    role=role,
                    content=content,
                )
            )


async def get_history(user_id: int, limit: int = 10) -> list[dict]:
    """Return last N messages for context (oldest to newest), scoped by project_id."""
    from app.models.message import Message

    async with async_session_maker() as session:
        result = await session.execute(
            select(Message)
            .where(
                Message.user_id == user_id,
                Message.project_id == settings.PROJECT_ID,
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]
