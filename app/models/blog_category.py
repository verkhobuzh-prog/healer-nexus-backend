"""
Blog categories: hierarchical (parent_id self-FK). Multi-project.
"""
from __future__ import annotations

from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BlogCategory(Base, TimestampMixin):
    """Категорія блогу (ієрархічна)."""

    __tablename__ = "blog_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("blog_categories.id"),
        nullable=True,
        index=True,
    )
    icon_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["BlogCategory | None"] = relationship(
        "BlogCategory",
        remote_side="BlogCategory.id",
        foreign_keys=[parent_id],
        back_populates="children",
    )
    children: Mapped[list["BlogCategory"]] = relationship(
        "BlogCategory",
        back_populates="parent",
        foreign_keys=[parent_id],
    )

    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_blog_categories_project_slug"),
        Index("ix_blog_categories_project_active", "project_id", "is_active"),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<BlogCategory(id={self.id}, slug={self.slug!r})>"
