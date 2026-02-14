"""Add practitioner personalization columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "practitioner_profiles",
        sa.Column("unique_story", sa.Text(), nullable=True),
    )
    op.add_column(
        "practitioner_profiles",
        sa.Column("soft_cta_text", sa.String(500), nullable=True),
    )
    op.add_column(
        "practitioner_profiles",
        sa.Column("contact_link", sa.String(255), nullable=True),
    )
    op.add_column(
        "practitioner_profiles",
        sa.Column(
            "creator_signature",
            sa.String(255),
            nullable=False,
            server_default="Створено з ❤️ на платформі Healer Nexus",
        ),
    )


def downgrade() -> None:
    op.drop_column("practitioner_profiles", "creator_signature")
    op.drop_column("practitioner_profiles", "contact_link")
    op.drop_column("practitioner_profiles", "soft_cta_text")
    op.drop_column("practitioner_profiles", "unique_story")
