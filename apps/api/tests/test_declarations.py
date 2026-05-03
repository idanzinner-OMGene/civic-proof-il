"""Integration tests for the declarations API routes.

POST /declarations/ingest, POST /declarations/{id}/verify, GET /declarations/{id}
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import app
from api.routers.declarations import _declaration_cache
from api.routers.pipeline import VerifyPipeline, get_pipeline


def _stub_pipeline_factory(bundles: list[dict]):
    """Return a dependency-override factory that yields a fixed list of bundles."""

    class _Stub(VerifyPipeline):
        def verify(self, statement, language=None):  # noqa: ARG002
            return list(bundles)

    stub = _Stub()
    return lambda: stub


_SAMPLE_BUNDLE = {
    "verdict": {
        "status": "supported",
        "confidence": {"overall": 0.75},
        "needs_human_review": False,
        "reasons": [],
    },
    "top_evidence": [],
    "uncertainty_note": None,
    "claim": {"claim_id": "c1", "claim_type": "vote_cast", "checkability": "checkable"},
}


def _ingest(client: TestClient, **overrides) -> dict:
    """Helper: POST /declarations/ingest with sensible defaults."""
    body = {
        "utterance_text": overrides.pop("utterance_text", "voted against the bill"),
        "language": overrides.pop("language", "en"),
        "source_document_id": overrides.pop("source_document_id", str(uuid4())),
    }
    body.update(overrides)
    return client.post("/declarations/ingest", json=body).json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ingest_declaration() -> None:
    with TestClient(app) as c:
        r = c.post(
            "/declarations/ingest",
            json={
                "utterance_text": "\u05d7\u05d1\u05e8 \u05d4\u05db\u05e0\u05e1\u05ea \u05d4\u05e6\u05d1\u05d9\u05e2 \u05e0\u05d2\u05d3 \u05d4\u05d7\u05d5\u05e7",
                "language": "he",
                "source_document_id": str(uuid4()),
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert "declaration" in body
    assert "declaration_id" in body["declaration"]
    assert "utterance_text" in body["declaration"]
    assert body["claims_count"] >= 0
    assert isinstance(body["family"], str)
    assert isinstance(body["checkability"], str)


def test_ingest_declaration_minimal() -> None:
    with TestClient(app) as c:
        r = c.post(
            "/declarations/ingest",
            json={
                "utterance_text": "voted against the bill",
                "source_document_id": str(uuid4()),
            },
        )
    assert r.status_code == 200


def test_ingest_declaration_empty_text_rejected() -> None:
    with TestClient(app) as c:
        r = c.post(
            "/declarations/ingest",
            json={
                "utterance_text": "",
                "source_document_id": str(uuid4()),
            },
        )
    assert r.status_code == 422


def test_get_declaration_after_ingest() -> None:
    with TestClient(app) as c:
        ingest_body = _ingest(c)
        declaration_id = ingest_body["declaration"]["declaration_id"]
        r = c.get(f"/declarations/{declaration_id}")
    assert r.status_code == 200
    assert r.json()["declaration"]["declaration_id"] == declaration_id


def test_get_declaration_not_found() -> None:
    with TestClient(app) as c:
        r = c.get("/declarations/00000000-0000-0000-0000-000000000099")
    assert r.status_code == 404


def test_verify_declaration_after_ingest() -> None:
    app.dependency_overrides[get_pipeline] = _stub_pipeline_factory([_SAMPLE_BUNDLE])
    try:
        with TestClient(app) as c:
            ingest_body = _ingest(c)
            declaration_id = ingest_body["declaration"]["declaration_id"]
            r = c.post(
                f"/declarations/{declaration_id}/verify",
                json={"language": "he"},
            )
        assert r.status_code == 200
        body = r.json()
        assert "declaration" in body
        assert "claims" in body
        assert "claim_verdicts" in body
        assert "attribution_edges" in body
        assert isinstance(body["overall_relation"], str)
    finally:
        app.dependency_overrides.pop(get_pipeline, None)
        _declaration_cache.clear()


def test_verify_declaration_not_found() -> None:
    with TestClient(app) as c:
        r = c.post(
            "/declarations/00000000-0000-0000-0000-000000000099/verify",
            json={"language": "he"},
        )
    assert r.status_code == 404
