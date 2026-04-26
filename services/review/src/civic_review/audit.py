"""Immutable audit-log entries for the review queue.

Every state transition on a review task records a row in
``review_actions`` (Phase-1 migration 0002). The CHECK constraint
limits ``action`` to the five values enumerated in :class:`ReviewAction`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RELINK = "relink"
    ANNOTATE = "annotate"
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class ReviewActionRecord:
    action_id: UUID
    task_id: int
    actor: str
    action: ReviewAction
    diff: dict[str, Any]
    created_at: datetime

    @classmethod
    def new(
        cls,
        *,
        task_id: int,
        actor: str,
        action: ReviewAction | str,
        diff: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> "ReviewActionRecord":
        from datetime import timezone

        return cls(
            action_id=uuid4(),
            task_id=task_id,
            actor=actor,
            action=ReviewAction(action),
            diff=dict(diff or {}),
            created_at=now or datetime.now(tz=timezone.utc),
        )
