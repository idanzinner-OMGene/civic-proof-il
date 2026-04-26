"""Tests for step-5 fuzzy match and step-6 LLM tiebreaker (Phase 3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from civic_entity_resolution import (
    FUZZY_MARGIN,
    FUZZY_RESOLVE_THRESHOLD,
    Candidate,
    resolve,
)


class _FakeRecord(dict):
    def get(self, key, default=None):  # type: ignore[override]
        return super().get(key, default)


class _FakeFuzzySession:
    """Fake Neo4j session returning a configurable set of (id, he, en) rows."""

    def __init__(self, rows: list[dict]):
        self._rows = [_FakeRecord(r) for r in rows]

    def run(self, cypher: str, **_params):
        if "LIMIT 500" in cypher:
            return iter(self._rows)
        return iter([])


@dataclass
class _FakePGCursor:
    last_query: str = ""
    last_params: tuple = ()
    rows: list[tuple] = field(default_factory=list)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, query, params):
        self.last_query = query
        self.last_params = params

    def fetchall(self):
        return self.rows


class _FakePGConn:
    def __init__(self, alias_rows=None):
        self._cursor = _FakePGCursor(rows=alias_rows or [])

    def cursor(self):
        return self._cursor


def test_fuzzy_resolves_when_score_clears_threshold_and_margin() -> None:
    person_id = uuid.uuid4()
    other_id = uuid.uuid4()
    session = _FakeFuzzySession(
        [
            {"id": str(person_id), "he": "אברהם לוי", "en": "Avraham Levi"},
            {"id": str(other_id), "he": "שרה כהן", "en": "Sara Cohen"},
        ]
    )
    result = resolve(
        "person",
        hebrew_name="אברהם לוי",
        neo4j_session=session,
        pg_conn=_FakePGConn(),
    )
    assert result.is_resolved()
    assert result.entity_id == person_id
    assert any(c.match_step == 5 for c in result.candidates)


def test_fuzzy_ambiguous_when_margin_too_small() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    # Two nearly-identical names should both score above threshold but
    # within the margin, so resolver returns ambiguous.
    session = _FakeFuzzySession(
        [
            {"id": str(a), "he": "יוסף כהן", "en": "Yosef Cohen"},
            {"id": str(b), "he": "יוסף כוהן", "en": "Yosef Cohen"},
        ]
    )
    result = resolve(
        "person",
        hebrew_name="יוסף כהן",
        neo4j_session=session,
        pg_conn=_FakePGConn(),
    )
    assert result.status == "ambiguous"


def test_fuzzy_below_threshold_returns_unresolved() -> None:
    session = _FakeFuzzySession(
        [{"id": str(uuid.uuid4()), "he": "שם שונה לגמרי", "en": "Totally Different"}]
    )
    result = resolve(
        "person",
        hebrew_name="אברהם לוי",
        neo4j_session=session,
        pg_conn=_FakePGConn(),
    )
    assert result.status == "unresolved"


class _PickFirstTiebreaker:
    def pick(self, kind, he, en, candidates):
        return candidates[0].entity_id


def test_llm_tiebreaker_picks_when_ambiguous() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    session = _FakeFuzzySession(
        [
            {"id": str(a), "he": "יוסף כהן", "en": "Yosef Cohen"},
            {"id": str(b), "he": "יוסף כוהן", "en": "Yosef Cohen"},
        ]
    )
    result = resolve(
        "person",
        hebrew_name="יוסף כהן",
        neo4j_session=session,
        pg_conn=_FakePGConn(),
        llm_tiebreaker=_PickFirstTiebreaker(),
    )
    assert result.is_resolved()
    assert result.entity_id in {a, b}


class _RefuseTiebreaker:
    def pick(self, kind, he, en, candidates):
        return None


def test_llm_tiebreaker_returning_none_keeps_ambiguous() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    session = _FakeFuzzySession(
        [
            {"id": str(a), "he": "יוסף כהן", "en": "Yosef Cohen"},
            {"id": str(b), "he": "יוסף כוהן", "en": "Yosef Cohen"},
        ]
    )
    result = resolve(
        "person",
        hebrew_name="יוסף כהן",
        neo4j_session=session,
        pg_conn=_FakePGConn(),
        llm_tiebreaker=_RefuseTiebreaker(),
    )
    assert result.status == "ambiguous"


def test_constants_are_in_sane_range() -> None:
    assert 50 <= FUZZY_RESOLVE_THRESHOLD <= 100
    assert 1 <= FUZZY_MARGIN <= 30
