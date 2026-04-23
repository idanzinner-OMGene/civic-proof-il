"""Phase-2 plenum vote adapter.

Reads ``KNS_Vote`` + ``KNS_VoteDetails``; normalizes into
:class:`NormalizedVoteEvent` bundles carrying the VoteEvent node and
its per-person ``CAST_VOTE`` relationships.
"""

from __future__ import annotations

from .normalize import NormalizedCastVote, NormalizedVoteEvent, normalize_vote
from .parse import parse_votes
from .upsert import upsert_vote

__all__ = [
    "NormalizedCastVote",
    "NormalizedVoteEvent",
    "normalize_vote",
    "parse_votes",
    "upsert_vote",
]
