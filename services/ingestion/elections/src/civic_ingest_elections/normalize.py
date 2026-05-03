"""Normalize parsed CEC election rows → :class:`NormalizedElectionResult`.

Responsibilities:

- Compute deterministic ``election_result_id`` via
  ``uuid5(NS, "cec_election:{knesset}:{ballot_letters}")``.
- Resolve ``list_party_id`` via the curated party/list mapping so that lists
  that entered the Knesset map to the same ``Party`` node as the positions
  adapter.
- Compute ``passed_threshold`` from the list's votes vs. the official
  3.25% threshold applied to the page's total valid votes.
- Parse ``vote_share`` float from the percentage string on the page.
"""

from __future__ import annotations

import math
import uuid
from typing import Iterable

from .party_list_mapping import THRESHOLD_RULE, resolve_party_id
from .types import PHASE2_UUID_NAMESPACE, NormalizedElectionResult, ParsedElectionPage, ParsedElectionRow

__all__ = ["normalize_election_result", "normalize_page"]


def normalize_election_result(
    row: ParsedElectionRow,
    page: ParsedElectionPage,
) -> Iterable[NormalizedElectionResult]:
    """Yield one :class:`NormalizedElectionResult` for ``row``.

    Returns an empty iterable if ``ballot_letters`` is empty (structurally
    broken upstream row).
    """
    if not row.ballot_letters:
        return

    knesset_number = page.knesset_number
    ballot_letters = row.ballot_letters

    election_result_id = uuid.uuid5(
        PHASE2_UUID_NAMESPACE,
        f"cec_election:{knesset_number}:{ballot_letters}",
    )

    list_party_id = resolve_party_id(knesset_number, ballot_letters)

    vote_share = _parse_vote_share(row.vote_share_pct)

    threshold_votes = math.ceil(page.total_valid_votes * THRESHOLD_RULE)
    passed_threshold = row.votes >= threshold_votes

    yield NormalizedElectionResult(
        election_result_id=election_result_id,
        knesset_number=knesset_number,
        election_date=page.election_date,
        list_party_id=list_party_id,
        list_name=row.list_name,
        ballot_letters=ballot_letters,
        votes=row.votes,
        seats_won=row.seats_won,
        vote_share=vote_share,
        passed_threshold=passed_threshold,
    )


def normalize_page(page: ParsedElectionPage) -> Iterable[NormalizedElectionResult]:
    """Yield one :class:`NormalizedElectionResult` per row in ``page``."""
    for row in page.rows:
        yield from normalize_election_result(row, page)


def _parse_vote_share(pct_str: str) -> float:
    """Convert a percentage string like ``"23.41%"`` to ``0.2341``."""
    try:
        return round(float(pct_str.rstrip('%')) / 100.0, 6)
    except ValueError:
        return 0.0
