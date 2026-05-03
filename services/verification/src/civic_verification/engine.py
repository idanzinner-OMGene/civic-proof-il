"""Deterministic verdict engine + abstention policy.

Inputs:

* the decomposed / resolved claim (claim_type, resolved slots, time_scope),
* the reranked evidence list (from :mod:`civic_retrieval.rerank`),
* the checkability string set by the decomposer.

Outputs a :class:`VerdictOutcome` with:

* ``status`` — supported | contradicted | mixed | insufficient_evidence
  | non_checkable.
* ``confidence`` — the Confidence vector from the rubric.
* ``needs_human_review`` — true when the abstention policy triggers.
* ``reasons`` — a structured decision trace the reviewer UI renders.

No LLM is involved. The only LLM seam in verification is the
uncertainty-note bundler (:mod:`civic_verification.provenance`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from civic_ontology.models.common import Confidence
from civic_retrieval.graph import GraphEvidence
from civic_retrieval.lexical import LexicalEvidence
from civic_retrieval.rerank import RerankScore

from .confidence import compute_confidence

__all__ = ["VerdictInputs", "VerdictOutcome", "decide_verdict"]


@dataclass(frozen=True, slots=True)
class VerdictInputs:
    claim_id: str
    claim_type: str
    checkability: str
    ranked_evidence: Sequence[RerankScore] = field(default_factory=tuple)
    expected_vote_value: str | None = None  # only for vote_cast
    expected_seats: int | None = None  # election_result
    expect_passed_threshold: bool | None = None  # election_result
    claim_time_scope: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class VerdictOutcome:
    status: str
    confidence: Confidence
    needs_human_review: bool
    reasons: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "confidence": self.confidence.model_dump(),
            "needs_human_review": self.needs_human_review,
            "reasons": list(self.reasons),
        }


# Plan: abstain to "insufficient_evidence" + needs_human_review when:
#  * overall confidence is below ABSTAIN_OVERALL, OR
#  * zero evidence items matched the claim_type graph template AND
#    fewer than MIN_CROSS_SOURCE distinct documents are cited.
ABSTAIN_OVERALL: float = 0.45
MIN_CROSS_SOURCE: int = 1
HUMAN_REVIEW_OVERALL: float = 0.62


def _zero_confidence() -> Confidence:
    return Confidence(
        source_authority=0.0,
        directness=0.0,
        temporal_alignment=0.0,
        entity_resolution=0.0,
        cross_source_consistency=0.0,
        overall=0.0,
    )


def decide_verdict(inputs: VerdictInputs) -> VerdictOutcome:
    reasons: list[dict[str, Any]] = []

    if inputs.checkability != "checkable":
        return VerdictOutcome(
            status="non_checkable",
            confidence=_zero_confidence(),
            needs_human_review=inputs.checkability
            in ("insufficient_entity_resolution",),
            reasons=(
                {"kind": "abstain", "reason": "checkability", "detail": inputs.checkability},
            ),
        )

    ranked = list(inputs.ranked_evidence)
    if not ranked:
        return VerdictOutcome(
            status="insufficient_evidence",
            confidence=_zero_confidence(),
            needs_human_review=True,
            reasons=(
                {"kind": "abstain", "reason": "no_evidence"},
            ),
        )

    confidence = compute_confidence(ranked)

    if confidence.overall < ABSTAIN_OVERALL:
        reasons.append(
            {"kind": "abstain", "reason": "low_confidence", "overall": confidence.overall}
        )
        return VerdictOutcome(
            status="insufficient_evidence",
            confidence=confidence,
            needs_human_review=True,
            reasons=tuple(reasons),
        )

    graph_hits = [
        r for r in ranked
        if isinstance(r.evidence, GraphEvidence) and r.evidence.claim_type == inputs.claim_type
    ]

    status = _compare(inputs, graph_hits, ranked, reasons)

    tier1_graph = any(
        isinstance(r.evidence, GraphEvidence) and r.evidence.source_tier == 1
        for r in graph_hits
    )
    needs_review = confidence.overall < HUMAN_REVIEW_OVERALL or status == "mixed"
    # Official Tier-1 graph rows should drive contradiction review; Tier-2/3 alone is risky.
    if status == "contradicted" and graph_hits and not tier1_graph:
        needs_review = True
    return VerdictOutcome(
        status=status,
        confidence=confidence,
        needs_human_review=needs_review,
        reasons=tuple(reasons),
    )


def _compare(
    inputs: VerdictInputs,
    graph_hits: list[RerankScore],
    ranked: list[RerankScore],
    reasons: list[dict[str, Any]],
) -> str:
    claim_type = inputs.claim_type

    if claim_type == "vote_cast":
        return _vote_cast(inputs, graph_hits, ranked, reasons)

    if claim_type == "election_result":
        return _election_result(inputs, graph_hits, reasons)

    if claim_type in {"bill_sponsorship", "office_held", "committee_membership"}:
        if graph_hits:
            reasons.append(
                {"kind": "support", "source": "graph", "count": len(graph_hits)}
            )
            return "supported"
        lex_hits = _lex_corroborations(ranked)
        if lex_hits:
            reasons.append({"kind": "support", "source": "lexical", "count": lex_hits})
            return "supported"
        reasons.append({"kind": "abstain", "reason": "no_graph_or_lex_support"})
        return "insufficient_evidence"

    if claim_type == "committee_attendance":
        if not graph_hits:
            reasons.append({"kind": "abstain", "reason": "no_attendance_graph_hit"})
            return "insufficient_evidence"
        present = [g for g in graph_hits if g.evidence.properties.get("presence") == "present"]
        if present:
            reasons.append({"kind": "support", "count": len(present)})
            return "supported"
        reasons.append({"kind": "contradict", "reason": "only_absent_sessions"})
        return "contradicted"

    # statement_about_formal_action: rely on corroboration + cross-source
    if _lex_corroborations(ranked) >= 2:
        reasons.append({"kind": "support", "source": "lexical_multi"})
        return "supported"
    if _lex_corroborations(ranked) == 1:
        reasons.append({"kind": "mixed", "source": "lexical_single"})
        return "mixed"
    reasons.append({"kind": "abstain", "reason": "no_corroboration"})
    return "insufficient_evidence"


def _election_result(
    inputs: VerdictInputs,
    graph_hits: list[RerankScore],
    reasons: list[dict[str, Any]],
) -> str:
    if not graph_hits:
        reasons.append({"kind": "abstain", "reason": "no_election_graph_hit"})
        return "insufficient_evidence"

    expect_seats = inputs.expected_seats
    expect_passed = inputs.expect_passed_threshold

    for r in graph_hits:
        if not isinstance(r.evidence, GraphEvidence):
            continue
        props = r.evidence.properties
        seats = props.get("seats_won")
        passed = props.get("passed_threshold")

        seats_ok = True
        if expect_seats is not None:
            try:
                seats_ok = int(seats) == int(expect_seats)
            except (TypeError, ValueError):
                seats_ok = False

        passed_ok = True
        if expect_passed is not None:
            if passed is None:
                passed_ok = False
            else:
                passed_ok = bool(passed) == bool(expect_passed)

        if seats_ok and passed_ok:
            reasons.append(
                {
                    "kind": "support",
                    "source": "graph",
                    "seats_won": seats,
                    "passed_threshold": passed,
                }
            )
            return "supported"

    reasons.append(
        {
            "kind": "contradict",
            "expected_seats": expect_seats,
            "expect_passed_threshold": expect_passed,
            "observed": [
                {
                    "seats_won": g.evidence.properties.get("seats_won"),
                    "passed_threshold": g.evidence.properties.get("passed_threshold"),
                    "knesset_number": g.evidence.properties.get("knesset_number"),
                }
                for g in graph_hits
                if isinstance(g.evidence, GraphEvidence)
            ],
        }
    )
    return "contradicted"


def _lex_corroborations(ranked: list[RerankScore]) -> int:
    return sum(1 for r in ranked if isinstance(r.evidence, LexicalEvidence))


def _vote_cast(
    inputs: VerdictInputs,
    graph_hits: list[RerankScore],
    ranked: list[RerankScore],
    reasons: list[dict[str, Any]],
) -> str:
    if not graph_hits:
        reasons.append({"kind": "abstain", "reason": "no_graph_vote_record"})
        return "insufficient_evidence"
    recorded_values = {
        r.evidence.properties.get("vote_value")
        for r in graph_hits
        if isinstance(r.evidence, GraphEvidence)
    }
    expected = inputs.expected_vote_value
    if expected is None:
        reasons.append({"kind": "support", "reason": "any_vote_recorded"})
        return "supported"
    if recorded_values == {expected}:
        reasons.append({"kind": "support", "detail": f"matches {expected}"})
        return "supported"
    if expected in recorded_values and len(recorded_values) > 1:
        reasons.append({"kind": "mixed", "detail": list(recorded_values)})
        return "mixed"
    reasons.append(
        {"kind": "contradict", "expected": expected, "observed": sorted(filter(None, recorded_values))}
    )
    return "contradicted"
