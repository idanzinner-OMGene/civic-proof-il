"""V2 Stage B — relation judgment between a declaration-aligned claim and formal records.

Maps v1 verdict outcomes and checkability signals to :class:`RelationType` values used
on :class:`~civic_ontology.models.attribution.AttributionEdge` edges.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from civic_ontology.models.attribution import ConfidenceBand, RelationType

_VERDICT_TO_RELATION: dict[str, RelationType] = {
    "supported": "supported_by",
    "contradicted": "contradicted_by",
    "mixed": "overstates",
    "insufficient_evidence": "not_checkable_against_record",
    "non_checkable": "not_checkable_against_record",
}

CONFIDENCE_BAND_THRESHOLDS = {"high": 0.8, "medium": 0.6, "low": 0.45}

RELATION_PRIORITY: tuple[RelationType, ...] = (
    "contradicted_by",
    "entity_ambiguous",
    "time_scope_mismatch",
    "not_checkable_against_record",
    "overstates",
    "underspecifies",
    "supported_by",
)


def determine_relation(
    *,
    verdict_status: str,
    checkability: str,
    reasons: Sequence[Mapping[str, Any]],
    lexical_hits: int,
) -> RelationType:
    """Map a v1 verdict status (with refinements) to a V2 :class:`RelationType`."""

    base = _VERDICT_TO_RELATION.get(verdict_status, "not_checkable_against_record")
    if verdict_status == "non_checkable":
        if checkability == "insufficient_entity_resolution":
            return "entity_ambiguous"
        if checkability == "insufficient_time_scope":
            return "time_scope_mismatch"
    if verdict_status == "contradicted":
        for reason in reasons:
            r = reason.get("reason")
            if isinstance(r, str) and "time_scope" in r:
                return "time_scope_mismatch"
    if verdict_status == "mixed" and lexical_hits == 1:
        return "underspecifies"
    return base


def determine_confidence_band(overall: float) -> ConfidenceBand:
    """Bucket a numeric overall confidence into a discrete :class:`ConfidenceBand`."""

    if overall >= CONFIDENCE_BAND_THRESHOLDS["high"]:
        return "high"
    if overall >= CONFIDENCE_BAND_THRESHOLDS["medium"]:
        return "medium"
    if overall >= CONFIDENCE_BAND_THRESHOLDS["low"]:
        return "low"
    return "uncertain"


def worst_relation(relations: Iterable[RelationType]) -> RelationType:
    """Pick the worst present relation using :data:`RELATION_PRIORITY` (index 0 = worst)."""

    rels = list(relations)
    if not rels:
        return "not_checkable_against_record"
    best_idx: int | None = None
    chosen: RelationType | None = None
    for r in rels:
        try:
            idx = RELATION_PRIORITY.index(r)
        except ValueError:
            continue
        if best_idx is None or idx < best_idx:
            best_idx = idx
            chosen = r
    return chosen if chosen is not None else "not_checkable_against_record"
