"""Tests for civic_verification.declaration_verifier — end-to-end declaration verification."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from civic_claim_decomp.declaration_decomposer import DeclarationDecompositionResult
from civic_claim_decomp.decomposer import DecomposedClaim
from civic_ontology.models.declaration import Declaration
from civic_verification.declaration_verifier import DeclarationVerifier


def _make_declaration() -> Declaration:
    return Declaration(
        declaration_id=uuid.uuid4(),
        speaker_person_id=None,
        utterance_text="test utterance",
        utterance_language="he",
        utterance_time=None,
        source_document_id=uuid.uuid4(),
        source_kind="other",
        quoted_span=None,
        canonicalized_text=None,
        claim_family="unknown",
        checkability="not_checkable",
        derived_atomic_claim_ids=[],
        created_at=datetime.now(tz=timezone.utc),
    )


def _make_claim(claim_type: str = "vote_cast") -> DecomposedClaim:
    return DecomposedClaim(
        claim_id=uuid.uuid4(),
        raw_text="test",
        normalized_text="test",
        claim_type=claim_type,
        slots={},
        time_phrase=None,
        method="rules",
        source_rule=None,
    )


def _make_bundle(
    status: str,
    confidence_overall: float = 0.85,
    needs_human_review: bool = False,
    claim_type: str = "vote_cast",
    checkability: str = "checkable",
) -> dict:
    return {
        "verdict": {
            "status": status,
            "confidence": {
                "overall": confidence_overall,
                "source_authority": 0.9,
                "directness": 0.8,
                "temporal_alignment": 0.8,
                "entity_resolution": 0.9,
                "cross_source_consistency": 0.8,
            },
            "needs_human_review": needs_human_review,
            "reasons": [{"kind": "support", "source": "graph", "count": 1}],
        },
        "top_evidence": [],
        "uncertainty_note": None,
        "claim": {
            "claim_id": str(uuid.uuid4()),
            "claim_type": claim_type,
            "normalized_text": "test",
            "slots": {},
            "time_phrase": None,
            "time_scope": {"start": None, "end": None, "granularity": "unknown"},
            "checkability": checkability,
            "method": "rule",
        },
    }


def _make_decomp_result(
    declaration: Declaration | None = None,
    claims: list[DecomposedClaim] | None = None,
) -> DeclarationDecompositionResult:
    decl = declaration or _make_declaration()
    return DeclarationDecompositionResult(
        declaration=decl,
        claims=claims or [],
    )


def test_verify_supported_produces_supported_by_edge() -> None:
    claim = _make_claim()
    decomp = _make_decomp_result(claims=[claim])
    pipeline = MagicMock()
    pipeline.verify.return_value = [_make_bundle("supported")]

    verifier = DeclarationVerifier(pipeline)
    result = verifier.verify(decomp)

    assert len(result.attribution_edges) == 1
    assert result.attribution_edges[0].relation_type == "supported_by"
    assert result.overall_relation == "supported_by"


def test_verify_contradicted_produces_contradicted_by_edge() -> None:
    claim = _make_claim()
    decomp = _make_decomp_result(claims=[claim])
    pipeline = MagicMock()
    pipeline.verify.return_value = [_make_bundle("contradicted")]

    verifier = DeclarationVerifier(pipeline)
    result = verifier.verify(decomp)

    assert len(result.attribution_edges) == 1
    assert result.attribution_edges[0].relation_type == "contradicted_by"
    assert result.overall_relation == "contradicted_by"


def test_verify_no_claims_returns_default_relation() -> None:
    decomp = _make_decomp_result(claims=[])
    pipeline = MagicMock()
    pipeline.verify.return_value = []

    verifier = DeclarationVerifier(pipeline)
    result = verifier.verify(decomp)

    assert result.attribution_edges == []
    assert result.overall_relation == "not_checkable_against_record"


def test_verify_multiple_claims_worst_relation() -> None:
    claims = [_make_claim(), _make_claim()]
    decomp = _make_decomp_result(claims=claims)
    pipeline = MagicMock()
    pipeline.verify.return_value = [
        _make_bundle("supported"),
        _make_bundle("contradicted"),
    ]

    verifier = DeclarationVerifier(pipeline)
    result = verifier.verify(decomp)

    assert len(result.attribution_edges) == 2
    assert result.overall_relation == "contradicted_by"


def test_verify_triggers_review_for_contradicted() -> None:
    claim = _make_claim()
    decomp = _make_decomp_result(claims=[claim])
    pipeline = MagicMock()
    pipeline.verify.return_value = [_make_bundle("contradicted")]

    review_conn = MagicMock()
    verifier = DeclarationVerifier(pipeline, review_connection=review_conn)

    with patch("civic_review.open_review_task") as mock_open:
        result = verifier.verify(decomp)
        assert result.overall_relation == "contradicted_by"
        mock_open.assert_called_once()
        call_kwargs = mock_open.call_args
        assert call_kwargs[1]["kind"] == "declaration"


def test_verify_no_review_for_supported() -> None:
    claim = _make_claim()
    decomp = _make_decomp_result(claims=[claim])
    pipeline = MagicMock()
    pipeline.verify.return_value = [_make_bundle("supported")]

    review_conn = MagicMock()
    verifier = DeclarationVerifier(pipeline, review_connection=review_conn)

    with patch("civic_review.open_review_task") as mock_open:
        result = verifier.verify(decomp)
        assert result.overall_relation == "supported_by"
        mock_open.assert_not_called()
