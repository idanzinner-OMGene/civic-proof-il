"""Postgres client helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Callable

import psycopg

from ..settings import get_settings


def _build_connect() -> Callable[[], psycopg.Connection]:
    """Return a zero-arg callable that opens a new psycopg connection.

    Wrapped in a factory so tests can monkey-patch :func:`get_pg_connection`
    without reaching across module state.
    """

    settings = get_settings()
    conninfo = (
        f"host={settings.postgres_host} "
        f"port={settings.postgres_port} "
        f"dbname={settings.postgres_db} "
        f"user={settings.postgres_user} "
        f"password={settings.postgres_password}"
    )

    def _connect() -> psycopg.Connection:
        return psycopg.connect(conninfo)

    return _connect


@lru_cache
def _connector() -> Callable[[], psycopg.Connection]:
    return _build_connect()


def get_pg_connection() -> psycopg.Connection:
    """Open a new Postgres connection using cached settings."""

    return _connector()()


def ping_postgres() -> bool:
    """Return True if a simple ``SELECT 1`` round-trip succeeds."""

    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False
