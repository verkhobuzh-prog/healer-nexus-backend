"""Alembic env: sync URL from app config (SQLite)."""
from __future__ import annotations

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.models.base import Base
from app.models.user import User  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.specialist import Specialist  # noqa: F401
from app.models.healer import Healer  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.specialist_content import SpecialistContent  # noqa: F401
from app.models.practitioner_profile import PractitionerProfile  # noqa: F401
from app.models.blog_post import BlogPost  # noqa: F401

logger = logging.getLogger("alembic.env")
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def get_url() -> str:
    from app.config import settings
    url = settings.DATABASE_URL
    if "sqlite+aiosqlite" in url:
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conf = config.get_section(config.config_ini_section) or {}
    conf["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(conf, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
