"""blog analytics: blog_post_views and blog_analytics_daily

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blog_post_views",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("referrer_url", sa.String(500), nullable=True),
        sa.Column("referrer_source", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"], ondelete=None),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blog_post_views_post_id", "blog_post_views", ["post_id"], unique=False)
    op.create_index("ix_blog_post_views_project_id", "blog_post_views", ["project_id"], unique=False)
    op.create_index("ix_blog_post_views_viewed_at", "blog_post_views", ["viewed_at"], unique=False)
    op.create_index(
        "ix_blog_post_views_post_viewed",
        "blog_post_views",
        ["post_id", "viewed_at"],
        unique=False,
    )
    op.create_index(
        "ix_blog_post_views_project_viewed",
        "blog_post_views",
        ["project_id", "viewed_at"],
        unique=False,
    )

    op.create_table(
        "blog_analytics_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("views_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views_unique", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referrer_telegram", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referrer_facebook", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referrer_twitter", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referrer_google", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referrer_direct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referrer_other", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"], ondelete=None),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "date", name="uq_blog_analytics_post_date"),
    )
    op.create_index("ix_blog_analytics_daily_post_id", "blog_analytics_daily", ["post_id"], unique=False)
    op.create_index("ix_blog_analytics_daily_project_id", "blog_analytics_daily", ["project_id"], unique=False)
    op.create_index("ix_blog_analytics_daily_date", "blog_analytics_daily", ["date"], unique=False)
    op.create_index(
        "ix_blog_analytics_project_date",
        "blog_analytics_daily",
        ["project_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_blog_analytics_project_date", table_name="blog_analytics_daily")
    op.drop_index("ix_blog_analytics_daily_date", table_name="blog_analytics_daily")
    op.drop_index("ix_blog_analytics_daily_project_id", table_name="blog_analytics_daily")
    op.drop_index("ix_blog_analytics_daily_post_id", table_name="blog_analytics_daily")
    op.drop_table("blog_analytics_daily")
    op.drop_index("ix_blog_post_views_project_viewed", table_name="blog_post_views")
    op.drop_index("ix_blog_post_views_post_viewed", table_name="blog_post_views")
    op.drop_index("ix_blog_post_views_viewed_at", table_name="blog_post_views")
    op.drop_index("ix_blog_post_views_project_id", table_name="blog_post_views")
    op.drop_index("ix_blog_post_views_post_id", table_name="blog_post_views")
    op.drop_table("blog_post_views")
