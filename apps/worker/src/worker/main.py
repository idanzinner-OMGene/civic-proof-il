from __future__ import annotations

import signal
import time
from typing import Callable

import structlog

from .settings import get_settings

log = structlog.get_logger()

_should_exit = False

_DISPATCHABLE_KINDS = ("fetch", "parse", "normalize", "upsert")


def _request_exit(signum, frame) -> None:  # pragma: no cover
    global _should_exit
    _should_exit = True


def run_once() -> dict:
    """Single tick of the worker loop.

    When a live Postgres connection is available (production /
    compose / `ENV=ci`) this attempts to claim one job from the
    Phase-2 ``jobs`` queue via ``FOR UPDATE SKIP LOCKED`` and dispatch
    it. In environments without a reachable DB (unit tests at import
    time) the tick is a no-op and the function simply returns a status
    dict — this preserves the Phase-0 smoke-test contract.
    """

    settings = get_settings()

    status: dict = {"env": settings.env, "ok": True}
    try:
        from civic_clients.postgres import make_connection
        from civic_ingest.queue import Job, claim_one, mark_done, mark_failed
    except ImportError as exc:  # pragma: no cover - only hit in minimal envs
        log.info(
            "worker_tick",
            env=settings.env,
            mode="stub",
            reason=f"imports unavailable: {exc}",
        )
        return status

    try:
        conn = make_connection()
    except Exception as exc:
        log.info(
            "worker_tick",
            env=settings.env,
            mode="stub",
            reason=f"postgres unavailable: {exc.__class__.__name__}",
        )
        return status

    try:
        job = claim_one(conn, kinds=_DISPATCHABLE_KINDS)
        conn.commit()
        if job is None:
            log.info("worker_tick", env=settings.env, mode="live", job=None)
            status["job"] = None
            return status

        log.info(
            "worker_tick",
            env=settings.env,
            mode="live",
            job_id=str(job.job_id),
            kind=job.kind,
        )
        try:
            _dispatch(job)
            mark_done(conn, job.job_id)
            conn.commit()
            status["job"] = str(job.job_id)
            status["job_status"] = "done"
        except Exception as exc:
            conn.rollback()
            mark_failed(conn, job.job_id, error=repr(exc))
            conn.commit()
            status["job"] = str(job.job_id)
            status["job_status"] = "failed"
    finally:
        conn.close()

    return status


def _dispatch(job) -> None:
    """Dispatch a claimed job to its adapter.

    Phase-2 keeps this thin: the actual per-adapter handler registry
    lives inside each ``civic_ingest_<adapter>`` package. The worker
    only knows the four generic kinds.
    """

    from civic_ingest.handlers import dispatch as _dispatch_impl  # type: ignore

    _dispatch_impl(job)


def run_forever(sleep_fn: Callable[[float], None] = time.sleep) -> None:
    signal.signal(signal.SIGTERM, _request_exit)
    signal.signal(signal.SIGINT, _request_exit)
    settings = get_settings()
    log.info("worker_start", tick_seconds=settings.worker_tick_seconds)
    while not _should_exit:
        run_once()
        sleep_fn(settings.worker_tick_seconds)
    log.info("worker_stop")


if __name__ == "__main__":
    run_forever()
