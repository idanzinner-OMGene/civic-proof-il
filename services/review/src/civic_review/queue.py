"""Review queue + Postgres-backed repository.

The MVP contract (plan lines 181-184): let a reviewer approve, reject,
relink, annotate, or escalate a task, and persist an immutable
audit-log row for every action. Full reviewer UI + conflict-resolution
flow stays in Phase 5.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID, uuid4

from psycopg import Connection

from .audit import ReviewAction, ReviewActionRecord

__all__ = [
    "PostgresReviewRepository",
    "ReviewTask",
    "open_review_task",
]


_VALID_STATUSES = {"open", "claimed", "resolved", "escalated"}
_TERMINAL_STATUSES = {"resolved", "escalated"}
_DECISION_TO_STATUS: dict[str, str] = {
    ReviewAction.APPROVE: "resolved",
    ReviewAction.REJECT: "resolved",
    ReviewAction.RELINK: "resolved",
    ReviewAction.ANNOTATE: "open",  # annotation is non-terminal
    ReviewAction.ESCALATE: "escalated",
}


@dataclass(frozen=True, slots=True)
class ReviewTask:
    id: int
    task_id: UUID
    kind: str
    status: str
    priority: int
    payload: dict[str, Any]
    assigned_to: str | None
    created_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": str(self.task_id),
            "kind": self.kind,
            "status": self.status,
            "priority": self.priority,
            "payload": self.payload,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat(),
        }


def open_review_task(
    conn: Connection,
    *,
    kind: str,
    payload: dict[str, Any],
    priority: int = 0,
) -> UUID:
    """Push a new open task onto the queue. Returns the ``task_id`` UUID."""

    if kind not in {"entity_resolution", "verdict", "conflict"}:
        raise ValueError(f"invalid review kind: {kind!r}")
    task_id = uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO review_tasks (task_id, kind, status, priority, payload)
            VALUES (%s, %s, 'open', %s, %s::jsonb)
            """,
            (str(task_id), kind, priority, json.dumps(payload)),
        )
    return task_id


class PostgresReviewRepository:
    """Concrete repository backing :mod:`api.routers.review`.

    All writes are atomic: the task update and the ``review_actions``
    insert happen inside the same transaction. If either step fails
    the caller sees a rollback.
    """

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def list_open_tasks(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, task_id, kind, status, priority, payload, assigned_to, created_at
                FROM review_tasks
                WHERE status IN ('open', 'claimed')
                ORDER BY priority DESC, id ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [self._row_to_task(r).as_dict() for r in rows]

    def resolve_task(
        self,
        task_id: UUID,
        *,
        decision: str,
        reviewer_id: str,
        notes: str | None,
    ) -> dict[str, Any] | None:
        """Apply a reviewer decision and write an audit-log row.

        ``decision`` is a ReviewAction value (string). Unknown actions
        return ``None`` without mutating state.
        """

        try:
            action = ReviewAction(decision)
        except ValueError:
            return None

        new_status = _DECISION_TO_STATUS[action]
        diff = {"notes": notes} if notes else {}

        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, task_id, kind, status, priority, payload, assigned_to, created_at
                FROM review_tasks
                WHERE task_id = %s
                FOR UPDATE
                """,
                (str(task_id),),
            )
            row = cur.fetchone()
            if row is None:
                return None
            task = self._row_to_task(row)
            if task.status in _TERMINAL_STATUSES:
                # Still record an audit trail for the attempted action.
                self._insert_action(cur, task.id, reviewer_id, action, diff)
                return task.as_dict()

            cur.execute(
                """
                UPDATE review_tasks
                SET status = %s, assigned_to = COALESCE(%s, assigned_to)
                WHERE id = %s
                RETURNING id, task_id, kind, status, priority, payload, assigned_to, created_at
                """,
                (new_status, reviewer_id, task.id),
            )
            updated = cur.fetchone()
            self._insert_action(cur, task.id, reviewer_id, action, diff)
        return self._row_to_task(updated).as_dict()

    @staticmethod
    def _insert_action(
        cur,
        task_id: int,
        actor: str,
        action: ReviewAction,
        diff: dict[str, Any],
    ) -> UUID:
        rec = ReviewActionRecord.new(task_id=task_id, actor=actor, action=action, diff=diff)
        cur.execute(
            """
            INSERT INTO review_actions (action_id, task_id, actor, action, diff, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            """,
            (
                str(rec.action_id),
                rec.task_id,
                rec.actor,
                rec.action.value,
                json.dumps(rec.diff),
                rec.created_at,
            ),
        )
        return rec.action_id

    @staticmethod
    def _row_to_task(row: Iterable[Any]) -> ReviewTask:
        id_, task_id, kind, status, priority, payload, assigned_to, created_at = row
        if isinstance(payload, (bytes, str)):
            payload = json.loads(payload)
        if not isinstance(created_at, datetime):
            created_at = datetime.fromisoformat(str(created_at))
        elif created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return ReviewTask(
            id=id_,
            task_id=UUID(str(task_id)),
            kind=kind,
            status=status,
            priority=priority,
            payload=payload,
            assigned_to=assigned_to,
            created_at=created_at,
        )
