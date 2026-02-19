"""
Blog view events: one row per view with referrer, device, ip_hash for analytics.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlogPostView(Base):
    """Single view event for a blog post."""

    __tablename__ = "blog_post_views"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("blog_posts.id"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    referrer_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referrer_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_blog_post_views_post_viewed", "post_id", "viewed_at"),
        Index("ix_blog_post_views_project_viewed", "project_id", "viewed_at"),
        {"sqlite_autoincrement": True},
    )
