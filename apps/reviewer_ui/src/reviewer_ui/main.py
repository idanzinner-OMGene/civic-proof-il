"""Thin reviewer web UI (Phase 5) — proxies the civic API's review queue."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from uuid import UUID

import httpx
import structlog
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from civic_common.logging import configure_logging

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
_security = HTTPBasic()
log = structlog.get_logger()


def _api_base() -> str:
    return os.environ.get("CIVIC_API_BASE", "http://localhost:8000").rstrip("/")


def _verify_credentials(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """Verify HTTP Basic credentials against REVIEWER_UI_USER / REVIEWER_UI_PASSWORD env vars.

    Raises HTTP 503 if REVIEWER_UI_PASSWORD is not configured (fail-safe: no
    unguarded deployment).  Uses secrets.compare_digest to prevent timing attacks.
    """
    expected_user = os.environ.get("REVIEWER_UI_USER", "reviewer").encode()
    expected_pass = os.environ.get("REVIEWER_UI_PASSWORD", "").encode()
    if not expected_pass:
        raise HTTPException(
            status_code=503,
            detail="REVIEWER_UI_PASSWORD is not configured",
        )
    user_ok = secrets.compare_digest(credentials.username.encode(), expected_user)
    pass_ok = secrets.compare_digest(credentials.password.encode(), expected_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="civic-proof-il reviewer", version="0.0.0")

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/", response_class=HTMLResponse, name="queue")
    def queue(
        request: Request,
        kind_filter: str | None = None,
        _user: str = Depends(_verify_credentials),
    ) -> object:
        with httpx.Client(timeout=20.0) as c:
            r = c.get(f"{_api_base()}/review/tasks", params={"limit": 100})
            r.raise_for_status()
        tasks: list[dict] = r.json().get("tasks", [])
        if kind_filter:
            tasks = [row for row in tasks if row.get("kind") == kind_filter]
        return TEMPLATES.TemplateResponse(
            request,
            "queue.html",
            {
                "tasks": tasks,
                "kind_filter": kind_filter,
                "api_base": _api_base(),
            },
        )

    @app.get("/conflicts", response_class=HTMLResponse, name="conflicts")
    def conflicts(
        request: Request,
        _user: str = Depends(_verify_credentials),
    ) -> object:
        with httpx.Client(timeout=20.0) as c:
            r = c.get(f"{_api_base()}/review/tasks", params={"limit": 100})
            r.raise_for_status()
        tasks = [t for t in r.json().get("tasks", []) if t.get("kind") == "conflict"]
        return TEMPLATES.TemplateResponse(
            request,
            "queue.html",
            {
                "tasks": tasks,
                "kind_filter": "conflict",
                "api_base": _api_base(),
            },
        )

    @app.get("/tasks/{task_id}", response_class=HTMLResponse, name="task_detail")
    def task_detail(
        request: Request,
        task_id: str,
        _user: str = Depends(_verify_credentials),
    ) -> object:
        with httpx.Client(timeout=20.0) as c:
            r = c.get(f"{_api_base()}/review/tasks", params={"limit": 200})
            r.raise_for_status()
        tasks = r.json().get("tasks", [])
        task = next((t for t in tasks if t.get("task_id") == task_id), None)
        if task is None:
            return TEMPLATES.TemplateResponse(
                request,
                "not_found.html",
                {"task_id": task_id},
                status_code=404,
            )
        return TEMPLATES.TemplateResponse(
            request,
            "task_detail.html",
            {
                "task": task,
                "api_base": _api_base(),
                "payload_json": json.dumps(
                    task.get("payload"), ensure_ascii=False, indent=2, default=str
                ),
            },
        )

    def _proxy_result(label: str, r: httpx.Response) -> HTMLResponse:
        body = f"<p><strong>{label}</strong> — HTTP {r.status_code}</p><pre>{_html_escape(r.text[:2000])}</pre>"
        return HTMLResponse(body, status_code=200 if r.is_success else 502)

    @app.post("/proxy/tasks/{task_id}/resolve", response_class=HTMLResponse)
    def proxy_resolve(
        task_id: str,
        decision: str = Form(...),
        reviewer_id: str = Form(...),
        notes: str | None = Form(None),
        _user: str = Depends(_verify_credentials),
    ) -> HTMLResponse:
        payload = {
            "decision": decision,
            "reviewer_id": reviewer_id,
            "notes": notes.strip() if notes else None,
        }
        with httpx.Client(timeout=30.0) as c:
            r = c.post(
                f"{_api_base()}/review/tasks/{task_id}/resolve",
                json=payload,
            )
        return _proxy_result("resolve", r)

    @app.post("/proxy/tasks/{task_id}/relink-entity", response_class=HTMLResponse)
    def proxy_relink(
        task_id: str,
        candidate_id: str = Form(...),
        canonical_entity_id: str = Form(...),
        entity_kind: str = Form(...),
        reviewer_id: str = Form(...),
        notes: str | None = Form(None),
        _user: str = Depends(_verify_credentials),
    ) -> HTMLResponse:
        try:
            UUID(candidate_id)
            UUID(canonical_entity_id)
        except ValueError:
            return HTMLResponse("<p class='err'>מזהי UUID לא תקינים</p>", status_code=400)
        payload = {
            "candidate_id": candidate_id,
            "canonical_entity_id": canonical_entity_id,
            "entity_kind": entity_kind,
            "reviewer_id": reviewer_id,
            "notes": notes.strip() if notes else None,
        }
        with httpx.Client(timeout=30.0) as c:
            r = c.post(
                f"{_api_base()}/review/tasks/{task_id}/relink-entity",
                json=payload,
            )
        return _proxy_result("relink-entity", r)

    @app.post("/proxy/tasks/{task_id}/confirm-evidence", response_class=HTMLResponse)
    def proxy_confirm(
        task_id: str,
        span_ids: str = Form(...),
        reviewer_id: str = Form(...),
        _user: str = Depends(_verify_credentials),
    ) -> HTMLResponse:
        ids = [s.strip() for s in span_ids.replace("\n", ",").split(",") if s.strip()]
        if not ids:
            return HTMLResponse("<p class='err'>נא להזין span_ids מופרדים בפסיקים</p>", status_code=400)
        payload = {"span_ids": ids, "reviewer_id": reviewer_id}
        with httpx.Client(timeout=30.0) as c:
            r = c.post(
                f"{_api_base()}/review/tasks/{task_id}/confirm-evidence",
                json=payload,
            )
        return _proxy_result("confirm-evidence", r)

    return app


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


app = create_app()
