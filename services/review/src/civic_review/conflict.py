"""Conflict detection → review queue (Phase 5).

When the verdict engine returns ``mixed`` and Tier-1 graph evidence is
present, enqueue a ``conflict`` task for human triage.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import psycopg
from civic_retrieval.rerank import RerankScore
from civic_verification.engine import VerdictOutcome

from .queue import open_review_task

__all__ = ["maybe_open_conflict_task", "tier1_evidence_count"]


def tier1_evidence_count(ranked: Sequence[RerankScore]) -> int:
    return sum(1 for r in ranked if getattr(r.evidence, "source_tier", 0) == 1)


def maybe_open_conflict_task(
    conn: psycopg.Connection,
    *,
    claim_id: str,
    outcome: VerdictOutcome,
    ranked: Sequence[RerankScore],
) -> UUID | None:
    """If ``outcome`` is ``mixed`` and we have at least one Tier-1 hit, open a task."""

    if outcome.status != "mixed":
        return None
    if tier1_evidence_count(ranked) < 1:
        return None
    payload: dict[str, Any] = {
        "claim_id": claim_id,
        "outcome": outcome.as_dict(),
    }
    return open_review_task(conn, kind="conflict", payload=payload, priority=10)
