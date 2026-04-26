"""Unit tests for persist_statement (uses a fake psycopg connection)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from civic_claim_decomp import (
    DecomposedClaim,
    StatementRecord,
    persist_statement,
)


@dataclass
class _FakeCursor:
    executed: list[tuple[str, tuple]] = field(default_factory=list)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, query, params):
        self.executed.append((query, params))


class _FakeConn:
    def __init__(self):
        self._cursor = _FakeCursor()

    def cursor(self):
        return self._cursor


def _claim() -> DecomposedClaim:
    return DecomposedClaim(
        claim_id=uuid.uuid4(),
        raw_text="anything",
        normalized_text="anything",
        claim_type="vote_cast",
        slots={
            "speaker_person_id": "X",
            "target_person_id": None,
            "bill_id": "Y",
            "committee_id": None,
            "office_id": None,
            "vote_value": "for",
        },
        time_phrase="2024",
        method="rules",
    )


def test_persist_statement_inserts_one_statement_and_each_claim() -> None:
    conn = _FakeConn()
    stmt = StatementRecord(
        statement_id=uuid.uuid4(),
        raw_text="anything",
        language="en",
    )
    c1 = _claim()
    c2 = _claim()
    summary = persist_statement(
        conn,
        stmt,
        [c1, c2],
        checkability_by_claim={c1.claim_id: "checkable", c2.claim_id: "checkable"},
        time_scope_by_claim={
            c1.claim_id: {"start": None, "end": None, "granularity": "year"},
        },
    )
    assert summary["claims_persisted"] == 2
    executed = conn.cursor().executed
    # One INSERT into statements + two INSERTs into statement_claims.
    assert sum(1 for q, _ in executed if "INTO statements" in q) == 1
    assert sum(1 for q, _ in executed if "INTO statement_claims" in q) == 2


def test_persist_statement_default_checkability_is_non_checkable() -> None:
    conn = _FakeConn()
    stmt = StatementRecord(statement_id=uuid.uuid4(), raw_text="x", language="he")
    c = _claim()
    persist_statement(conn, stmt, [c], checkability_by_claim={})
    claim_rows = [p for q, p in conn.cursor().executed if "INTO statement_claims" in q]
    assert claim_rows
    assert "non_checkable" in claim_rows[0]
