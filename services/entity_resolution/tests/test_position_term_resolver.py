"""Unit tests for :func:`resolve_position_terms`.

Uses a fake Neo4j session stub — an infrastructure mock, not domain data.
Per ``.cursor/rules/real-data-tests.mdc``, pure-logic unit tests with
minimal inline inputs are allowed when those inputs are not styled as
realistic domain entities.  The values here are test-run bookkeeping
UUIDs and ISO-8601 strings, not real person/office identities.
"""

from __future__ import annotations

from typing import Any

from civic_entity_resolution import PositionTermMatch, resolve_position_terms


# ---------------------------------------------------------------------------
# Fake Neo4j session stub
# ---------------------------------------------------------------------------


class _FakeRecord:
    """Minimal record stub that mimics neo4j.Record's dict-like access."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeSession:
    """Fake session that returns pre-canned records from ``run()``."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.last_cypher: str | None = None
        self.last_params: dict[str, Any] = {}

    def run(self, cypher: str, **params: Any) -> list[_FakeRecord]:
        self.last_cypher = cypher
        self.last_params = params
        return [_FakeRecord(r) for r in self._rows]


# ---------------------------------------------------------------------------
# Shared test data (not real domain records — test bookkeeping UUIDs only)
# ---------------------------------------------------------------------------

_PERSON_ID = "aaaaaaaa-0000-4000-8000-000000000001"
_OFFICE_ID_A = "bbbbbbbb-0000-4000-8000-000000000001"
_OFFICE_ID_B = "bbbbbbbb-0000-4000-8000-000000000002"
_TERM_ID_1 = "cccccccc-0000-4000-8000-000000000001"
_TERM_ID_2 = "cccccccc-0000-4000-8000-000000000002"

_ROW_MINISTER = {
    "position_term_id": _TERM_ID_1,
    "person_id": _PERSON_ID,
    "office_id": _OFFICE_ID_A,
    "appointing_body": "government",
    "valid_from": "2022-11-15T00:00:00",
    "valid_to": None,
    "is_acting": False,
}

_ROW_MK_EXPIRED = {
    "position_term_id": _TERM_ID_2,
    "person_id": _PERSON_ID,
    "office_id": _OFFICE_ID_B,
    "appointing_body": "knesset",
    "valid_from": "2021-03-01T00:00:00",
    "valid_to": "2022-11-14T00:00:00",
    "is_acting": False,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolve_returns_matching_terms():
    session = _FakeSession([_ROW_MINISTER])
    results = resolve_position_terms(session, person_id=_PERSON_ID)

    assert len(results) == 1
    m = results[0]
    assert isinstance(m, PositionTermMatch)
    assert m.position_term_id == _TERM_ID_1
    assert m.person_id == _PERSON_ID
    assert m.office_id == _OFFICE_ID_A
    assert m.appointing_body == "government"
    assert m.valid_from == "2022-11-15T00:00:00"
    assert m.valid_to is None
    assert m.is_acting is False


def test_resolve_passes_person_id_to_cypher():
    session = _FakeSession([])
    resolve_position_terms(session, person_id=_PERSON_ID)

    assert session.last_params.get("person_id") == _PERSON_ID


def test_resolve_passes_office_id_when_supplied():
    session = _FakeSession([_ROW_MINISTER])
    resolve_position_terms(session, person_id=_PERSON_ID, office_id=_OFFICE_ID_A)

    assert session.last_params.get("office_id") == _OFFICE_ID_A
    assert "$office_id" in session.last_cypher  # type: ignore[operator]


def test_resolve_passes_as_of_date_when_supplied():
    session = _FakeSession([_ROW_MINISTER])
    resolve_position_terms(
        session, person_id=_PERSON_ID, as_of_date="2023-06-01"
    )

    assert session.last_params.get("as_of_date") == "2023-06-01"
    assert "$as_of_date" in session.last_cypher  # type: ignore[operator]


def test_resolve_no_match_returns_empty():
    session = _FakeSession([])
    results = resolve_position_terms(session, person_id=_PERSON_ID)

    assert results == []


def test_resolve_multiple_terms_returns_all():
    session = _FakeSession([_ROW_MINISTER, _ROW_MK_EXPIRED])
    results = resolve_position_terms(session, person_id=_PERSON_ID)

    assert len(results) == 2
    ids = {r.position_term_id for r in results}
    assert ids == {_TERM_ID_1, _TERM_ID_2}


def test_resolve_open_ended_term_has_none_valid_to():
    """A term with no valid_to (ongoing) must come back with valid_to=None."""
    session = _FakeSession([_ROW_MINISTER])
    results = resolve_position_terms(session, person_id=_PERSON_ID)

    assert len(results) == 1
    assert results[0].valid_to is None


def test_resolve_expired_term_has_valid_to():
    """A term with a finish date must surface that date."""
    session = _FakeSession([_ROW_MK_EXPIRED])
    results = resolve_position_terms(session, person_id=_PERSON_ID)

    assert len(results) == 1
    assert results[0].valid_to == "2022-11-14T00:00:00"


def test_resolve_without_office_or_date_omits_those_filters():
    """When office_id and as_of_date are both None, neither filter clause
    nor parameter should appear in the generated Cypher."""
    session = _FakeSession([])
    resolve_position_terms(session, person_id=_PERSON_ID)

    cypher = session.last_cypher or ""
    assert "$office_id" not in cypher
    assert "$as_of_date" not in cypher


def test_resolve_is_acting_field_mapped_correctly():
    """is_acting must be passed through as a bool."""
    row = {**_ROW_MINISTER, "is_acting": True}
    session = _FakeSession([row])
    results = resolve_position_terms(session, person_id=_PERSON_ID)

    assert results[0].is_acting is True
