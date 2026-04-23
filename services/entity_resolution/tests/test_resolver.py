"""Unit tests for the deterministic resolver.

Exercises steps 1-4 via in-memory fakes for Neo4j session + psycopg
connection. Live-DB coverage lives in the Phase-2 integration test.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from civic_entity_resolution.resolver import resolve


class _FakeNeoResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FakeNeoSession:
    def __init__(self, rows_by_needle: dict[str, list[dict]] | None = None,
                 exact_rows: list[dict] | None = None):
        self._rows_by_needle = rows_by_needle or {}
        self._exact_rows = exact_rows or []

    def run(self, cypher: str, **params):
        if "CONTAINS $needle" in cypher:
            return _FakeNeoResult(self._rows_by_needle.get(params["needle"], []))
        if "hebrew_name: $name" in cypher:
            return _FakeNeoResult(self._exact_rows)
        return _FakeNeoResult([])


@dataclass
class _FakePGCursor:
    rows: list[tuple] = field(default_factory=list)
    last_query: str = ""
    last_params: tuple = ()

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
    def __init__(self, alias_rows: list[tuple]):
        self._cursor = _FakePGCursor(rows=alias_rows)

    def cursor(self):
        return self._cursor


def test_external_id_match_is_step_1():
    person_id = uuid.uuid4()
    session = _FakeNeoSession(
        rows_by_needle={
            '"knesset_mk_id": "800"': [{"id": str(person_id)}],
        }
    )
    result = resolve(
        "person",
        external_ids={"knesset_mk_id": "800"},
        neo4j_session=session,
    )
    assert result.is_resolved()
    assert result.entity_id == person_id
    assert result.candidates[0].match_step == 1


def test_hebrew_exact_match_is_step_2():
    person_id = uuid.uuid4()
    session = _FakeNeoSession(
        exact_rows=[{"id": str(person_id)}],
    )
    result = resolve(
        "person",
        hebrew_name="אברהם",
        neo4j_session=session,
    )
    assert result.is_resolved()
    assert result.entity_id == person_id
    assert result.candidates[0].match_step == 2


def test_alias_match_is_step_3():
    person_id = uuid.uuid4()
    session = _FakeNeoSession()
    pg = _FakePGConn(alias_rows=[(person_id, 90)])
    result = resolve(
        "person",
        hebrew_name="אברהם",
        neo4j_session=session,
        pg_conn=pg,
    )
    assert result.is_resolved()
    assert result.entity_id == person_id
    assert result.candidates[0].match_step == 3


def test_unresolved_returns_none():
    session = _FakeNeoSession()
    result = resolve(
        "person",
        hebrew_name="לא קיים",
        neo4j_session=session,
        pg_conn=_FakePGConn(alias_rows=[]),
    )
    assert result.status == "unresolved"
    assert result.entity_id is None


def test_ambiguous_returns_candidates_not_resolved():
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    session = _FakeNeoSession()
    pg = _FakePGConn(alias_rows=[(id_a, 90), (id_b, 90)])
    result = resolve(
        "person",
        hebrew_name="אברהם",
        neo4j_session=session,
        pg_conn=pg,
    )
    assert result.status == "ambiguous"
    assert result.entity_id is None
    assert len(result.candidates) == 2


def test_invalid_kind_raises():
    with pytest.raises(ValueError):
        resolve("alien", hebrew_name="X")  # type: ignore[arg-type]
