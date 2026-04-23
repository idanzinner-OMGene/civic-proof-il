"""Neo4j upsert for NormalizedPerson → Person/Party/Office + rels."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedPerson

__all__ = ["UPSERT_ROOT", "upsert_person"]


UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

PERSON_TEMPLATE = UPSERT_ROOT / "person_upsert.cypher"
PARTY_TEMPLATE = UPSERT_ROOT / "party_upsert.cypher"
OFFICE_TEMPLATE = UPSERT_ROOT / "office_upsert.cypher"
MEMBER_OF_TEMPLATE = UPSERT_ROOT / "relationships" / "member_of.cypher"
HELD_OFFICE_TEMPLATE = UPSERT_ROOT / "relationships" / "held_office.cypher"


def upsert_person(person: NormalizedPerson) -> dict:
    """Idempotently write a :class:`NormalizedPerson` to Neo4j.

    Returns a summary dict for logging / tests.
    """

    summary: dict = {"person_id": str(person.person_id)}

    run_upsert(
        PERSON_TEMPLATE,
        {
            "person_id": str(person.person_id),
            "canonical_name": person.canonical_name,
            "hebrew_name": person.hebrew_name,
            "english_name": None,
            "external_ids": json.dumps(person.external_ids, ensure_ascii=False),
            "source_tier": 1,
        },
    )

    if person.party is not None:
        run_upsert(
            PARTY_TEMPLATE,
            {
                "party_id": str(person.party.party_id),
                "canonical_name": person.party.canonical_name,
                "hebrew_name": person.party.hebrew_name,
                "english_name": None,
                "abbreviation": None,
            },
        )
        run_upsert(
            MEMBER_OF_TEMPLATE,
            {
                "person_id": str(person.person_id),
                "party_id": str(person.party.party_id),
                "valid_from": datetime.now(tz=timezone.utc).isoformat(),
                "valid_to": None,
            },
        )
        summary["party_id"] = str(person.party.party_id)

    if person.office is not None:
        run_upsert(
            OFFICE_TEMPLATE,
            {
                "office_id": str(person.office.office_id),
                "canonical_name": person.office.canonical_name,
                "office_type": person.office.office_type,
                "scope": person.office.scope,
            },
        )
        run_upsert(
            HELD_OFFICE_TEMPLATE,
            {
                "person_id": str(person.person_id),
                "office_id": str(person.office.office_id),
                "valid_from": datetime.now(tz=timezone.utc).isoformat(),
                "valid_to": None,
            },
        )
        summary["office_id"] = str(person.office.office_id)

    return summary
