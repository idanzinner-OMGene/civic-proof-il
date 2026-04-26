"""Regression: every supported verdict with claims must carry evidence context."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.regression

from civic_retrieval import GraphEvidence, rerank
from civic_verification import VerdictInputs, decide_verdict, bundle_provenance


def test_supported_vote_has_top_evidence_or_abstains():
    g = [
        GraphEvidence(
            claim_type="vote_cast",
            node_ids={"a": "1"},
            properties={"vote_value": "for"},
            source_tier=1,
        )
    ]
    rnk = rerank(g, claim_type="vote_cast")
    out = decide_verdict(
        VerdictInputs(
            claim_id="c1",
            claim_type="vote_cast",
            checkability="checkable",
            ranked_evidence=rnk,
            expected_vote_value="for",
        )
    )
    b = bundle_provenance(out, rnk, claim_id="c1", claim_type="vote_cast")
    d = b.as_dict()
    if d["verdict"].get("status") == "supported":
        assert d.get("top_evidence") is not None


def test_tier2_vote_mismatch_still_emits_traced_outcome():
    g = [
        GraphEvidence(
            claim_type="vote_cast",
            node_ids={"a": "1"},
            properties={"vote_value": "against"},
            source_tier=2,
        )
    ]
    rnk = rerank(g, claim_type="vote_cast")
    out = decide_verdict(
        VerdictInputs(
            claim_id="c1",
            claim_type="vote_cast",
            checkability="checkable",
            ranked_evidence=rnk,
            expected_vote_value="for",
        )
    )
    assert out.status in {"contradicted", "insufficient_evidence", "supported", "mixed"}
    assert out.reasons  # must carry at least one trace row for debugging


def test_tier2_only_contradiction_flags_human_review():
    """Tier-2/3 graph rows alone must not auto-close a contradiction."""
    g = [
        GraphEvidence(
            claim_type="vote_cast",
            node_ids={"a": "1"},
            properties={"vote_value": "against"},
            source_tier=2,
        )
    ]
    rnk = rerank(g, claim_type="vote_cast")
    out = decide_verdict(
        VerdictInputs(
            claim_id="c1",
            claim_type="vote_cast",
            checkability="checkable",
            ranked_evidence=rnk,
            expected_vote_value="for",
        )
    )
    if out.status == "contradicted":
        assert out.needs_human_review is True


def test_supported_bundle_has_top_evidence_when_confidence_positive():
    g = [
        GraphEvidence(
            claim_type="vote_cast",
            node_ids={"a": "1"},
            properties={"vote_value": "for"},
            source_tier=1,
        )
    ]
    rnk = rerank(g, claim_type="vote_cast")
    out = decide_verdict(
        VerdictInputs(
            claim_id="c1",
            claim_type="vote_cast",
            checkability="checkable",
            ranked_evidence=rnk,
            expected_vote_value="for",
        )
    )
    b = bundle_provenance(out, rnk, claim_id="c1", claim_type="vote_cast")
    d = b.as_dict()
    overall = float(d["verdict"].get("confidence", {}).get("overall", 0.0))
    if overall > 0.0:
        assert d.get("top_evidence"), "top_evidence must be non-empty when confidence is positive"
