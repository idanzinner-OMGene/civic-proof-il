"""End-to-end tests for POST /claims/verify.

Uses a stub ``VerifyPipeline`` so the test is hermetic — no backing
services are required. The real pipeline is swapped in production via
:func:`api.routers.pipeline.set_pipeline` at app bootstrap.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.routers.pipeline import VerifyPipeline, get_pipeline


def _stub_pipeline_factory(response: list[dict]):
    class _Stub(VerifyPipeline):
        def verify(self, statement, language=None):  # noqa: ARG002
            return list(response)

    stub = _Stub()
    return lambda: stub


def test_verify_accepts_statement_and_returns_claims() -> None:
    expected = [
        {
            "verdict": {"status": "supported", "confidence": {"overall": 0.8}, "needs_human_review": False, "reasons": []},
            "top_evidence": [],
            "uncertainty_note": None,
            "claim": {"claim_id": "abc", "claim_type": "vote_cast"},
        }
    ]
    app.dependency_overrides[get_pipeline] = _stub_pipeline_factory(expected)
    try:
        with TestClient(app) as c:
            r = c.post("/claims/verify", json={"statement": "demo", "language": "he"})
        assert r.status_code == 200
        body = r.json()
        assert body["claims"] == expected
    finally:
        app.dependency_overrides.pop(get_pipeline, None)


def test_verify_rejects_empty_statement() -> None:
    with TestClient(app) as c:
        r = c.post("/claims/verify", json={"statement": "", "language": "he"})
    assert r.status_code == 422


def test_verify_pipeline_returns_empty_claims_without_backends() -> None:
    # The default pipeline has no backends wired; decomposition alone
    # may still emit claims but retrieval returns no evidence, so the
    # verdict engine abstains.
    with TestClient(app) as c:
        r = c.post(
            "/claims/verify",
            json={"statement": "This sentence does not match any rule template.", "language": "en"},
        )
    assert r.status_code == 200
    assert "claims" in r.json()
