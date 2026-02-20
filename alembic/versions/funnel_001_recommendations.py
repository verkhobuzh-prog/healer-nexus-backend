"""Create specialist_recommendations table for recommendation funnel

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "specialist_recommendations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="chat"),
        sa.Column("recommended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details_viewed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("details_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("booked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("booked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("links_revealed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("links_revealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("link_clicks", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialists.id"], ondelete=None),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete=None),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete=None),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_spec_rec_project_specialist",
        "specialist_recommendations",
        ["project_id", "specialist_id"],
        unique=False,
    )
    op.create_index(
        "ix_spec_rec_specialist_recommended",
        "specialist_recommendations",
        ["specialist_id", "recommended_at"],
        unique=False,
    )
    op.create_index(
        "ix_spec_rec_user_id",
        "specialist_recommendations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_specialist_recommendations_project_id",
        "specialist_recommendations",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_specialist_recommendations_specialist_id",
        "specialist_recommendations",
        ["specialist_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_specialist_recommendations_specialist_id",
        table_name="specialist_recommendations",
    )
    op.drop_index(
        "ix_specialist_recommendations_project_id",
        table_name="specialist_recommendations",
    )
    op.drop_index("ix_spec_rec_user_id", table_name="specialist_recommendations")
    op.drop_index(
        "ix_spec_rec_specialist_recommended",
        table_name="specialist_recommendations",
    )
    op.drop_index(
        "ix_spec_rec_project_specialist",
        table_name="specialist_recommendations",
    )
    op.drop_table("specialist_recommendations")
