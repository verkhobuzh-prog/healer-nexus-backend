"""add role column to specialists

Revision ID: 20250131100000
Revises: 562214e6051d
Create Date: 2025-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250131100000"
down_revision: Union[str, None] = "562214e6051d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "specialists",
        sa.Column("role", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("specialists", "role")
