"""Five-axis confidence rubric.

Reports one Confidence vector per verdict. Axes map 1:1 to the
``Confidence`` contract in ``civic_ontology.models.common``:

* source_authority          — weighted by top-ranked evidence tier
* directness                — best directness score across evidence
* temporal_alignment        — best temporal score across evidence
* entity_resolution         — best entity score across evidence
* cross_source_consistency  — best cross-source score across evidence

``overall`` is computed as a weighted mean using the SAME weights the
reranker used, so downstream consumers can trust a single source of
truth for axis importance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from civic_ontology.models.common import Confidence
from civic_retrieval.rerank import WEIGHTS, RerankScore

__all__ = ["FiveAxisRubric", "compute_confidence"]


@dataclass(frozen=True, slots=True)
class FiveAxisRubric:
    source_authority: float
    directness: float
    temporal_alignment: float
    entity_resolution: float
    cross_source_consistency: float

    def as_confidence(self) -> Confidence:
        return Confidence(
            source_authority=self.source_authority,
            directness=self.directness,
            temporal_alignment=self.temporal_alignment,
            entity_resolution=self.entity_resolution,
            cross_source_consistency=self.cross_source_consistency,
            overall=round(
                WEIGHTS["source_tier"] * self.source_authority
                + WEIGHTS["directness"] * self.directness
                + WEIGHTS["temporal_alignment"] * self.temporal_alignment
                + WEIGHTS["entity_resolution"] * self.entity_resolution
                + WEIGHTS["cross_source_consistency"] * self.cross_source_consistency,
                4,
            ),
        )


def compute_confidence(ranked: Iterable[RerankScore]) -> Confidence:
    """Compute a :class:`Confidence` vector from a ranked evidence list.

    ``source_authority`` is taken from the HIGHEST source_tier score
    (which corresponds to the LOWEST tier number via
    :func:`_source_tier_score`). The other four axes take the MAX
    across evidence. Empty input returns an all-zero rubric.
    """

    best: dict[str, float] = {
        "source_tier": 0.0,
        "directness": 0.0,
        "temporal_alignment": 0.0,
        "entity_resolution": 0.0,
        "cross_source_consistency": 0.0,
    }
    for s in ranked:
        best["source_tier"] = max(best["source_tier"], s.source_tier)
        best["directness"] = max(best["directness"], s.directness)
        best["temporal_alignment"] = max(best["temporal_alignment"], s.temporal_alignment)
        best["entity_resolution"] = max(best["entity_resolution"], s.entity_resolution)
        best["cross_source_consistency"] = max(
            best["cross_source_consistency"], s.cross_source_consistency
        )
    rubric = FiveAxisRubric(
        source_authority=best["source_tier"],
        directness=best["directness"],
        temporal_alignment=best["temporal_alignment"],
        entity_resolution=best["entity_resolution"],
        cross_source_consistency=best["cross_source_consistency"],
    )
    return rubric.as_confidence()
