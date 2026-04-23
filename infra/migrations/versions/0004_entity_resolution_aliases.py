"""phase 2 entity resolution aliases

Creates the ``entity_aliases`` table consumed by
``civic_entity_resolution.resolver`` (step 3 of the plan's resolution
order). One row per (entity_kind, alias_text, alias_locale) triple.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-23

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_aliases",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "alias_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("entity_kind", sa.Text(), nullable=False),
        sa.Column(
            "canonical_entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("alias_text", sa.Text(), nullable=False),
        sa.Column("alias_locale", sa.Text(), nullable=False, server_default=sa.text("'he'")),
        sa.Column("alias_source", sa.Text(), nullable=True),
        sa.Column(
            "confidence",
            sa.SmallInteger(),
            server_default=sa.text("100"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "entity_kind IN ('person', 'party', 'office', 'committee', 'bill')",
            name="entity_aliases_kind_check",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="entity_aliases_confidence_check",
        ),
        sa.UniqueConstraint(
            "entity_kind",
            "alias_text",
            "alias_locale",
            name="uq_entity_aliases_triple",
        ),
    )
    op.create_index(
        "idx_entity_aliases_kind_text",
        "entity_aliases",
        ["entity_kind", "alias_text"],
    )


def downgrade() -> None:
    op.drop_index("idx_entity_aliases_kind_text", table_name="entity_aliases")
    op.drop_table("entity_aliases")
