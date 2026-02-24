"""Add slug to practitioner_profiles and backfill from specialist name

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "practitioner_profiles",
        sa.Column("slug", sa.String(255), nullable=True),
    )
    op.create_index(
        op.f("ix_practitioner_profiles_slug"),
        "practitioner_profiles",
        ["slug"],
        unique=True,
    )

    # Backfill slugs for existing practitioners from specialist name
    from app.services.blog_slug import generate_slug

    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT pp.id, s.name FROM practitioner_profiles pp "
            "JOIN specialists s ON s.id = pp.specialist_id"
        )
    )
    rows = result.fetchall()
    for row in rows:
        pid, name = row[0], row[1] or ""
        base = generate_slug(name) if name else "practitioner"
        slug = f"{base}-{pid}"
        conn.execute(
            text("UPDATE practitioner_profiles SET slug = :s WHERE id = :id"),
            {"s": slug, "id": pid},
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_practitioner_profiles_slug"), table_name="practitioner_profiles")
    op.drop_column("practitioner_profiles", "slug")
