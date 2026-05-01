from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from reviewer_ui.main import app

_AUTH = ("reviewer", os.environ.get("REVIEWER_UI_PASSWORD", "test_secret"))


def test_healthz_requires_no_auth():
    with TestClient(app) as t:
        r = t.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_queue_requires_auth_returns_401():
    with TestClient(app, raise_server_exceptions=False) as t:
        r = t.get("/")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_queue_page_uses_tasks_from_api():
    with patch("reviewer_ui.main.httpx.Client") as c:
        inst = MagicMock()
        c.return_value.__enter__.return_value = inst
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_resp.json = lambda: {"tasks": []}
        inst.get.return_value = mock_resp
        with TestClient(app) as t:
            r = t.get("/", auth=_AUTH)
    assert r.status_code == 200
    assert "תור" in r.text


def test_proxy_resolve_posts_to_api():
    task_id = "00000000-0000-4000-8000-000000000001"
    with patch("reviewer_ui.main.httpx.Client") as c:
        inst = MagicMock()
        c.return_value.__enter__.return_value = inst
        post_resp = MagicMock()
        post_resp.is_success = True
        post_resp.status_code = 200
        post_resp.text = '{"ok": true}'
        inst.post.return_value = post_resp
        with TestClient(app) as t:
            r = t.post(
                f"/proxy/tasks/{task_id}/resolve",
                data={
                    "decision": "approve",
                    "reviewer_id": "alice",
                    "notes": "ok",
                },
                auth=_AUTH,
            )
    assert r.status_code == 200
    inst.post.assert_called_once()
    args, kwargs = inst.post.call_args
    assert f"/review/tasks/{task_id}/resolve" in args[0]
    assert kwargs["json"]["decision"] == "approve"
    assert kwargs["json"]["reviewer_id"] == "alice"


def test_proxy_confirm_posts_span_ids():
    task_id = "00000000-0000-4000-8000-000000000002"
    with patch("reviewer_ui.main.httpx.Client") as c:
        inst = MagicMock()
        c.return_value.__enter__.return_value = inst
        post_resp = MagicMock()
        post_resp.is_success = True
        post_resp.status_code = 200
        post_resp.text = "{}"
        inst.post.return_value = post_resp
        with TestClient(app) as t:
            r = t.post(
                f"/proxy/tasks/{task_id}/confirm-evidence",
                data={"span_ids": "a, b", "reviewer_id": "bob"},
                auth=_AUTH,
            )
    assert r.status_code == 200
    _args, kwargs = inst.post.call_args
    assert kwargs["json"]["span_ids"] == ["a", "b"]
    assert kwargs["json"]["reviewer_id"] == "bob"
