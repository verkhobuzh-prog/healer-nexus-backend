"""JWT auth: users email/password/role, refresh_tokens, specialists.user_id

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: add JWT/auth columns; make telegram_id nullable (SQLite batch)
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("role", sa.String(20), nullable=False, server_default="user"))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column(
            "telegram_id",
            existing_type=sa.BigInteger(),
            nullable=True,
        )
        batch_op.create_index("ix_users_email", ["email"], unique=True)

    # --- refresh_tokens table (no CASCADE)
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete=None),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_user_revoked", "refresh_tokens", ["user_id", "revoked"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    # --- specialists: add user_id (SQLite batch)
    with op.batch_alter_table("specialists", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_specialists_user_id", "users", ["user_id"], ["id"])
        batch_op.create_index("ix_specialists_user_id", ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("specialists", schema=None) as batch_op:
        batch_op.drop_index("ix_specialists_user_id", table_name="specialists")
        batch_op.drop_constraint("fk_specialists_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")

    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_revoked", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_email", table_name="users")
        batch_op.alter_column("telegram_id", existing_type=sa.BigInteger(), nullable=False)
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("role")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("email")
