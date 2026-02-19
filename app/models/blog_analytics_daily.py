"""
Pre-aggregated daily analytics per post (views, unique, referrer breakdown).
"""
from __future__ import annotations

from datetime import date
from sqlalchemy import String, Integer, ForeignKey, Date, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlogAnalyticsDaily(Base):
    """Daily aggregated stats per post."""

    __tablename__ = "blog_analytics_daily"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("blog_posts.id"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    views_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views_unique: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrer_telegram: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrer_facebook: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrer_twitter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrer_google: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrer_direct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrer_other: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "date", name="uq_blog_analytics_post_date"),
        Index("ix_blog_analytics_project_date", "project_id", "date"),
        {"sqlite_autoincrement": True},
    )
