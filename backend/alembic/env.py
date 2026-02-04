"""Alembic env: sync migrations for asyncpg / SQLite project."""
from __future__ import annotations

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import ALL models
from app.models.base import Base
from app.models.user import User  # noqa: F401
from app.models.specialist import Specialist  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.healer import Healer  # noqa: F401

logger = logging.getLogger("alembic.env")

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    """Convert async DATABASE_URL to sync for migrations."""
    from app.config import settings

    db_url = settings.DATABASE_URL

    if "postgresql+asyncpg" in db_url:
        sync_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    elif "postgresql+psycopg2" in db_url:
        sync_url = db_url
    elif db_url.startswith("postgresql://"):
        sync_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif "sqlite+aiosqlite" in db_url:
        sync_url = db_url.replace("sqlite+aiosqlite", "sqlite", 1)
    elif db_url.startswith("sqlite://"):
        sync_url = db_url
    else:
        raise ValueError(
            f"Unsupported DATABASE_URL scheme.\n"
            "Expected: postgresql+asyncpg, postgresql+psycopg2, postgresql, sqlite+aiosqlite, or sqlite."
        )

    logger.info("Using sync migration URL (driver: %s)", "psycopg2" if "psycopg2" in sync_url else "sqlite")
    return sync_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL)."""
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB)."""
    sync_url = get_sync_url()
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = sync_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
