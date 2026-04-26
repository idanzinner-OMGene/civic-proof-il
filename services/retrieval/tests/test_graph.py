"""Tests for the graph retrieval dispatcher.

Uses a fake Neo4j driver to avoid the docker stack. Cypher files are
still loaded from disk so the test fails if an expected template is
missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from civic_retrieval.graph import (
    TEMPLATE_DIR,
    GraphRetriever,
    run_graph_retrieval,
)


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.seen_cypher: str | None = None
        self.seen_params: dict | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def run(self, cypher, **params):
        self.seen_cypher = cypher
        self.seen_params = params
        return iter(self._rows)


class _FakeDriver:
    def __init__(self, rows):
        self._session = _FakeSession(rows)

    def session(self):
        return self._session


def test_all_six_claim_type_templates_exist_on_disk() -> None:
    expected = {
        "vote_cast.cypher",
        "bill_sponsorship.cypher",
        "office_held.cypher",
        "committee_membership.cypher",
        "committee_attendance.cypher",
        "statement_about_formal_action.cypher",
    }
    actual = {p.name for p in TEMPLATE_DIR.glob("*.cypher")}
    assert expected <= actual, f"missing templates: {expected - actual}"


def test_unknown_claim_type_raises() -> None:
    with pytest.raises(FileNotFoundError):
        run_graph_retrieval(_FakeDriver([]), "nope", {})


def test_vote_cast_dispatch_records_cypher_and_params() -> None:
    rows = [
        {
            "node_ids": {"speaker_person_id": "A", "vote_event_id": "B", "bill_id": "C"},
            "properties": {"vote_value": "for", "occurred_at": "2024-01-01T00:00:00Z"},
            "source_document_ids": ["D1"],
            "source_tier": 1,
        }
    ]
    driver = _FakeDriver(rows)
    ev = run_graph_retrieval(
        driver,
        "vote_cast",
        {
            "speaker_person_id": "A",
            "bill_id": "C",
            "time_start": "2024-01-01T00:00:00Z",
            "time_end": "2024-12-31T23:59:59Z",
        },
    )
    assert len(ev) == 1
    assert ev[0].node_ids["speaker_person_id"] == "A"
    assert ev[0].properties["vote_value"] == "for"
    assert ev[0].source_document_ids == ("D1",)
    assert ev[0].source_tier == 1


def test_record_missing_keys_defaults_to_empty() -> None:
    driver = _FakeDriver([{}])
    ev = run_graph_retrieval(
        driver,
        "office_held",
        {"speaker_person_id": "A", "office_id": "B"},
    )
    assert len(ev) == 1
    assert ev[0].node_ids == {}
    assert ev[0].source_tier == 1
