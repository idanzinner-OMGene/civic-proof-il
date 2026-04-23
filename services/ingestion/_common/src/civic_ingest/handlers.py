"""Registry of job handlers.

Each adapter package imports :func:`register` at module load time and
binds a callable of shape ``callable(job) -> None`` for whichever job
``kind`` / ``payload["adapter"]`` pair it owns.

The worker calls :func:`dispatch`; adapters own everything else.
"""

from __future__ import annotations

from typing import Callable

__all__ = ["JobHandler", "dispatch", "register"]


JobHandler = Callable[["object"], None]

_REGISTRY: dict[tuple[str, str | None], JobHandler] = {}


def register(kind: str, *, adapter: str | None = None):
    """Decorator / callable — register a handler for ``kind`` + ``adapter``.

    If ``adapter`` is ``None`` the handler is the default for that
    ``kind``. Adapter-specific handlers win over defaults.
    """

    def _decorator(fn: JobHandler) -> JobHandler:
        _REGISTRY[(kind, adapter)] = fn
        return fn

    return _decorator


def dispatch(job) -> None:
    """Look up and run a handler for ``job``; raise if none registered."""

    adapter = None
    if isinstance(job.payload, dict):
        adapter = job.payload.get("adapter")

    handler = _REGISTRY.get((job.kind, adapter)) or _REGISTRY.get((job.kind, None))
    if handler is None:
        raise LookupError(
            f"no handler registered for kind={job.kind!r} adapter={adapter!r}"
        )
    handler(job)


def clear_registry() -> None:
    """Testing hook — wipe the registry between tests."""

    _REGISTRY.clear()
