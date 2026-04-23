"""civic_archival — Phase 2 archival service.

See `services/archival/README.md` and the Phase-2 plan for the full contract.
Core entry points:

* :class:`civic_archival.fetcher.Fetcher` — polite httpx wrapper.
* :func:`civic_archival.archiver.archive_payload` — idempotent write to MinIO
  + ``raw_fetch_objects`` insert keyed on ``content_sha256``.
"""

from __future__ import annotations

from .archiver import ArchiveRecord, archive_payload
from .fetcher import FetchResult, Fetcher, fetch

__all__ = [
    "ArchiveRecord",
    "FetchResult",
    "Fetcher",
    "archive_payload",
    "fetch",
]
