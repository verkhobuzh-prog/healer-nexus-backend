"""
Blog tags: flat, many-to-many with posts. Multi-project. usage_count denormalized.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, UniqueConstraint, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class BlogTag(Base):
    """Тег блогу (плоский список)."""

    __tablename__ = "blog_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_blog_tags_project_slug"),
        Index("ix_blog_tags_project_id", "project_id"),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<BlogTag(id={self.id}, slug={self.slug!r})>"
