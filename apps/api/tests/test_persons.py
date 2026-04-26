"""Tests for GET /persons/{person_id}."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import app
from api.routers.persons import get_person_repository


class _StubRepo:
    def __init__(self, card: dict | None) -> None:
        self.card = card

    def fetch(self, person_id):  # noqa: ARG002
        return self.card


def test_persons_get_returns_404_when_missing() -> None:
    app.dependency_overrides[get_person_repository] = lambda: _StubRepo(None)
    try:
        with TestClient(app) as c:
            r = c.get(f"/persons/{uuid4()}")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_person_repository, None)


def test_persons_get_returns_card_when_found() -> None:
    card = {"person_id": str(uuid4()), "hebrew_name": "Demo"}
    app.dependency_overrides[get_person_repository] = lambda: _StubRepo(card)
    try:
        with TestClient(app) as c:
            r = c.get(f"/persons/{card['person_id']}")
        assert r.status_code == 200
        assert r.json() == card
    finally:
        app.dependency_overrides.pop(get_person_repository, None)
