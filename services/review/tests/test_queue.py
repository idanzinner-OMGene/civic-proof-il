"""Tests for PostgresReviewRepository using an in-memory fake cursor.

The real repo issues SQL via psycopg; the fake below records every
statement the repo executes and serves canned rows. Tests assert both
the state transition AND the audit-log insert.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from civic_review import PostgresReviewRepository, ReviewAction


class _FakeCursor:
    def __init__(self, rows_by_query: dict[str, list[tuple]]):
        self._rows_by_query = rows_by_query
        self.calls: list[tuple[str, tuple]] = []
        self._last_rows: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql: str, params=()):
        self.calls.append((sql, params))
        self._last_rows = self._match(sql)

    def fetchone(self):
        return self._last_rows[0] if self._last_rows else None

    def fetchall(self):
        return list(self._last_rows)

    def _match(self, sql: str) -> list[tuple]:
        for key, rows in self._rows_by_query.items():
            if key in sql:
                return rows
        return []


class _FakeConn:
    def __init__(self, rows_by_query: dict[str, list[tuple]]):
        self.cursor_obj = _FakeCursor(rows_by_query)

    def cursor(self):
        return self.cursor_obj


def _task_row(task_id, status="open") -> tuple:
    return (
        1,
        str(task_id),
        "verdict",
        status,
        0,
        json.dumps({"verdict_id": "v-1"}),
        None,
        datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc),
    )


def test_resolve_task_approve_transitions_to_resolved_and_writes_audit_row() -> None:
    tid = uuid4()
    open_row = _task_row(tid, "open")
    resolved_row = _task_row(tid, "resolved")
    conn = _FakeConn(
        {
            "FROM review_tasks\n                WHERE task_id": [open_row],
            "UPDATE review_tasks": [resolved_row],
        }
    )
    repo = PostgresReviewRepository(conn)
    out = repo.resolve_task(tid, decision="approve", reviewer_id="rev_1", notes="ok")
    assert out is not None
    assert out["status"] == "resolved"
    sqls = [c[0] for c in conn.cursor_obj.calls]
    assert any("UPDATE review_tasks" in s for s in sqls)
    assert any("INSERT INTO review_actions" in s for s in sqls)


def test_resolve_task_returns_none_when_task_missing() -> None:
    conn = _FakeConn({})  # no row
    repo = PostgresReviewRepository(conn)
    out = repo.resolve_task(uuid4(), decision="approve", reviewer_id="rev_1", notes=None)
    assert out is None


def test_resolve_task_rejects_unknown_decision() -> None:
    conn = _FakeConn({"FROM review_tasks": [_task_row(uuid4())]})
    repo = PostgresReviewRepository(conn)
    out = repo.resolve_task(uuid4(), decision="frobnicate", reviewer_id="r", notes=None)
    assert out is None


def test_resolve_task_escalate_marks_status_escalated() -> None:
    tid = uuid4()
    conn = _FakeConn(
        {
            "FROM review_tasks\n                WHERE task_id": [_task_row(tid, "open")],
            "UPDATE review_tasks": [_task_row(tid, "escalated")],
        }
    )
    repo = PostgresReviewRepository(conn)
    out = repo.resolve_task(tid, decision="escalate", reviewer_id="rev_2", notes=None)
    assert out is not None
    assert out["status"] == "escalated"


def test_resolve_task_annotate_keeps_status_open() -> None:
    tid = uuid4()
    conn = _FakeConn(
        {
            "FROM review_tasks\n                WHERE task_id": [_task_row(tid, "open")],
            "UPDATE review_tasks": [_task_row(tid, "open")],
        }
    )
    repo = PostgresReviewRepository(conn)
    out = repo.resolve_task(tid, decision="annotate", reviewer_id="rev_1", notes="pending")
    assert out is not None
    assert out["status"] == "open"


def test_resolve_task_on_terminal_row_still_records_audit() -> None:
    tid = uuid4()
    conn = _FakeConn(
        {
            "FROM review_tasks\n                WHERE task_id": [_task_row(tid, "resolved")],
        }
    )
    repo = PostgresReviewRepository(conn)
    out = repo.resolve_task(tid, decision="annotate", reviewer_id="rev_1", notes=None)
    assert out is not None
    sqls = [c[0] for c in conn.cursor_obj.calls]
    assert not any("UPDATE review_tasks" in s for s in sqls)
    assert any("INSERT INTO review_actions" in s for s in sqls)


def test_list_open_tasks_queries_open_and_claimed_rows() -> None:
    tid = uuid4()
    conn = _FakeConn(
        {"FROM review_tasks\n                WHERE status IN": [_task_row(tid, "open")]}
    )
    repo = PostgresReviewRepository(conn)
    rows = repo.list_open_tasks(limit=10)
    assert rows and rows[0]["task_id"] == str(tid)


def test_review_action_enum_exposes_five_values() -> None:
    assert {a.value for a in ReviewAction} == {
        "approve",
        "reject",
        "relink",
        "annotate",
        "escalate",
    }
