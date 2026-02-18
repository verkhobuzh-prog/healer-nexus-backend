"""
Blog posts: practitioner-authored articles with slug, status, optional AI generation.
Multi-project: project_id on every row. FK to practitioner_profiles.id (no CASCADE).
"""
from __future__ import annotations

import re
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, UniqueConstraint, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import Base, TimestampMixin


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EditorType(str, enum.Enum):
    MARKDOWN = "markdown"
    WYSIWYG = "wysiwyg"


class BlogPost(Base, TimestampMixin):
    """Пост блогу практика."""

    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    practitioner_id: Mapped[int] = mapped_column(
        ForeignKey("practitioner_profiles.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(600), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    editor_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EditorType.MARKDOWN.value
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PostStatus.DRAFT.value, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    featured_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    telegram_discussion_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_prompt_topic: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("blog_categories.id"),
        nullable=True,
        index=True,
    )

    practitioner: Mapped["PractitionerProfile"] = relationship(
        "PractitionerProfile",
        lazy="selectin",
        foreign_keys=[practitioner_id],
    )
    category: Mapped["BlogCategory | None"] = relationship(
        "BlogCategory",
        lazy="selectin",
        foreign_keys=[category_id],
    )
    tags: Mapped[list["BlogTag"]] = relationship(
        "BlogTag",
        secondary="blog_post_tags",
        lazy="selectin",
        backref="posts",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_blog_posts_project_slug"),
        Index("ix_blog_posts_project_status", "project_id", "status"),
        Index("ix_blog_posts_practitioner_status", "practitioner_id", "status"),
        {"sqlite_autoincrement": True},
    )

    @property
    def reading_time_minutes(self) -> int:
        """Approximate reading time: word_count / 200."""
        if not self.content or not self.content.strip():
            return 0
        word_count = len(re.findall(r"\S+", self.content))
        return max(1, (word_count + 199) // 200)

    def __repr__(self) -> str:
        return f"<BlogPost(id={self.id}, slug={self.slug!r}, status={self.status})>"


