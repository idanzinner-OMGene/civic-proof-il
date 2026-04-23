"""phase 2 postgres-native job queue

Adds a single ``jobs`` table used by the Phase-2 worker
(apps/worker/src/worker/main.py) to claim work with
``FOR UPDATE SKIP LOCKED``. Complements the Phase-1
``parse_jobs`` table — ``parse_jobs`` stays a domain row; ``jobs``
is pipeline plumbing shared by every ingestion adapter.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-23

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.SmallInteger(),
            server_default=sa.text("5"),
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.SmallInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "run_after",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "ingest_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('fetch', 'parse', 'normalize', 'upsert')",
            name="jobs_kind_check",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed', 'dead_letter')",
            name="jobs_status_check",
        ),
    )
    op.create_index(
        "idx_jobs_claim",
        "jobs",
        ["status", "run_after"],
    )
    op.create_index(
        "idx_jobs_kind_status",
        "jobs",
        ["kind", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_kind_status", table_name="jobs")
    op.drop_index("idx_jobs_claim", table_name="jobs")
    op.drop_table("jobs")
