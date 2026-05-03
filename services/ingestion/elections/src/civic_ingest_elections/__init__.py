"""V2 elections adapter — official CEC national election results.

Fetches official final national results from the Central Elections Committee
(ועדת הבחירות המרכזית) pages (votesXX.bechirot.gov.il), parses the per-list
results table, and upserts ElectionResult nodes + FOR_PARTY edges to Neo4j.

Source tier: 1 (official government authority).
"""

from __future__ import annotations

from .normalize import NormalizedElectionResult, normalize_election_result
from .parse import ParsedElectionPage, ParsedElectionRow, parse_election_page
from .party_list_mapping import get_election_date, resolve_party_id
from .upsert import upsert_election_result

__all__ = [
    "NormalizedElectionResult",
    "ParsedElectionPage",
    "ParsedElectionRow",
    "get_election_date",
    "normalize_election_result",
    "parse_election_page",
    "resolve_party_id",
    "upsert_election_result",
]
