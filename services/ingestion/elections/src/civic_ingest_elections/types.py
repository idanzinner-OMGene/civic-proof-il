"""Interface dataclasses shared across parse / normalize / upsert layers.

Defining them here (rather than in parse.py or normalize.py) breaks the
dependency cycle so all three modules can be developed and tested
independently against the same contract.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

__all__ = [
    "PHASE2_UUID_NAMESPACE",
    "ParsedElectionPage",
    "ParsedElectionRow",
    "NormalizedElectionResult",
]

PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


@dataclass(frozen=True, slots=True)
class ParsedElectionRow:
    """One list's result row from the CEC national results page."""

    list_name: str
    ballot_letters: str
    seats_won: int
    vote_share_pct: str
    votes: int


@dataclass(frozen=True, slots=True)
class ParsedElectionPage:
    """Full national results page for one election."""

    knesset_number: int
    election_date: str
    total_valid_votes: int
    total_votes_cast: int
    total_invalid_votes: int
    eligible_voters: int
    rows: list[ParsedElectionRow] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class NormalizedElectionResult:
    """Normalized record ready for Neo4j upsert — one per list per election."""

    election_result_id: uuid.UUID
    knesset_number: int
    election_date: str
    list_party_id: uuid.UUID
    list_name: str
    ballot_letters: str
    votes: int
    seats_won: int
    vote_share: float
    passed_threshold: bool
