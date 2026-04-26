"""Live-stack validation for /claims/verify (Phase 3+4 gold set).

``CIVIC_LIVE_WIRING=1`` forces the API lifespan to inject a live
``VerifyPipeline`` when ``ENV`` is not production-like (test/CI) but
all backing services are reachable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from yaml import YAMLError

from api.main import app
from civic_clients import minio_client, neo4j, opensearch, postgres
from civic_common.settings import get_settings

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
_STATEMENTS = ROOT / "tests" / "fixtures" / "phase3" / "statements"


def _all_backing_stores_up() -> bool:
    return bool(
        postgres.ping() and neo4j.ping() and opensearch.ping() and minio_client.ping()
    )


def _parse_labels(path: Path) -> dict[str, Any]:
    try:
        out = yaml.safe_load(path.read_text(encoding="utf-8"))
        return out if isinstance(out, dict) else {}
    except (YAMLError, OSError, TypeError):
        return {}


def test_phase34_gold_set_verify_roundtrip() -> None:
    if not _all_backing_stores_up():
        pytest.skip("one or more backing stores unreachable from this host")
    if not _STATEMENTS.is_dir():
        pytest.skip("no gold-set statement fixtures")

    old = os.environ.get("CIVIC_LIVE_WIRING")
    os.environ["CIVIC_LIVE_WIRING"] = "1"
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            n = 0
            for d in sorted(p for p in _STATEMENTS.iterdir() if p.is_dir()):
                st = d / "statement.txt"
                lab = d / "labels.yaml"
                if not st.is_file() or not lab.is_file():
                    continue
                text = st.read_text(encoding="utf-8").strip()
                data = _parse_labels(lab)
                lang = str(data.get("language", "he"))
                r = c.post(
                    "/claims/verify",
                    json={"statement": text, "language": lang},
                )
                assert r.status_code == 200, (d.name, r.text)
                body = r.json()
                assert "claims" in body
                n += 1
                ex = data.get("expected")
                if data.get("semantic_test") and isinstance(ex, dict):
                    want = ex.get("expected_claim_types")
                    if isinstance(want, list) and want:
                        got = {item.get("claim", {}).get("claim_type") for item in body["claims"]}
                        assert got <= set(want), (d.name, got, want)
            assert n >= 1, "no statement folders under gold set"
    finally:
        if old is None:
            os.environ.pop("CIVIC_LIVE_WIRING", None)
        else:
            os.environ["CIVIC_LIVE_WIRING"] = old
        get_settings.cache_clear()
