"""Reviewer confirmation of evidence spans (audit only in Phase 5 v1)."""

from __future__ import annotations

import json

import psycopg

from .audit import ReviewAction, ReviewActionRecord
from .queue import ReviewTask

__all__ = ["append_span_confirmation"]


def append_span_confirmation(
    conn: psycopg.Connection,
    *,
    task: ReviewTask,
    span_ids: list[str],
    reviewer_id: str,
) -> bool:
    """Record an ``annotate``-style action with ``span_ids`` in the diff (non-terminal)."""

    if not span_ids:
        return False
    diff = {
        "kind": "evidence_confirmation",
        "span_ids": list(span_ids),
    }
    rec = ReviewActionRecord.new(
        task_id=task.id,
        actor=reviewer_id,
        action=ReviewAction.ANNOTATE,
        diff=diff,
    )
    with conn.cursor() as cur:
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
    return True
