"""add telegram_channel_id to practitioner_profiles

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("practitioner_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("telegram_channel_id", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("practitioner_profiles", schema=None) as batch_op:
        batch_op.drop_column("telegram_channel_id")
