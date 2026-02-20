"""Add social_links JSON to practitioner_profiles

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("practitioner_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("social_links", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("practitioner_profiles", schema=None) as batch_op:
        batch_op.drop_column("social_links")
