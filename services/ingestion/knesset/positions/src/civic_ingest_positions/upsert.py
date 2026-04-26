"""Neo4j upsert for :class:`NormalizedPositionBundle`.

Every bundle fires between 1 and 5 ``run_upsert`` calls:

* 1× Person stub — safety MERGE (the people adapter may not have
  ingested this historical ``PersonID`` yet; null attributes let the
  people adapter fill them in on its next pass via ``coalesce``).
* (party-lane) 2 calls: Party stub MERGE + MEMBER_OF edge.
* (office-lane) 2 calls: Office MERGE + HELD_OFFICE edge.

All three relationship templates (``member_of.cypher``,
``held_office.cypher``) use ``MATCH`` on both endpoints; the Person/
Party/Office stubs above ensure the MATCHes succeed on first run.
"""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedPositionBundle

__all__ = ["upsert_position"]

UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

PERSON_TEMPLATE = UPSERT_ROOT / "person_upsert.cypher"
PARTY_TEMPLATE = UPSERT_ROOT / "party_upsert.cypher"
OFFICE_TEMPLATE = UPSERT_ROOT / "office_upsert.cypher"
MEMBER_OF_TEMPLATE = UPSERT_ROOT / "relationships" / "member_of.cypher"
HELD_OFFICE_TEMPLATE = UPSERT_ROOT / "relationships" / "held_office.cypher"


def upsert_position(bundle: NormalizedPositionBundle) -> dict:
    person_id_str = str(bundle.person_id)
    run_upsert(
        PERSON_TEMPLATE,
        {
            "person_id": person_id_str,
            "canonical_name": None,
            "hebrew_name": None,
            "english_name": None,
            "external_ids": None,
            "source_tier": 1,
        },
    )

    summary: dict = {
        "person_id": person_id_str,
        "person_to_position_id_external": bundle.person_to_position_id_external,
        "party_edges": 0,
        "office_edges": 0,
    }

    if bundle.party is not None:
        run_upsert(
            PARTY_TEMPLATE,
            {
                "party_id": str(bundle.party.party_id),
                "canonical_name": bundle.party.party_name,
                "hebrew_name": bundle.party.party_name,
                "english_name": None,
                "abbreviation": None,
            },
        )
        run_upsert(
            MEMBER_OF_TEMPLATE,
            {
                "person_id": person_id_str,
                "party_id": str(bundle.party.party_id),
                "valid_from": bundle.party.valid_from,
                "valid_to": bundle.party.valid_to,
            },
        )
        summary["party_edges"] = 1
        summary["party_id"] = str(bundle.party.party_id)

    if bundle.office is not None:
        run_upsert(
            OFFICE_TEMPLATE,
            {
                "office_id": str(bundle.office.office_id),
                "canonical_name": bundle.office.canonical_name,
                "office_type": bundle.office.office_type,
                "scope": bundle.office.scope,
            },
        )
        run_upsert(
            HELD_OFFICE_TEMPLATE,
            {
                "person_id": person_id_str,
                "office_id": str(bundle.office.office_id),
                "valid_from": bundle.office.valid_from,
                "valid_to": bundle.office.valid_to,
            },
        )
        summary["office_edges"] = 1
        summary["office_id"] = str(bundle.office.office_id)

    return summary
