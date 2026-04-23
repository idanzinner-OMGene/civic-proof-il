"""Postgres client factory + readiness probe.

Exposes both sync (:class:`psycopg.Connection`) and async
(:class:`psycopg.AsyncConnection`) entry points. The env contract is the
one defined in :class:`civic_common.settings.Settings` — nothing else.
"""

from __future__ import annotations

import psycopg

from civic_common.settings import get_settings

__all__ = [
    "build_conninfo",
    "make_async_connection",
    "make_connection",
    "ping",
]


def build_conninfo() -> str:
    """Return a libpq conninfo string built from current settings."""

    s = get_settings()
    return (
        f"host={s.postgres_host} "
        f"port={s.postgres_port} "
        f"dbname={s.postgres_db} "
        f"user={s.postgres_user} "
        f"password={s.postgres_password}"
    )


def make_connection() -> psycopg.Connection:
    """Open a new synchronous Postgres connection."""

    return psycopg.connect(build_conninfo())


async def make_async_connection() -> psycopg.AsyncConnection:
    """Open a new async Postgres connection.

    Note: returns an already-opened connection; caller is responsible for
    awaiting ``conn.close()`` or using ``async with``.
    """

    return await psycopg.AsyncConnection.connect(build_conninfo())


def ping() -> bool:
    """Return ``True`` iff ``SELECT 1`` round-trips cleanly."""

    try:
        with make_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False
