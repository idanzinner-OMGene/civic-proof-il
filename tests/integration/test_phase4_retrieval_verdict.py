"""Phase-4 integration test — rerank → verdict → provenance bundle.

Hermetic: assembles evidence records in memory and exercises the
reranker + verdict engine + bundler.
"""

from __future__ import annotations

from civic_retrieval import GraphEvidence, LexicalEvidence, rerank
from civic_verification import (
    VerdictInputs,
    bundle_provenance,
    decide_verdict,
)


def _graph(vote_value: str | None = None, tier: int = 1):
    props = {"vote_value": vote_value} if vote_value else {}
    props["occurred_at"] = "2024-06-01T00:00:00Z"
    return GraphEvidence(
        claim_type="vote_cast",
        node_ids={"speaker_person_id": "P"},
        properties=props,
        source_document_ids=("d",),
        source_tier=tier,
    )


def test_supported_vote_cast_generates_review_skip_when_confident() -> None:
    ranked = rerank([_graph(vote_value="for")], claim_type="vote_cast")
    outcome = decide_verdict(
        VerdictInputs(
            claim_id="C",
            claim_type="vote_cast",
            checkability="checkable",
            ranked_evidence=ranked,
            expected_vote_value="for",
        )
    )
    assert outcome.status == "supported"
    bundle = bundle_provenance(outcome, ranked, claim_id="C", claim_type="vote_cast")
    assert bundle.verdict["status"] == "supported"
    assert len(bundle.top_evidence) == 1


def test_contradicted_vote_cast_marks_for_review_when_low_confidence() -> None:
    ranked = rerank([_graph(vote_value="against", tier=3)], claim_type="vote_cast")
    outcome = decide_verdict(
        VerdictInputs(
            claim_id="C",
            claim_type="vote_cast",
            checkability="checkable",
            ranked_evidence=ranked,
            expected_vote_value="for",
        )
    )
    assert outcome.status in {"contradicted", "insufficient_evidence"}
    if outcome.status == "contradicted":
        # lower tier => lower confidence => reviewer flag
        assert outcome.needs_human_review


def test_non_checkable_claim_short_circuits() -> None:
    ranked = rerank([LexicalEvidence("s", "d", "t", 1, 1.0)], claim_type="vote_cast")
    outcome = decide_verdict(
        VerdictInputs(
            claim_id="C",
            claim_type="vote_cast",
            checkability="insufficient_time_scope",
            ranked_evidence=ranked,
        )
    )
    assert outcome.status == "non_checkable"
    assert outcome.confidence.overall == 0.0
