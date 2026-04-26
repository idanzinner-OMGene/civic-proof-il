"""Tests for the deterministic reranker."""

from __future__ import annotations

from civic_retrieval import GraphEvidence, LexicalEvidence, rerank


def _lex(span_id: str, tier: int, text: str = "ex", doc: str = "d") -> LexicalEvidence:
    return LexicalEvidence(span_id, doc, text, tier, 0.5)


def _graph(claim_type: str, tier: int = 1, doc: str = "d") -> GraphEvidence:
    return GraphEvidence(
        claim_type=claim_type,
        node_ids={"speaker_person_id": "P"},
        properties={"vote_value": "for", "occurred_at": "2024-06-01T00:00:00Z"},
        source_document_ids=(doc,),
        source_tier=tier,
    )


def test_tier1_beats_tier3() -> None:
    a = _lex("a", 1)
    b = _lex("b", 3)
    out = rerank([b, a], claim_type="vote_cast")
    assert out[0].evidence.span_id == "a"


def test_graph_evidence_with_matching_claim_type_ranks_high() -> None:
    g = _graph("vote_cast")
    lex = _lex("x", 2)
    out = rerank([lex, g], claim_type="vote_cast")
    assert out[0].evidence is g


def test_temporal_alignment_penalty() -> None:
    in_range = _graph("vote_cast")
    out_range = GraphEvidence(
        claim_type="vote_cast",
        node_ids={"speaker_person_id": "P"},
        properties={"occurred_at": "2020-01-01T00:00:00Z"},
        source_document_ids=("d2",),
        source_tier=1,
    )
    ranked = rerank(
        [out_range, in_range],
        claim_type="vote_cast",
        claim_time_scope={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z",
        },
    )
    assert ranked[0].evidence is in_range


def test_cross_source_bonus() -> None:
    a = _graph("vote_cast", doc="d1")
    b = _lex("s1", 1, doc="d2")
    c = _lex("s2", 1, doc="d3")
    ranked = rerank([a, b, c], claim_type="vote_cast")
    # With 3 distinct docs, cross_source_consistency maxes out for every item
    top = ranked[0]
    assert top.cross_source_consistency == 1.0
    assert 0.0 <= top.overall <= 1.0


def test_entity_resolution_match_bumps_score() -> None:
    matching = _graph("vote_cast")
    non_matching = GraphEvidence(
        claim_type="vote_cast",
        node_ids={"speaker_person_id": "OTHER"},
        properties={"occurred_at": "2024-06-01T00:00:00Z"},
        source_document_ids=("d2",),
        source_tier=1,
    )
    ranked = rerank(
        [non_matching, matching],
        claim_type="vote_cast",
        resolved_ids={"speaker_person_id": "P"},
    )
    assert ranked[0].evidence is matching


def test_deterministic_order() -> None:
    a = _lex("a", 1)
    b = _lex("b", 1)
    c = _lex("c", 1)
    ordering = [r.evidence.span_id for r in rerank([c, a, b], claim_type="vote_cast")]
    assert ordering == sorted(ordering)
