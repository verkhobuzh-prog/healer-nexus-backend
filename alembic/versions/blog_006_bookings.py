"""bookings table for chat + specialists integration

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("practitioner_id", sa.Integer(), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=True),
        sa.Column("specialist_notes", sa.Text(), nullable=True),
        sa.Column("telegram_notified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("contact_method", sa.String(50), nullable=False, server_default="telegram"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(datetime('now'))"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(datetime('now'))"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete=None),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialists.id"], ondelete=None),
        sa.ForeignKeyConstraint(["practitioner_id"], ["practitioner_profiles.id"], ondelete=None),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete=None),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_project_id", "bookings", ["project_id"], unique=False)
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], unique=False)
    op.create_index("ix_bookings_specialist_id", "bookings", ["specialist_id"], unique=False)
    op.create_index("ix_bookings_practitioner_id", "bookings", ["practitioner_id"], unique=False)
    op.create_index("ix_bookings_conversation_id", "bookings", ["conversation_id"], unique=False)
    op.create_index("ix_bookings_status", "bookings", ["status"], unique=False)
    op.create_index("ix_bookings_project_status", "bookings", ["project_id", "status"], unique=False)
    op.create_index("ix_bookings_specialist_status", "bookings", ["specialist_id", "status"], unique=False)
    op.create_index("ix_bookings_user_created", "bookings", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookings_user_created", table_name="bookings")
    op.drop_index("ix_bookings_specialist_status", table_name="bookings")
    op.drop_index("ix_bookings_project_status", table_name="bookings")
    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_index("ix_bookings_conversation_id", table_name="bookings")
    op.drop_index("ix_bookings_practitioner_id", table_name="bookings")
    op.drop_index("ix_bookings_specialist_id", table_name="bookings")
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_index("ix_bookings_project_id", table_name="bookings")
    op.drop_table("bookings")
