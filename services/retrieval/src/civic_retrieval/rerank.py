"""Deterministic reranker.

Combines the five signals called out in plan lines 390-402:

1. ``source_tier`` (1 > 2 > 3).
2. ``directness`` — how close the evidence is to the claim (graph
   evidence hitting the exact vote event is maximally direct; lexical
   evidence mentioning the MK but not the bill is low directness).
3. ``temporal_alignment`` — overlap between claim time scope and
   evidence time metadata.
4. ``entity_resolution`` — how confident we were that the entities on
   the evidence record point at the same entity the claim resolved to.
5. ``cross_source_consistency`` — whether multiple independent
   documents corroborate the same fact.

No learned weights; all weights live in :data:`WEIGHTS` and can be
audited / tuned without a deploy. Output is sorted by ``overall``
score descending and is guaranteed deterministic for a fixed input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Union

from .graph import GraphEvidence
from .lexical import LexicalEvidence

__all__ = ["Evidence", "RerankScore", "WEIGHTS", "rerank"]


Evidence = Union[GraphEvidence, LexicalEvidence]


WEIGHTS: Mapping[str, float] = {
    "source_tier": 0.30,
    "directness": 0.25,
    "temporal_alignment": 0.20,
    "entity_resolution": 0.15,
    "cross_source_consistency": 0.10,
}


@dataclass(frozen=True, slots=True)
class RerankScore:
    source_tier: float
    directness: float
    temporal_alignment: float
    entity_resolution: float
    cross_source_consistency: float
    overall: float
    evidence: Evidence

    def as_dict(self) -> dict[str, float]:
        return {
            "source_tier": self.source_tier,
            "directness": self.directness,
            "temporal_alignment": self.temporal_alignment,
            "entity_resolution": self.entity_resolution,
            "cross_source_consistency": self.cross_source_consistency,
            "overall": self.overall,
        }


def _source_tier_score(tier: int) -> float:
    return {1: 1.0, 2: 0.6, 3: 0.3}.get(tier, 0.1)


def _directness_score(e: Evidence, claim_type: str) -> float:
    if isinstance(e, GraphEvidence):
        if e.claim_type == claim_type:
            return 1.0
        return 0.6
    text = (e.text or "").strip()
    if not text:
        return 0.0
    if len(text) < 160:
        return 0.75
    return 0.5


def _temporal_score(
    e: Evidence,
    claim_time_scope: Mapping[str, str | None] | None,
) -> float:
    if not claim_time_scope:
        return 0.5
    start = claim_time_scope.get("start")
    end = claim_time_scope.get("end")
    if isinstance(e, GraphEvidence):
        occurred = str(e.properties.get("occurred_at") or "")
        if not occurred:
            return 0.6
        if start and occurred < start:
            return 0.2
        if end and occurred > end:
            return 0.2
        return 1.0
    captured = str((e.properties or {}).get("captured_at") or "")
    if not captured:
        return 0.5
    if start and captured < start:
        return 0.4
    if end and captured > end:
        return 0.4
    return 0.8


def _entity_score(e: Evidence, resolved_ids: Mapping[str, str] | None) -> float:
    if not resolved_ids:
        return 0.5
    if isinstance(e, GraphEvidence):
        hits = sum(
            1 for slot, value in resolved_ids.items()
            if e.node_ids.get(slot) == value
        )
        if hits == 0:
            return 0.2
        return min(1.0, 0.5 + 0.25 * hits)
    return 0.6


def _cross_source_score(e: Evidence, cross_source_count: int) -> float:
    if cross_source_count <= 1:
        return 0.3
    if cross_source_count == 2:
        return 0.7
    return 1.0


def rerank(
    evidences: Iterable[Evidence],
    *,
    claim_type: str,
    claim_time_scope: Mapping[str, str | None] | None = None,
    resolved_ids: Mapping[str, str] | None = None,
) -> list[RerankScore]:
    materialized = list(evidences)
    distinct_docs: set[str] = set()
    for e in materialized:
        if isinstance(e, GraphEvidence):
            distinct_docs.update(e.source_document_ids)
        else:
            if e.document_id:
                distinct_docs.add(e.document_id)
    cross = len(distinct_docs)

    scored: list[RerankScore] = []
    for e in materialized:
        tier = e.source_tier if isinstance(e, LexicalEvidence) else e.source_tier
        parts = {
            "source_tier": _source_tier_score(tier),
            "directness": _directness_score(e, claim_type),
            "temporal_alignment": _temporal_score(e, claim_time_scope),
            "entity_resolution": _entity_score(e, resolved_ids),
            "cross_source_consistency": _cross_source_score(e, cross),
        }
        overall = sum(WEIGHTS[k] * v for k, v in parts.items())
        scored.append(
            RerankScore(
                source_tier=parts["source_tier"],
                directness=parts["directness"],
                temporal_alignment=parts["temporal_alignment"],
                entity_resolution=parts["entity_resolution"],
                cross_source_consistency=parts["cross_source_consistency"],
                overall=round(overall, 4),
                evidence=e,
            )
        )
    scored.sort(key=lambda s: (-s.overall, _stable_key(s.evidence)))
    return scored


def _stable_key(e: Evidence) -> str:
    if isinstance(e, GraphEvidence):
        return "g:" + ":".join(sorted(e.node_ids.values()))
    return "l:" + e.span_id
