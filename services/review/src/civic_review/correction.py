"""Entity-resolution corrections on ``entity_candidates`` (Phase 5)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg

__all__ = ["RelinkRequest", "apply_entity_relink", "relink_by_task_id"]


@dataclass(frozen=True, slots=True)
class RelinkRequest:
    """Point an ambiguous row at a canonical entity (person/party/…)."""

    candidate_id: UUID
    canonical_entity_id: UUID
    entity_kind: str  # person | party | office | committee | bill
    reviewer_id: str


def apply_entity_relink(
    conn: psycopg.Connection, req: RelinkRequest
) -> tuple[bool, str | None]:
    """``UPDATE`` the polymorphic link; return ``(True, None)`` on success."""

    if req.entity_kind not in {"person", "party", "office", "committee", "bill"}:
        return False, "invalid entity_kind"
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE entity_candidates
            SET
              canonical_entity_id = %s,
              entity_kind = %s
            WHERE candidate_id = %s
            RETURNING id
            """,
            (str(req.canonical_entity_id), req.entity_kind, str(req.candidate_id)),
        )
        row = cur.fetchone()
    if row is None:
        return False, "candidate not found"
    return True, None


def relink_by_task_id(
    conn: psycopg.Connection,
    *,
    task_id: UUID,
    req: RelinkRequest,
) -> bool:
    """Convenience: verify the task is ``entity_resolution`` and apply relink.

    The task ``payload`` must include ``"candidate_id"`` matching
    :attr:`RelinkRequest.candidate_id` so reviewers cannot re-point an
    unrelated row.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, kind, payload FROM review_tasks
            WHERE task_id = %s
            """,
            (str(task_id),),
        )
        row = cur.fetchone()
    if row is None:
        return False
    _id, kind, raw_payload = row
    if kind != "entity_resolution":
        return False
    payload: dict[str, Any]
    if isinstance(raw_payload, dict):
        payload = raw_payload
    else:
        payload = json.loads(raw_payload)
    want = str(payload.get("candidate_id", ""))
    if want != str(req.candidate_id):
        return False
    ok, _ = apply_entity_relink(conn, req)
    return ok
