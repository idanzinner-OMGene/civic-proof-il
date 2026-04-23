"""Neo4j upsert for NormalizedVoteEvent bundles."""

from __future__ import annotations

from pathlib import Path

from civic_clients.neo4j import run_upsert

from .normalize import NormalizedVoteEvent

UPSERT_ROOT = Path(__file__).resolve().parents[6] / "infra" / "neo4j" / "upserts"

VOTE_EVENT_TEMPLATE = UPSERT_ROOT / "vote_event_upsert.cypher"
PERSON_TEMPLATE = UPSERT_ROOT / "person_upsert.cypher"
CAST_VOTE_TEMPLATE = UPSERT_ROOT / "relationships" / "cast_vote.cypher"


def upsert_vote(event: NormalizedVoteEvent) -> dict:
    run_upsert(
        VOTE_EVENT_TEMPLATE,
        {
            "vote_event_id": str(event.vote_event_id),
            "bill_id": str(event.bill_id) if event.bill_id else None,
            "occurred_at": event.occurred_at,
            "vote_type": event.vote_type,
        },
    )
    for cv in event.cast_votes:
        # Ensure a Person stub exists before MERGEing the edge — the votes
        # CSV (oknesset) often references MKs that the people adapter
        # hasn't yet ingested (different Knesset terms / coverage). The
        # stub carries no canonical attributes; the people adapter will
        # fill them in on its next pass via MATCH-then-SET.
        run_upsert(
            PERSON_TEMPLATE,
            {
                "person_id": str(cv.person_id),
                "canonical_name": None,
                "hebrew_name": None,
                "english_name": None,
                "external_ids": None,
                "source_tier": 2,
            },
        )
        run_upsert(
            CAST_VOTE_TEMPLATE,
            {
                "person_id": str(cv.person_id),
                "vote_event_id": str(event.vote_event_id),
                "value": cv.value,
            },
        )
    return {
        "vote_event_id": str(event.vote_event_id),
        "cast_votes": len(event.cast_votes),
    }
