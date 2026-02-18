"""blog tags and categories

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blog_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("icon_emoji", sa.String(10), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_id"], ["blog_categories.id"]),
        sa.UniqueConstraint("project_id", "slug", name="uq_blog_categories_project_slug"),
    )
    op.create_index("ix_blog_categories_project_id", "blog_categories", ["project_id"], unique=False)
    op.create_index("ix_blog_categories_parent_id", "blog_categories", ["parent_id"], unique=False)
    op.create_index("ix_blog_categories_slug", "blog_categories", ["slug"], unique=False)
    op.create_index("ix_blog_categories_project_active", "blog_categories", ["project_id", "is_active"], unique=False)

    op.create_table(
        "blog_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "slug", name="uq_blog_tags_project_slug"),
    )
    op.create_index("ix_blog_tags_project_id", "blog_tags", ["project_id"], unique=False)
    op.create_index("ix_blog_tags_slug", "blog_tags", ["slug"], unique=False)

    op.create_table(
        "blog_post_tags",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("post_id", "tag_id", name="pk_blog_post_tags"),
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["blog_tags.id"]),
    )

    op.add_column("blog_posts", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_index("ix_blog_posts_category_id", "blog_posts", ["category_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_blog_posts_category_id", table_name="blog_posts")
    op.drop_column("blog_posts", "category_id")
    op.drop_table("blog_post_tags")
    op.drop_index("ix_blog_tags_slug", table_name="blog_tags")
    op.drop_index("ix_blog_tags_project_id", table_name="blog_tags")
    op.drop_table("blog_tags")
    op.drop_index("ix_blog_categories_project_active", table_name="blog_categories")
    op.drop_index("ix_blog_categories_slug", table_name="blog_categories")
    op.drop_index("ix_blog_categories_parent_id", table_name="blog_categories")
    op.drop_index("ix_blog_categories_project_id", table_name="blog_categories")
    op.drop_table("blog_categories")
