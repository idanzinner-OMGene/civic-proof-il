"""Neo4j upsert for :class:`NormalizedElectionResult`.

Each result fires three ``run_upsert`` calls:

1. Party stub MERGE — ensures the Party node exists before the relationship
   is created. For lists that entered the Knesset the MERGE collapses onto
   the existing Party node created by the positions adapter; for below-
   threshold lists it creates a new stub node with minimal attributes.
2. ElectionResult node MERGE — keyed by ``election_result_id``.
3. FOR_PARTY edge MERGE — ``(:ElectionResult)-[:FOR_PARTY]->(:Party)``.
"""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .types import NormalizedElectionResult

__all__ = ["upsert_election_result"]

_UPSERT_ROOT = Path(__file__).resolve().parents[5] / "infra" / "neo4j" / "upserts"

_PARTY_TEMPLATE = _UPSERT_ROOT / "party_upsert.cypher"
_ELECTION_RESULT_TEMPLATE = _UPSERT_ROOT / "election_result_upsert.cypher"
_FOR_PARTY_TEMPLATE = _UPSERT_ROOT / "relationships" / "for_party.cypher"


def upsert_election_result(result: NormalizedElectionResult) -> dict:
    """Write one election list result to Neo4j.

    Returns a summary dict with the key IDs written.
    """
    party_id_str = str(result.list_party_id)
    election_result_id_str = str(result.election_result_id)

    run_upsert(
        _PARTY_TEMPLATE,
        {
            "party_id": party_id_str,
            "canonical_name": result.list_name,
            "hebrew_name": result.list_name,
            "english_name": None,
            "abbreviation": result.ballot_letters,
        },
    )

    run_upsert(
        _ELECTION_RESULT_TEMPLATE,
        {
            "election_result_id": election_result_id_str,
            "election_date": result.election_date,
            "knesset_number": result.knesset_number,
            "list_name": result.list_name,
            "ballot_letters": result.ballot_letters,
            "list_party_id": party_id_str,
            "votes": result.votes,
            "seats_won": result.seats_won,
            "vote_share": result.vote_share,
            "passed_threshold": result.passed_threshold,
            "source_document_id": None,
        },
    )

    run_upsert(
        _FOR_PARTY_TEMPLATE,
        {
            "election_result_id": election_result_id_str,
            "party_id": party_id_str,
        },
    )

    return {
        "election_result_id": election_result_id_str,
        "party_id": party_id_str,
        "ballot_letters": result.ballot_letters,
        "seats_won": result.seats_won,
        "passed_threshold": result.passed_threshold,
    }
