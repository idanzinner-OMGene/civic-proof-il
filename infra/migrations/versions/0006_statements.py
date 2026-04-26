"""phase 3 statements and statement_claims

Persists incoming statements (the raw input to ``POST /claims/verify``)
and the atomic claims the decomposer produces from each statement. Gives
the API a stable join key so re-runs and review actions can trace a
verdict back to the original statement text.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "statements",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "statement_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("speaker_hint", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_family", sa.Text(), nullable=True),
        sa.Column(
            "received_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "language IN ('he', 'en')",
            name="statements_language_check",
        ),
    )
    op.create_index(
        "idx_statements_received_at",
        "statements",
        ["received_at"],
    )

    op.create_table(
        "statement_claims",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "statement_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("claim_type", sa.Text(), nullable=False),
        sa.Column("checkability", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column(
            "slots",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "time_scope",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "statement_id", "claim_id", name="uq_statement_claim"
        ),
        sa.CheckConstraint(
            "claim_type IN ('vote_cast','bill_sponsorship','office_held',"
            "'committee_membership','committee_attendance',"
            "'statement_about_formal_action')",
            name="statement_claims_type_check",
        ),
        sa.CheckConstraint(
            "checkability IN ('checkable','non_checkable',"
            "'insufficient_time_scope','insufficient_entity_resolution')",
            name="statement_claims_checkability_check",
        ),
        sa.CheckConstraint(
            "method IN ('rules', 'llm', 'rules+llm')",
            name="statement_claims_method_check",
        ),
    )
    op.create_index(
        "idx_statement_claims_statement_id",
        "statement_claims",
        ["statement_id"],
    )
    op.create_index(
        "idx_statement_claims_claim_id",
        "statement_claims",
        ["claim_id"],
    )
    op.create_foreign_key(
        "fk_statement_claims_statement",
        "statement_claims",
        "statements",
        ["statement_id"],
        ["statement_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_statement_claims_statement", "statement_claims", type_="foreignkey"
    )
    op.drop_index("idx_statement_claims_claim_id", table_name="statement_claims")
    op.drop_index(
        "idx_statement_claims_statement_id", table_name="statement_claims"
    )
    op.drop_table("statement_claims")
    op.drop_index("idx_statements_received_at", table_name="statements")
    op.drop_table("statements")
