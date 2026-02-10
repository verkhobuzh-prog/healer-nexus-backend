"""add_project_id_to_core_tables

Revision ID: 20250131000000
Revises:
Create Date: 2025-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250131000000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("project_id", sa.String(50), nullable=False, server_default="healer_nexus"),
    )
    op.create_index("ix_users_project_id", "users", ["project_id"], unique=False)

    op.add_column(
        "specialists",
        sa.Column("project_id", sa.String(50), nullable=False, server_default="healer_nexus"),
    )
    op.create_index("ix_specialists_project_id", "specialists", ["project_id"], unique=False)

    op.add_column(
        "messages",
        sa.Column("project_id", sa.String(50), nullable=False, server_default="healer_nexus"),
    )
    op.create_index("ix_messages_project_id", "messages", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_project_id", table_name="messages")
    op.drop_column("messages", "project_id")

    op.drop_index("ix_specialists_project_id", table_name="specialists")
    op.drop_column("specialists", "project_id")

    op.drop_index("ix_users_project_id", table_name="users")
    op.drop_column("users", "project_id")
