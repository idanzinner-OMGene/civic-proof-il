"""Neo4j upsert for NormalizedCommittee bundles."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedCommittee

UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

COMMITTEE_TEMPLATE = UPSERT_ROOT / "committee_upsert.cypher"
MEMBERSHIP_TERM_TEMPLATE = UPSERT_ROOT / "membership_term_upsert.cypher"
MEMBER_OF_COMMITTEE_TEMPLATE = (
    UPSERT_ROOT / "relationships" / "member_of_committee.cypher"
)


def upsert_committee(committee: NormalizedCommittee) -> dict:
    run_upsert(
        COMMITTEE_TEMPLATE,
        {
            "committee_id": str(committee.committee_id),
            "canonical_name": committee.canonical_name,
            "hebrew_name": committee.hebrew_name,
        },
    )

    for m in committee.memberships:
        valid_from = m.valid_from or datetime.now(tz=timezone.utc).isoformat()
        run_upsert(
            MEMBERSHIP_TERM_TEMPLATE,
            {
                "membership_term_id": str(m.membership_term_id),
                "person_id": str(m.person_id),
                "org_id": str(m.committee_id),
                "org_type": "committee",
                "valid_from": valid_from,
                "valid_to": m.valid_to,
            },
        )
        run_upsert(
            MEMBER_OF_COMMITTEE_TEMPLATE,
            {
                "person_id": str(m.person_id),
                "committee_id": str(m.committee_id),
                "valid_from": valid_from,
                "valid_to": m.valid_to,
            },
        )

    return {
        "committee_id": str(committee.committee_id),
        "memberships": len(committee.memberships),
    }
