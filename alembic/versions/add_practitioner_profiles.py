"""Add practitioner_profiles table

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "practitioner_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(50), nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("empathy_ratio", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("style", sa.String(50), nullable=False, server_default="calm"),
        sa.Column("persona_notes", sa.Text(), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialists.id"]),
    )
    op.create_index(op.f("ix_practitioner_profiles_project_id"), "practitioner_profiles", ["project_id"], unique=False)
    op.create_index(op.f("ix_practitioner_profiles_specialist_id"), "practitioner_profiles", ["specialist_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_practitioner_profiles_specialist_id"), table_name="practitioner_profiles")
    op.drop_index(op.f("ix_practitioner_profiles_project_id"), table_name="practitioner_profiles")
    op.drop_table("practitioner_profiles")
