from __future__ import annotations

import signal
import time
from typing import Callable

import structlog

from .settings import get_settings

log = structlog.get_logger()

_should_exit = False


def _request_exit(signum, frame) -> None:  # pragma: no cover
    global _should_exit
    _should_exit = True


def run_once() -> dict:
    """Single tick of the worker loop. Returns a status dict for tests."""
    settings = get_settings()
    log.info("worker_tick", env=settings.env)
    return {"env": settings.env, "ok": True}


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
