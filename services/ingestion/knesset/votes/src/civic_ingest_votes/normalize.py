"""Normalize a per-MK vote row → VoteEvent + one CAST_VOTE bundle.

The upstream CSV (``vote_rslts_kmmbr_shadow.csv``) lists one row
per ``(vote_id, kmmbr_id, vote_result)``. Each row is emitted as a
``NormalizedVoteEvent`` with exactly one ``NormalizedCastVote``. The
upsert step ``MERGE`` s the ``VoteEvent`` node by ``vote_event_id``
(so repeated rows collapse onto one node) and adds one CAST_VOTE edge
per (person, vote_event) pair — the edge's existence is idempotent
via a ``MERGE`` keyed on both endpoints plus the vote value.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterable

PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


# Canonical Knesset `vote_result` integer codes (validated against the
# recorded real cassette first row: value 1 = "for" for MK בנימין אלון).
# 0 = absent/no-show; we drop those from CAST_VOTE edges.
_KNS_VOTE_RESULT = {
    1: "for",
    2: "against",
    3: "abstain",
}


@dataclass(frozen=True, slots=True)
class NormalizedCastVote:
    person_id: uuid.UUID
    value: str


@dataclass(frozen=True, slots=True)
class NormalizedVoteEvent:
    vote_event_id: uuid.UUID
    bill_id: uuid.UUID | None
    occurred_at: str | None
    vote_type: str | None
    knesset_number: int | None = None
    cast_votes: tuple[NormalizedCastVote, ...] = field(default=())


def normalize_vote(row: dict) -> Iterable[NormalizedVoteEvent]:
    """Produce one ``VoteEvent`` with a single cast vote for the row.

    Unknown ``vote_result`` codes (0, 4+) yield a bare VoteEvent with
    no cast_votes so the MERGE still creates / confirms the node even
    when the MK was absent.
    """

    ext = row["vote_id_external"]
    raw = row.get("vote_result")
    mapped = _KNS_VOTE_RESULT.get(raw)

    cast_votes: tuple[NormalizedCastVote, ...] = ()
    if mapped is not None and row.get("person_id_external"):
        cast_votes = (
            NormalizedCastVote(
                person_id=_ext_uuid(
                    "knesset_person", str(row["person_id_external"])
                ),
                value=mapped,
            ),
        )

    yield NormalizedVoteEvent(
        vote_event_id=_ext_uuid("knesset_vote", ext),
        bill_id=None,  # vote→bill join comes from a future adapter pass
        occurred_at=None,  # header table holds the timestamp; this feed doesn't
        vote_type=None,
        knesset_number=row.get("knesset_number"),
        cast_votes=cast_votes,
    )
