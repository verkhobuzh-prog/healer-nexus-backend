"""create blog_posts table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("practitioner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(600), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("editor_type", sa.String(20), nullable=False, server_default="markdown"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("featured_image_url", sa.String(1000), nullable=True),
        sa.Column("meta_title", sa.String(255), nullable=True),
        sa.Column("meta_description", sa.String(500), nullable=True),
        sa.Column("views_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("telegram_discussion_url", sa.String(500), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("ai_prompt_topic", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["practitioner_id"], ["practitioner_profiles.id"]),
        sa.UniqueConstraint("project_id", "slug", name="uq_blog_posts_project_slug"),
    )
    op.create_index("ix_blog_posts_project_id", "blog_posts", ["project_id"], unique=False)
    op.create_index("ix_blog_posts_practitioner_id", "blog_posts", ["practitioner_id"], unique=False)
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], unique=False)
    op.create_index("ix_blog_posts_status", "blog_posts", ["status"], unique=False)
    op.create_index("ix_blog_posts_project_status", "blog_posts", ["project_id", "status"], unique=False)
    op.create_index("ix_blog_posts_practitioner_status", "blog_posts", ["practitioner_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_blog_posts_practitioner_status", table_name="blog_posts")
    op.drop_index("ix_blog_posts_project_status", table_name="blog_posts")
    op.drop_index("ix_blog_posts_status", table_name="blog_posts")
    op.drop_index("ix_blog_posts_slug", table_name="blog_posts")
    op.drop_index("ix_blog_posts_practitioner_id", table_name="blog_posts")
    op.drop_index("ix_blog_posts_project_id", table_name="blog_posts")
    op.drop_table("blog_posts")
