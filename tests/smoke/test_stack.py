"""End-to-end smoke tests against the running docker-compose stack."""

from __future__ import annotations

import httpx


def test_healthz(api_url, wait_for_api):
    r = httpx.get(f"{api_url}/healthz", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz_all_green(api_url, wait_for_api):
    r = httpx.get(f"{api_url}/readyz", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ready"
    for key in ("postgres", "neo4j", "opensearch", "minio"):
        assert body["components"].get(key) is True, f"{key} unhealthy: {body}"
