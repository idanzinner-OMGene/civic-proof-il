"""Postgres client — thin re-export from :mod:`civic_clients.postgres`.

Legacy public names (``get_pg_connection``, ``ping_postgres``) are kept as
module-level aliases so the existing ``api.health`` readiness probes and
the ``apps/api/tests/test_health.py`` monkeypatches continue to work
unchanged.
"""

from __future__ import annotations

from civic_clients.postgres import (
    make_async_connection,
    make_connection,
    ping,
)

get_pg_connection = make_connection
ping_postgres = ping

__all__ = [
    "get_pg_connection",
    "make_async_connection",
    "make_connection",
    "ping",
    "ping_postgres",
]
