"""Tests for the deterministic verdict engine + five-axis rubric."""

from __future__ import annotations

from civic_retrieval import GraphEvidence, LexicalEvidence, rerank
from civic_verification import (
    UncertaintyBundler,
    VerdictInputs,
    bundle_provenance,
    decide_verdict,
)


def _g(claim_type, vote=None, occurred="2024-06-01T00:00:00Z", doc="d", tier=1):
    return GraphEvidence(
        claim_type=claim_type,
        node_ids={"speaker_person_id": "P"},
        properties={"vote_value": vote, "occurred_at": occurred} if vote else {"occurred_at": occurred},
        source_document_ids=(doc,),
        source_tier=tier,
    )


def _l(span="s", tier=1):
    return LexicalEvidence(span, "d", "example excerpt text", tier, 1.0)


def test_non_checkable_returns_non_checkable_verdict() -> None:
    inputs = VerdictInputs(
        claim_id="C",
        claim_type="vote_cast",
        checkability="insufficient_time_scope",
    )
    out = decide_verdict(inputs)
    assert out.status == "non_checkable"
    assert out.confidence.overall == 0.0


def test_no_evidence_is_insufficient_and_needs_review() -> None:
    inputs = VerdictInputs(
        claim_id="C",
        claim_type="vote_cast",
        checkability="checkable",
    )
    out = decide_verdict(inputs)
    assert out.status == "insufficient_evidence"
    assert out.needs_human_review


def test_vote_cast_supports_matching_recorded_vote() -> None:
    ranked = rerank([_g("vote_cast", vote="for")], claim_type="vote_cast")
    inputs = VerdictInputs(
        claim_id="C",
        claim_type="vote_cast",
        checkability="checkable",
        ranked_evidence=ranked,
        expected_vote_value="for",
    )
    out = decide_verdict(inputs)
    assert out.status == "supported"


def test_vote_cast_contradicts_mismatched_vote() -> None:
    ranked = rerank([_g("vote_cast", vote="against")], claim_type="vote_cast")
    inputs = VerdictInputs(
        claim_id="C",
        claim_type="vote_cast",
        checkability="checkable",
        ranked_evidence=ranked,
        expected_vote_value="for",
    )
    out = decide_verdict(inputs)
    assert out.status == "contradicted"


def test_committee_attendance_only_absent_contradicts() -> None:
    ev = GraphEvidence(
        claim_type="committee_attendance",
        node_ids={},
        properties={"presence": "absent"},
        source_document_ids=("d",),
        source_tier=1,
    )
    ranked = rerank([ev], claim_type="committee_attendance")
    inputs = VerdictInputs(
        claim_id="C",
        claim_type="committee_attendance",
        checkability="checkable",
        ranked_evidence=ranked,
    )
    out = decide_verdict(inputs)
    assert out.status == "contradicted"


def test_office_held_without_graph_hit_falls_to_lexical() -> None:
    ranked = rerank([_l(), _l("s2")], claim_type="office_held")
    inputs = VerdictInputs(
        claim_id="C",
        claim_type="office_held",
        checkability="checkable",
        ranked_evidence=ranked,
    )
    out = decide_verdict(inputs)
    assert out.status == "supported"


def test_provenance_bundler_runs_summarizer_on_review() -> None:
    class _Summ:
        def summarize(self, payload):
            return "note"

    ranked = rerank([_l()], claim_type="bill_sponsorship")
    inputs = VerdictInputs(
        claim_id="C",
        claim_type="bill_sponsorship",
        checkability="checkable",
        ranked_evidence=ranked,
    )
    outcome = decide_verdict(inputs)
    bundle = bundle_provenance(
        outcome, ranked, claim_id="C", claim_type="bill_sponsorship", summarizer=_Summ()
    )
    if outcome.needs_human_review:
        assert bundle.uncertainty_note == "note"
    else:
        assert bundle.uncertainty_note is None


def test_uncertainty_bundler_class_is_callable() -> None:
    ranked = rerank([_g("office_held")], claim_type="office_held")
    inputs = VerdictInputs(
        claim_id="C",
        claim_type="office_held",
        checkability="checkable",
        ranked_evidence=ranked,
    )
    outcome = decide_verdict(inputs)
    bundler = UncertaintyBundler()
    bundle = bundler(outcome, ranked, claim_id="C", claim_type="office_held")
    assert "verdict" in bundle.as_dict()
    assert bundle.as_dict()["verdict"]["claim_id"] == "C"
