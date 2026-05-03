"""Neo4j upsert for :class:`NormalizedPositionBundle`.

Every bundle fires between 1 and 8 ``run_upsert`` calls:

* 1× Person stub — safety MERGE (the people adapter may not have
  ingested this historical ``PersonID`` yet; null attributes let the
  people adapter fill them in on its next pass via ``coalesce``).
* (party-lane) 2 calls: Party stub MERGE + MEMBER_OF edge.
* (office-lane) 2 calls: Office MERGE + HELD_OFFICE edge (legacy v1 path).
* (position-term-lane) 3 calls: PositionTerm MERGE + HAS_POSITION_TERM
  edge + ABOUT_OFFICE edge (V2 first-class time-bounded node path).

Both the legacy ``HELD_OFFICE`` edge and the new ``PositionTerm`` path
coexist in the graph.  Retrieval uses the PositionTerm path for richer
metadata (``appointing_body``, ``is_acting``, source provenance).

All relationship templates use ``MATCH`` on both endpoints; the stub
MERGEs above ensure the MATCHes succeed on first run.
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
POSITION_TERM_TEMPLATE = UPSERT_ROOT / "position_term_upsert.cypher"
MEMBER_OF_TEMPLATE = UPSERT_ROOT / "relationships" / "member_of.cypher"
HELD_OFFICE_TEMPLATE = UPSERT_ROOT / "relationships" / "held_office.cypher"
HAS_POSITION_TERM_TEMPLATE = UPSERT_ROOT / "relationships" / "has_position_term.cypher"
ABOUT_OFFICE_TEMPLATE = UPSERT_ROOT / "relationships" / "about_office.cypher"


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
                "hebrew_name": bundle.office.canonical_name,
                "english_name": None,
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

    if bundle.position_term is not None:
        pt = bundle.position_term
        position_term_id_str = str(pt.position_term_id)
        run_upsert(
            POSITION_TERM_TEMPLATE,
            {
                "position_term_id": position_term_id_str,
                "person_id": str(pt.person_id),
                "office_id": str(pt.office_id),
                "appointing_body": pt.appointing_body,
                "valid_from": pt.valid_from,
                "valid_to": pt.valid_to,
                "is_acting": pt.is_acting,
                "source_document_id": None,
            },
        )
        run_upsert(
            HAS_POSITION_TERM_TEMPLATE,
            {
                "person_id": person_id_str,
                "position_term_id": position_term_id_str,
            },
        )
        run_upsert(
            ABOUT_OFFICE_TEMPLATE,
            {
                "position_term_id": position_term_id_str,
                "office_id": str(pt.office_id),
            },
        )
        summary["position_term_id"] = position_term_id_str

    return summary
