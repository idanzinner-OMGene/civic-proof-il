"""Shared structured logging configuration for civic-proof-il services.

Call ``configure_logging()`` once at process startup (in ``create_app()`` or
``run_forever()``).  After that, every service obtains a logger via::

    import structlog
    log = structlog.get_logger()

JSON output is emitted when ``ENV != 'dev'`` (i.e. in compose, CI, and
production).  Coloured console output is used during local development.

The stdlib root logger is bridged through structlog so that third-party
libraries (uvicorn, httpx, alembic, etc.) also emit structured events.
"""

from __future__ import annotations

import logging
import os

import structlog


def configure_logging() -> None:
    """Configure structlog for the current process.

    Safe to call multiple times — subsequent calls are no-ops if structlog is
    already configured (``cache_logger_on_first_use=True`` is set on the first
    call and the root handler is only replaced when the list is empty).
    """
    env = os.environ.get("ENV", "dev")
    log_level = logging.DEBUG if env == "dev" else logging.INFO

    shared_processors: list = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: structlog.types.Processor
    if env == "dev":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    else:
        root.handlers = [handler]
    root.setLevel(log_level)
