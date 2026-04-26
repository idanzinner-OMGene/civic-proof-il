"""Review task endpoints.

* ``GET  /review/tasks`` — list open tasks (abstained verdicts awaiting
  human review).
* ``POST /review/tasks/{task_id}/resolve`` — close a task with a
  reviewer decision and persist an audit-log row (see W3-C3).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

import psycopg
from civic_review import PostgresReviewRepository
from civic_review.correction import RelinkRequest, relink_by_task_id
from civic_review.evidence import append_span_confirmation
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/review", tags=["review"])


# The five audit-log actions enumerated in Phase-1 migration 0002's
# ``review_actions.action`` CHECK constraint (see civic_review.audit).
ReviewDecision = Literal["approve", "reject", "relink", "annotate", "escalate"]


class ReviewResolveRequest(BaseModel):
    decision: ReviewDecision
    reviewer_id: str = Field(..., min_length=1)
    notes: str | None = None


class RelinkEntityRequest(BaseModel):
    candidate_id: UUID
    canonical_entity_id: UUID
    entity_kind: Literal["person", "party", "office", "committee", "bill"]
    reviewer_id: str = Field(..., min_length=1)
    notes: str | None = None


class ConfirmEvidenceRequest(BaseModel):
    span_ids: list[str] = Field(..., min_length=1)
    reviewer_id: str = Field(..., min_length=1)


class ReviewRepository(Protocol):
    def list_open_tasks(self, *, limit: int = 50) -> list[dict[str, Any]]: ...

    def resolve_task(
        self,
        task_id: UUID,
        *,
        decision: str,
        reviewer_id: str,
        notes: str | None,
    ) -> dict[str, Any] | None: ...


class _EmptyReviewRepository:
    def list_open_tasks(self, *, limit: int = 50) -> list[dict[str, Any]]:  # noqa: ARG002
        return []

    def resolve_task(  # noqa: D401, ARG002
        self,
        task_id: UUID,
        *,
        decision: str,
        reviewer_id: str,
        notes: str | None,
    ) -> dict[str, Any] | None:
        return None


_default_repository: ReviewRepository = _EmptyReviewRepository()


def get_review_repository() -> ReviewRepository:
    return _default_repository


def set_review_repository(repo: ReviewRepository) -> None:
    global _default_repository
    _default_repository = repo


def _get_pg_connection(request: Request) -> psycopg.Connection:
    conn = getattr(request.app.state, "pg_connection", None)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="postgres not wired (API lifespan did not open a review connection)",
        )
    return conn


def reset_review_repository() -> None:
    """Restore the empty in-memory repository (used after lifespan shutdown)."""

    global _default_repository
    _default_repository = _EmptyReviewRepository()


@router.get("/tasks")
def list_review_tasks(
    repo: Annotated[ReviewRepository, Depends(get_review_repository)],
    limit: int = 50,
) -> dict[str, list[dict[str, Any]]]:
    return {"tasks": repo.list_open_tasks(limit=limit)}


@router.post("/tasks/{task_id}/resolve")
def resolve_review_task(
    task_id: UUID,
    body: ReviewResolveRequest,
    repo: Annotated[ReviewRepository, Depends(get_review_repository)],
) -> dict[str, Any]:
    resolved = repo.resolve_task(
        task_id,
        decision=body.decision,
        reviewer_id=body.reviewer_id,
        notes=body.notes,
    )
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="review task not found"
        )
    return resolved


@router.post("/tasks/{task_id}/relink-entity")
def relink_entity(
    task_id: UUID,
    body: RelinkEntityRequest,
    conn: Annotated[psycopg.Connection, Depends(_get_pg_connection)],
) -> dict[str, str]:
    """Update ``entity_candidates`` and close the task with a ``relink`` audit row."""

    req = RelinkRequest(
        candidate_id=body.candidate_id,
        canonical_entity_id=body.canonical_entity_id,
        entity_kind=body.entity_kind,
        reviewer_id=body.reviewer_id,
    )
    if not relink_by_task_id(conn, task_id=task_id, req=req):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="relink failed (task not found, wrong kind, or candidate mismatch)",
        )
    repo = _repo_from_conn(conn)
    out = repo.resolve_task(
        task_id,
        decision="relink",
        reviewer_id=body.reviewer_id,
        notes=body.notes,
    )
    if out is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"status": "ok"}


@router.post("/tasks/{task_id}/confirm-evidence")
def confirm_evidence(
    task_id: UUID,
    body: ConfirmEvidenceRequest,
    conn: Annotated[psycopg.Connection, Depends(_get_pg_connection)],
) -> dict[str, str]:
    """Append a non-terminal audit row confirming span IDs (does not close the task)."""

    repo = _repo_from_conn(conn)
    task = repo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    if not append_span_confirmation(
        conn,
        task=task,
        span_ids=body.span_ids,
        reviewer_id=body.reviewer_id,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="nothing to record")
    return {"status": "ok"}


def _repo_from_conn(conn: psycopg.Connection) -> PostgresReviewRepository:
    return PostgresReviewRepository(conn)
