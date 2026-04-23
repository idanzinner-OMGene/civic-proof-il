"""IngestRun context manager — Phase-2 lifecycle wrapper for ``ingest_runs``.

Usage::

    from civic_ingest.orchestrator import IngestRun

    with IngestRun(source_family="knesset") as run:
        # ... enqueue jobs ...
        run.add_stats({"fetched": 120, "upserted": 118})

The context manager inserts a row in ``ingest_runs`` on entry (status
``running``) and closes it on exit (``succeeded`` or ``failed`` depending
on whether an exception propagated).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import psycopg

from civic_clients.postgres import make_connection

__all__ = ["IngestRun"]


@dataclass(slots=True)
class IngestRun:
    source_family: str
    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    stats: dict[str, Any] = field(default_factory=dict)
    _db_id: int | None = field(default=None, init=False, repr=False)
    _conn: psycopg.Connection | None = field(default=None, init=False, repr=False)
    _owns_conn: bool = field(default=False, init=False, repr=False)

    def __enter__(self) -> "IngestRun":
        self._conn = make_connection()
        self._owns_conn = True
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingest_runs (run_id, source_family, status, stats)
                VALUES (%s, %s, 'running', '{}'::jsonb)
                RETURNING id
                """,
                (str(self.run_id), self.source_family),
            )
            self._db_id = cur.fetchone()[0]
        self._conn.commit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        status = "failed" if exc_type is not None else "succeeded"
        assert self._conn is not None
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE ingest_runs
                       SET status = %s,
                           finished_at = now(),
                           stats = %s::jsonb
                     WHERE run_id = %s
                    """,
                    (status, json.dumps(self.stats), str(self.run_id)),
                )
            self._conn.commit()
        finally:
            if self._owns_conn:
                self._conn.close()
                self._conn = None

    @property
    def db_id(self) -> int:
        if self._db_id is None:
            raise RuntimeError("IngestRun must be entered before accessing db_id")
        return self._db_id

    @property
    def connection(self) -> psycopg.Connection:
        if self._conn is None:
            raise RuntimeError("IngestRun must be entered before accessing connection")
        return self._conn

    def add_stats(self, update: dict[str, Any]) -> None:
        self.stats.update(update)
