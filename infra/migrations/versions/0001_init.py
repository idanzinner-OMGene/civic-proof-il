"""init - phase 0 placeholder schema

Revision ID: 0001
Revises:
Create Date: 2026-04-21

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schema_migrations_info",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute(
        "INSERT INTO schema_migrations_info (note) VALUES ('phase-0 bootstrap: no domain schema yet')"
    )


def downgrade() -> None:
    op.drop_table("schema_migrations_info")
