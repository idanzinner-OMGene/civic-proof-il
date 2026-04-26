"""Persistence helper: ``persist_statement`` writes one statement + its
decomposed claims into the ``statements`` / ``statement_claims`` tables
introduced in migration 0006.

Kept deliberately dependency-light so the API layer can call it
without importing the whole decomposer entry point. Callers pass
pre-decomposed claims (from :func:`decompose`) and a resolved
``CheckabilityInputs`` per claim.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import psycopg

from .decomposer import DecomposedClaim

__all__ = ["StatementRecord", "persist_statement"]


@dataclass(frozen=True, slots=True)
class StatementRecord:
    statement_id: uuid.UUID
    raw_text: str
    language: str
    speaker_hint: str | None = None
    source_url: str | None = None
    source_family: str | None = None
    metadata: Mapping[str, Any] | None = None


def persist_statement(
    pg_conn: psycopg.Connection,
    statement: StatementRecord,
    claims: Iterable[DecomposedClaim],
    checkability_by_claim: Mapping[uuid.UUID, str],
    time_scope_by_claim: Mapping[uuid.UUID, Mapping[str, Any]] | None = None,
) -> dict:
    """Insert one statement + N claims atomically.

    Returns a summary dict with counts suitable for logging.
    Raises :class:`psycopg.Error` on any DB failure; the caller is
    expected to wrap the whole call in a transaction so partial
    failures roll back cleanly.
    """

    time_scope_by_claim = dict(time_scope_by_claim or {})
    checkability_by_claim = dict(checkability_by_claim)
    summary = {"statement_id": str(statement.statement_id), "claims_persisted": 0}

    with pg_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO statements
              (statement_id, raw_text, language, speaker_hint,
               source_url, source_family, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (statement_id) DO NOTHING
            """,
            (
                str(statement.statement_id),
                statement.raw_text,
                statement.language,
                statement.speaker_hint,
                statement.source_url,
                statement.source_family,
                json.dumps(dict(statement.metadata or {})),
            ),
        )
        for claim in claims:
            cur.execute(
                """
                INSERT INTO statement_claims
                  (statement_id, claim_id, claim_type, checkability,
                   method, slots, time_scope)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                ON CONFLICT (statement_id, claim_id) DO NOTHING
                """,
                (
                    str(statement.statement_id),
                    str(claim.claim_id),
                    claim.claim_type,
                    checkability_by_claim.get(claim.claim_id, "non_checkable"),
                    claim.method,
                    json.dumps(claim.slots, default=str),
                    json.dumps(dict(time_scope_by_claim.get(claim.claim_id, {}))),
                ),
            )
            summary["claims_persisted"] += 1
    return summary
