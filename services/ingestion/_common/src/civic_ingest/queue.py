"""Postgres-native job queue using ``FOR UPDATE SKIP LOCKED``.

Three primitives:

* :func:`enqueue` — insert a ``queued`` row.
* :func:`claim_one` — atomically transition the oldest/highest-priority
  ``queued`` row to ``running`` (returns ``None`` if the queue is empty).
* :func:`mark_done` / :func:`mark_failed` — closing transitions. After
  ``max_attempts`` failures the row moves to ``dead_letter`` and stops
  being claimed.

The table schema is defined in ``0003_jobs_queue.py``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Literal

import psycopg
from psycopg.rows import dict_row

__all__ = [
    "Job",
    "JobKind",
    "claim_one",
    "enqueue",
    "mark_done",
    "mark_failed",
]


JobKind = Literal["fetch", "parse", "normalize", "upsert"]


@dataclass(frozen=True, slots=True)
class Job:
    id: int
    job_id: uuid.UUID
    kind: JobKind
    payload: dict[str, Any]
    priority: int
    attempts: int
    run_after: datetime
    ingest_run_id: uuid.UUID | None


def enqueue(
    conn: psycopg.Connection,
    *,
    kind: JobKind,
    payload: dict[str, Any],
    priority: int = 5,
    run_after: datetime | None = None,
    ingest_run_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Insert a ``queued`` row and return its ``job_id`` (UUID)."""

    job_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO jobs
              (job_id, kind, payload, priority, run_after, ingest_run_id)
            VALUES (%s, %s, %s::jsonb, %s,
                    COALESCE(%s, now()), %s)
            """,
            (
                str(job_id),
                kind,
                json.dumps(payload),
                priority,
                run_after,
                str(ingest_run_id) if ingest_run_id else None,
            ),
        )
    return job_id


def claim_one(
    conn: psycopg.Connection,
    kinds: Iterable[JobKind],
    *,
    worker_id: str | None = None,
) -> Job | None:
    """Claim one runnable job atomically (``SKIP LOCKED``).

    Returns ``None`` if no matching ``queued`` row is runnable right now.
    The selected row is marked ``running`` and its ``attempts`` counter
    is incremented; caller MUST later call :func:`mark_done` or
    :func:`mark_failed`. ``worker_id`` is only used for logging today.
    """

    kinds_list = list(kinds)
    if not kinds_list:
        raise ValueError("kinds must be non-empty")

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            WITH claimed AS (
              SELECT id
                FROM jobs
               WHERE status = 'queued'
                 AND run_after <= now()
                 AND kind = ANY(%s)
               ORDER BY priority ASC, run_after ASC
                 FOR UPDATE SKIP LOCKED
               LIMIT 1
            )
            UPDATE jobs j
               SET status = 'running',
                   attempts = j.attempts + 1,
                   updated_at = now()
              FROM claimed
             WHERE j.id = claimed.id
           RETURNING j.id, j.job_id, j.kind, j.payload, j.priority,
                     j.attempts, j.run_after, j.ingest_run_id
            """,
            (kinds_list,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return Job(
        id=row["id"],
        job_id=row["job_id"],
        kind=row["kind"],
        payload=row["payload"] or {},
        priority=row["priority"],
        attempts=row["attempts"],
        run_after=row["run_after"],
        ingest_run_id=row["ingest_run_id"],
    )


def mark_done(conn: psycopg.Connection, job_id: uuid.UUID) -> None:
    """Transition a job from ``running`` to ``done``."""

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
               SET status = 'done',
                   updated_at = now(),
                   last_error = NULL
             WHERE job_id = %s
            """,
            (str(job_id),),
        )


def mark_failed(
    conn: psycopg.Connection,
    job_id: uuid.UUID,
    *,
    error: str,
    max_attempts: int = 5,
) -> None:
    """Mark a job failed; promote to ``dead_letter`` after ``max_attempts``.

    On each failure the job is re-queued with exponential backoff
    (``run_after = now() + (attempts^2) seconds``) until ``attempts``
    reaches ``max_attempts``, at which point it transitions terminally
    to ``dead_letter``.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
               SET status = CASE
                      WHEN attempts >= %s THEN 'dead_letter'
                      ELSE 'queued'
                   END,
                   last_error = %s,
                   run_after = CASE
                      WHEN attempts >= %s THEN run_after
                      ELSE now() + (attempts * attempts || ' seconds')::interval
                   END,
                   updated_at = now()
             WHERE job_id = %s
            """,
            (max_attempts, error, max_attempts, str(job_id)),
        )
