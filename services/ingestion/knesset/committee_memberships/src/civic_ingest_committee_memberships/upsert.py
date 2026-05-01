"""Neo4j upsert for :class:`NormalizedCommitteeMembership`.

Three ``run_upsert`` calls per membership:

1. Person stub MERGE — the people adapter may not have ingested this
   historical ``PersonID`` yet.
2. Committee stub MERGE — committee-name from the oknesset CSV is
   lower-tier than the committees adapter's canonical source, so we
   pass ``canonical_name=None`` and let ``coalesce`` preserve the
   Tier-1 data when it arrives.
3. MEMBER_OF_COMMITTEE edge MERGE.
"""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedCommitteeMembership

__all__ = ["upsert_committee_membership"]

UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

PERSON_TEMPLATE = UPSERT_ROOT / "person_upsert.cypher"
COMMITTEE_TEMPLATE = UPSERT_ROOT / "committee_upsert.cypher"
MEMBER_OF_COMMITTEE_TEMPLATE = (
    UPSERT_ROOT / "relationships" / "member_of_committee.cypher"
)


def upsert_committee_membership(
    membership: NormalizedCommitteeMembership,
) -> dict:
    person_id_str = str(membership.person_id)
    committee_id_str = str(membership.committee_id)

    run_upsert(
        PERSON_TEMPLATE,
        {
            "person_id": person_id_str,
            "canonical_name": None,
            "hebrew_name": None,
            "english_name": None,
            "external_ids": None,
            "source_tier": 2,
        },
    )
    run_upsert(
        COMMITTEE_TEMPLATE,
        {
            "committee_id": committee_id_str,
            "canonical_name": None,
            "hebrew_name": membership.committee_name,
            "english_name": None,
        },
    )
    run_upsert(
        MEMBER_OF_COMMITTEE_TEMPLATE,
        {
            "person_id": person_id_str,
            "committee_id": committee_id_str,
            "valid_from": membership.valid_from,
            "valid_to": membership.valid_to,
        },
    )
    return {
        "person_id": person_id_str,
        "committee_id": committee_id_str,
        "mk_individual_id": membership.mk_individual_id,
        "knesset": membership.knesset,
    }
