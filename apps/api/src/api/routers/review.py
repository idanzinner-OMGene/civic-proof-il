"""Review task endpoints.

* ``GET  /review/tasks`` — list open tasks (abstained verdicts awaiting
  human review).
* ``POST /review/tasks/{task_id}/resolve`` — close a task with a
  reviewer decision and persist an audit-log row (see W3-C3).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/review", tags=["review"])


# The five audit-log actions enumerated in Phase-1 migration 0002's
# ``review_actions.action`` CHECK constraint (see civic_review.audit).
ReviewDecision = Literal["approve", "reject", "relink", "annotate", "escalate"]


class ReviewResolveRequest(BaseModel):
    decision: ReviewDecision
    reviewer_id: str = Field(..., min_length=1)
    notes: str | None = None


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
