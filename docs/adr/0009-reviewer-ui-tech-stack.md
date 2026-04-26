# ADR-0009: Reviewer UI stack (FastAPI + Jinja2 + HTMX)

## Status

Accepted — 2026-04-26

## Context

Phase 5 needs a small queue browser that lists review tasks, links to
detail pages, and documents the JSON bodies for
``POST /review/...`` operations.

## Decision

Ship ``apps/reviewer_ui`` as a second FastAPI app that server-side
renders Jinja2 templates and loads queue data from the main API
(``CIVIC_API_BASE``) via ``httpx``. HTMX is included for future
progressive enhancement; v1 is mostly read-only with operator copy/paste
for API calls.

## Consequences

* No Node/npm in the monorepo for the reviewer surface.
* The UI container depends on a healthy ``api`` service
  (``docker compose`` service ``reviewer_ui``).
