"""
Junction table: BlogPost <-> BlogTag many-to-many. NO CASCADE on FKs.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlogPostTag(Base):
    """Association: post_id <-> tag_id."""

    __tablename__ = "blog_post_tags"

    post_id: Mapped[int] = mapped_column(
        ForeignKey("blog_posts.id"),
        primary_key=True,
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("blog_tags.id"),
        primary_key=True,
        nullable=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint("post_id", "tag_id", name="pk_blog_post_tags"),
    )
