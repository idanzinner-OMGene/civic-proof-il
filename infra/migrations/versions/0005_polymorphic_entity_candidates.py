"""phase 3 polymorphic entity_candidates

Extends the Phase-1 ``entity_candidates`` table to cover non-person
entity kinds (party, office, committee, bill). The original
``resolved_person_id`` column is renamed to ``canonical_entity_id`` and
a new ``entity_kind`` column is added (defaulting to ``'person'`` so
pre-existing rows retain their semantics).

Also adds a composite index ``(entity_kind, canonical_entity_id)`` so
the reviewer queue can efficiently filter ambiguous candidates per
kind.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "entity_candidates",
        "resolved_person_id",
        new_column_name="canonical_entity_id",
    )
    op.add_column(
        "entity_candidates",
        sa.Column(
            "entity_kind",
            sa.Text(),
            server_default=sa.text("'person'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "entity_candidates_kind_check",
        "entity_candidates",
        "entity_kind IN ('person', 'party', 'office', 'committee', 'bill')",
    )
    op.create_index(
        "idx_entity_candidates_kind_canonical",
        "entity_candidates",
        ["entity_kind", "canonical_entity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_entity_candidates_kind_canonical",
        table_name="entity_candidates",
    )
    op.drop_constraint(
        "entity_candidates_kind_check",
        "entity_candidates",
        type_="check",
    )
    op.drop_column("entity_candidates", "entity_kind")
    op.alter_column(
        "entity_candidates",
        "canonical_entity_id",
        new_column_name="resolved_person_id",
    )
