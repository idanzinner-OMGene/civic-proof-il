"""Tests for civic_verification.attribution_judge — edge construction from v1 verdicts."""

from __future__ import annotations

import uuid
from uuid import UUID

from civic_verification.attribution_judge import (
    build_attribution_edge,
    determine_to_object_type,
    extract_evidence_span_ids,
    extract_to_object_id,
)


# --- determine_to_object_type ---


def test_determine_to_object_type_vote_cast() -> None:
    assert determine_to_object_type("vote_cast") == "VoteEvent"


def test_determine_to_object_type_office_held() -> None:
    assert determine_to_object_type("office_held") == "PositionTerm"


def test_determine_to_object_type_bill_sponsorship() -> None:
    assert determine_to_object_type("bill_sponsorship") == "Bill"


def test_determine_to_object_type_election_result() -> None:
    assert determine_to_object_type("election_result") == "ElectionResult"


def test_determine_to_object_type_unknown_fallback() -> None:
    assert determine_to_object_type("some_other_type") == "AtomicClaim"


# --- extract_to_object_id ---


def test_extract_to_object_id_vote_cast() -> None:
    target = UUID("aaaaaaaa-1111-2222-3333-444444444444")
    result = extract_to_object_id(
        "vote_cast",
        [
            {
                "kind": "graph",
                "claim_type": "vote_cast",
                "node_ids": {"vote_event_id": str(target)},
            },
        ],
        fallback_claim_id=uuid.uuid4(),
    )
    assert result == target


def test_extract_to_object_id_fallback() -> None:
    fallback = uuid.uuid4()
    result = extract_to_object_id("vote_cast", [], fallback_claim_id=fallback)
    assert result == fallback


# --- extract_evidence_span_ids ---


def test_extract_evidence_span_ids_dedupes() -> None:
    span = UUID("00000000-0000-0000-0000-000000000001")
    evidence = [
        {"kind": "graph", "node_ids": {"span_id": str(span)}},
        {"kind": "graph", "node_ids": {"span_id": str(span)}},
    ]
    result = extract_evidence_span_ids(evidence)
    assert result == [span]


def test_extract_evidence_span_ids_from_lexical() -> None:
    span = UUID("00000000-0000-0000-0000-000000000002")
    evidence = [
        {"kind": "lexical", "span_id": str(span)},
    ]
    result = extract_evidence_span_ids(evidence)
    assert result == [span]


# --- build_attribution_edge ---


def test_build_attribution_edge_supported() -> None:
    decl_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    edge = build_attribution_edge(
        declaration_id=decl_id,
        claim_id=claim_id,
        claim_type="vote_cast",
        verdict_status="supported",
        checkability="checkable",
        confidence_overall=0.85,
        top_evidence=[],
        reasons=[],
        lexical_hits=0,
        needs_human_review=False,
    )
    assert edge.relation_type == "supported_by"
    assert edge.confidence_band == "high"
    assert edge.review_status == "pending"
    assert edge.from_declaration_id == decl_id
    assert edge.to_object_type == "VoteEvent"


def test_build_attribution_edge_needs_review() -> None:
    edge = build_attribution_edge(
        declaration_id=uuid.uuid4(),
        claim_id=uuid.uuid4(),
        claim_type="vote_cast",
        verdict_status="supported",
        checkability="checkable",
        confidence_overall=0.85,
        top_evidence=[],
        reasons=[],
        lexical_hits=0,
        needs_human_review=True,
    )
    assert edge.review_status == "needs_human_review"


def test_build_attribution_edge_low_confidence() -> None:
    edge = build_attribution_edge(
        declaration_id=uuid.uuid4(),
        claim_id=uuid.uuid4(),
        claim_type="office_held",
        verdict_status="mixed",
        checkability="checkable",
        confidence_overall=0.3,
        top_evidence=[],
        reasons=[],
        lexical_hits=2,
        needs_human_review=False,
    )
    assert edge.confidence_band == "uncertain"
