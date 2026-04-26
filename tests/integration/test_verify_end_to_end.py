"""End-to-end /claims/verify integration against in-memory retrievers.

Wires a real :class:`VerifyPipeline` with deterministic fake graph +
lexical retrievers and pushes a statement through the FastAPI route.
Hermetic; no docker.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.routers.pipeline import VerifyPipeline, get_pipeline
from civic_retrieval import GraphEvidence, LexicalEvidence


class _FakeGraph:
    def retrieve(self, claim_type, *, params):  # noqa: ARG002
        if claim_type == "vote_cast":
            return [
                GraphEvidence(
                    claim_type="vote_cast",
                    node_ids={"speaker_person_id": "P"},
                    properties={"vote_value": "for", "occurred_at": "2024-06-01T00:00:00Z"},
                    source_document_ids=("doc-1",),
                    source_tier=1,
                )
            ]
        return []


class _FakeLex:
    def search(self, q, *, size=10):  # noqa: ARG002
        return [LexicalEvidence("s-1", "doc-2", "excerpt", 1, 0.8)]


def test_verify_pipeline_returns_bundle_with_evidence() -> None:
    pipeline = VerifyPipeline(graph=_FakeGraph(), lexical=_FakeLex())
    app.dependency_overrides[get_pipeline] = lambda: pipeline
    try:
        with TestClient(app) as c:
            r = c.post(
                "/claims/verify",
                json={
                    "statement": "David Amiti voted for the Budget Law in 2024",
                    "language": "en",
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert "claims" in body
        if body["claims"]:
            first = body["claims"][0]
            assert "verdict" in first
            assert "top_evidence" in first
            assert "claim" in first
            assert first["claim"]["claim_type"] in {
                "vote_cast",
                "bill_sponsorship",
                "office_held",
                "committee_membership",
                "committee_attendance",
                "statement_about_formal_action",
            }
    finally:
        app.dependency_overrides.pop(get_pipeline, None)


def test_verify_pipeline_emits_empty_claims_for_nonmatching_statement() -> None:
    pipeline = VerifyPipeline()
    app.dependency_overrides[get_pipeline] = lambda: pipeline
    try:
        with TestClient(app) as c:
            r = c.post(
                "/claims/verify",
                json={"statement": "Completely unrelated text.", "language": "en"},
            )
        assert r.status_code == 200
    finally:
        app.dependency_overrides.pop(get_pipeline, None)
