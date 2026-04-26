"""civic_review — review queue + audit log MVP.

The service exposes a small Python surface that the FastAPI router
wires into:

* :class:`ReviewAction` — the five allowed actions per Phase-1
  migration 0002 (``approve``, ``reject``, ``relink``, ``annotate``,
  ``escalate``).
* :class:`ReviewTask` — a typed row from ``review_tasks``.
* :class:`PostgresReviewRepository` — the concrete repo that reads
  open tasks and writes both the task update AND an immutable
  ``review_actions`` audit-log row in a single transaction.
* :func:`open_review_task` — helper for the verdict engine that pushes
  a new task onto the queue when a verdict abstains.
"""

from __future__ import annotations

from .audit import ReviewAction, ReviewActionRecord
from .queue import PostgresReviewRepository, ReviewTask, open_review_task

__all__ = [
    "PostgresReviewRepository",
    "ReviewAction",
    "ReviewActionRecord",
    "ReviewTask",
    "open_review_task",
]
