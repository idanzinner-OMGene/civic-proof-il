"""Tests for the review-task router."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import app
from api.routers.review import get_review_repository


class _StubRepo:
    def __init__(self) -> None:
        self.tasks = [{"task_id": str(uuid4()), "status": "open"}]
        self.resolved: dict | None = None

    def list_open_tasks(self, *, limit=50):  # noqa: ARG002
        return self.tasks

    def resolve_task(self, task_id, *, decision, reviewer_id, notes):
        self.resolved = {
            "task_id": str(task_id),
            "decision": decision,
            "reviewer_id": reviewer_id,
            "notes": notes,
            "status": "resolved",
        }
        return self.resolved


def test_review_tasks_lists_open_tasks() -> None:
    repo = _StubRepo()
    app.dependency_overrides[get_review_repository] = lambda: repo
    try:
        with TestClient(app) as c:
            r = c.get("/review/tasks")
        assert r.status_code == 200
        assert r.json()["tasks"] == repo.tasks
    finally:
        app.dependency_overrides.pop(get_review_repository, None)


def test_review_resolve_records_decision_and_reviewer() -> None:
    repo = _StubRepo()
    app.dependency_overrides[get_review_repository] = lambda: repo
    tid = uuid4()
    try:
        with TestClient(app) as c:
            r = c.post(
                f"/review/tasks/{tid}/resolve",
                json={"decision": "approve", "reviewer_id": "rev_1", "notes": "ok"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] == "approve"
        assert body["reviewer_id"] == "rev_1"
        assert body["status"] == "resolved"
    finally:
        app.dependency_overrides.pop(get_review_repository, None)


def test_review_resolve_404_when_task_missing() -> None:
    class _NullRepo(_StubRepo):
        def resolve_task(self, *a, **kw):  # noqa: ARG002
            return None

    app.dependency_overrides[get_review_repository] = lambda: _NullRepo()
    try:
        with TestClient(app) as c:
            r = c.post(
                f"/review/tasks/{uuid4()}/resolve",
                json={"decision": "approve", "reviewer_id": "rev_1"},
            )
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_review_repository, None)
