"""phase 1 domain schema

Creates the nine Phase-1 pipeline tables listed in
docs/political_verifier_v_1_plan.md lines 232-241:

    1. ingest_runs           (plan line 233)
    2. raw_fetch_objects     (plan line 234)
    3. parse_jobs            (plan line 235)
    4. normalized_records    (plan line 236)
    5. entity_candidates     (plan line 237)
    6. review_tasks          (plan line 238)
    7. review_actions        (plan line 239)
    8. verification_runs     (plan line 240)
    9. verdict_exports       (plan line 241)

Plus supporting indexes:
    - idx_raw_fetch_objects_archive_uri
    - idx_normalized_records_kind
    - idx_review_tasks_status_priority
    - idx_verification_runs_claim_id

Shared cross-agent contracts (frozen in the phase plan):
    - Business keys are UUID (postgresql.UUID(as_uuid=True)), with a
      surrogate BIGSERIAL `id` PK plus a `<entity>_id UUID UNIQUE` key.
    - All timestamps are TIMESTAMPTZ.
    - `source_tier` is an INT with CHECK (source_tier IN (1, 2, 3)).

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-21

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("source_family", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "stats",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ingest_runs_status_check",
        ),
    )

    op.create_table(
        "raw_fetch_objects",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "object_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "ingest_run_id",
            sa.BigInteger(),
            sa.ForeignKey("ingest_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("archive_uri", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.Text(), nullable=False, unique=True),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column(
            "captured_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source_tier", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "source_tier IN (1, 2, 3)",
            name="raw_fetch_objects_source_tier_check",
        ),
    )
    op.create_index(
        "idx_raw_fetch_objects_archive_uri",
        "raw_fetch_objects",
        ["archive_uri"],
    )

    op.create_table(
        "parse_jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "raw_fetch_object_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_fetch_objects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("parser_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name="parse_jobs_status_check",
        ),
    )

    op.create_table(
        "normalized_records",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "record_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "parse_job_id",
            sa.BigInteger(),
            sa.ForeignKey("parse_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("record_kind", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("source_tier", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "record_kind IN ("
            "'person', 'office', 'party', 'committee', 'bill', "
            "'membership', 'vote', 'sponsorship', 'attendance', 'source_document'"
            ")",
            name="normalized_records_kind_check",
        ),
        sa.CheckConstraint(
            "source_tier IN (1, 2, 3)",
            name="normalized_records_source_tier_check",
        ),
    )
    op.create_index(
        "idx_normalized_records_kind",
        "normalized_records",
        ["record_kind"],
    )

    op.create_table(
        "entity_candidates",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("mention_text", sa.Text(), nullable=False),
        sa.Column(
            "resolved_person_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("confidence", sa.REAL(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="entity_candidates_confidence_check",
        ),
    )

    op.create_table(
        "review_tasks",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "priority",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("assigned_to", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('entity_resolution', 'verdict', 'conflict')",
            name="review_tasks_kind_check",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'claimed', 'resolved', 'escalated')",
            name="review_tasks_status_check",
        ),
    )
    op.create_index(
        "idx_review_tasks_status_priority",
        "review_tasks",
        ["status", sa.text("priority DESC")],
    )

    op.create_table(
        "review_actions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "action_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "task_id",
            sa.BigInteger(),
            sa.ForeignKey("review_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column(
            "diff",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('approve', 'reject', 'relink', 'annotate', 'escalate')",
            name="review_actions_action_check",
        ),
    )

    op.create_table(
        "verification_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("ruleset_version", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("verdict", postgresql.JSONB(), nullable=False),
        sa.Column(
            "needs_human_review",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_verification_runs_claim_id",
        "verification_runs",
        ["claim_id"],
    )

    op.create_table(
        "verdict_exports",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "verdict_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "verification_run_id",
            sa.BigInteger(),
            sa.ForeignKey("verification_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exported_to", sa.Text(), nullable=False),
        sa.Column(
            "exported_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("verdict_exports")
    op.drop_index("idx_verification_runs_claim_id", table_name="verification_runs")
    op.drop_table("verification_runs")
    op.drop_table("review_actions")
    op.drop_index("idx_review_tasks_status_priority", table_name="review_tasks")
    op.drop_table("review_tasks")
    op.drop_table("entity_candidates")
    op.drop_index("idx_normalized_records_kind", table_name="normalized_records")
    op.drop_table("normalized_records")
    op.drop_table("parse_jobs")
    op.drop_index("idx_raw_fetch_objects_archive_uri", table_name="raw_fetch_objects")
    op.drop_table("raw_fetch_objects")
    op.drop_table("ingest_runs")
