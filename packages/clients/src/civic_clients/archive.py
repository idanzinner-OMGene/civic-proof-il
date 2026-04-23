"""MinIO / S3 archive URI convention.

The single authoritative spec for the URI format is
``docs/conventions/archive-paths.md``. This module is the code side of
that contract: build + parse + hash helpers that every ingestion worker
and every API consumer must use so archive layouts never drift.

URI shape::

    s3://<bucket>/<source_family>/<YYYY>/<MM>/<DD>/<sha256>.<ext>

* ``bucket`` — value of the ``MINIO_BUCKET_ARCHIVE`` env var.
* ``source_family`` — one of :data:`SOURCE_FAMILIES` (mirrors the
  ``services/ingestion/*`` subdirectories from Phase 0).
* ``YYYY/MM/DD`` — UTC calendar date of ``captured_at``.
* ``sha256`` — hex-lowercase SHA-256 of the raw bytes.
* ``ext`` — lowercase, no leading dot.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

__all__ = [
    "ArchiveCoord",
    "SOURCE_FAMILIES",
    "build_archive_uri",
    "content_sha256",
    "parse_archive_uri",
]


SOURCE_FAMILIES: frozenset[str] = frozenset({"knesset", "gov_il", "elections"})
"""Allowed ``source_family`` path segments.

Kept in sync with the Phase-0 ``services/ingestion/*`` subdirectories.
"""


@dataclass(frozen=True, slots=True)
class ArchiveCoord:
    """Parsed components of an archive URI.

    All fields are canonical (lowercase, zero-padded) — :func:`parse_archive_uri`
    raises rather than producing a coord that round-trips to a different URI.
    """

    bucket: str
    source_family: str
    year: int
    month: int
    day: int
    sha256: str
    extension: str


_URI_RE = re.compile(
    r"^s3://(?P<bucket>[a-z0-9][a-z0-9.\-]{1,62})/"
    r"(?P<source_family>[a-z_]+)/"
    r"(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/"
    r"(?P<sha256>[0-9a-f]{64})\.(?P<extension>[a-z0-9]+)$"
)


def content_sha256(content: bytes) -> str:
    """Return the hex-lowercase SHA-256 of ``content``.

    Centralised so every caller agrees on algorithm + encoding.
    """

    return hashlib.sha256(content).hexdigest()


def _normalize_extension(extension: str) -> str:
    ext = extension.strip().lstrip(".").lower()
    if not ext:
        raise ValueError("extension must be non-empty")
    if not re.fullmatch(r"[a-z0-9]+", ext):
        raise ValueError(
            f"extension {extension!r} must be alphanumeric after normalization"
        )
    return ext


def build_archive_uri(
    source_family: str,
    captured_at: datetime,
    content: bytes,
    extension: str,
) -> str:
    """Return the canonical archive URI for ``content``.

    Strict validation:

    * ``source_family`` must be in :data:`SOURCE_FAMILIES`.
    * ``captured_at`` must be timezone-aware.
    * ``extension`` is normalised (leading ``.`` stripped, lowercased).

    The bucket is taken from the currently-configured
    :class:`civic_common.settings.Settings`, so changing
    ``MINIO_BUCKET_ARCHIVE`` flips every freshly built URI.
    """

    from civic_common.settings import get_settings

    if source_family not in SOURCE_FAMILIES:
        raise ValueError(
            f"source_family {source_family!r} not in {sorted(SOURCE_FAMILIES)!r}"
        )
    if captured_at.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")

    ext = _normalize_extension(extension)
    utc = captured_at.astimezone(timezone.utc)
    digest = content_sha256(content)
    bucket = get_settings().minio_bucket_archive

    return (
        f"s3://{bucket}/{source_family}/"
        f"{utc.year:04d}/{utc.month:02d}/{utc.day:02d}/"
        f"{digest}.{ext}"
    )


def parse_archive_uri(uri: str) -> ArchiveCoord:
    """Parse ``uri`` into an :class:`ArchiveCoord`; raise on any mismatch.

    This is the inverse of :func:`build_archive_uri` — any URI produced
    by ``build_archive_uri`` parses cleanly, and any URI that parses
    cleanly survives a build/parse round-trip.
    """

    m = _URI_RE.match(uri)
    if not m:
        raise ValueError(f"not a canonical archive URI: {uri!r}")

    source_family = m.group("source_family")
    if source_family not in SOURCE_FAMILIES:
        raise ValueError(
            f"source_family {source_family!r} not in {sorted(SOURCE_FAMILIES)!r}"
        )

    year = int(m.group("year"))
    month = int(m.group("month"))
    day = int(m.group("day"))
    try:
        datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"invalid calendar date in URI {uri!r}") from exc

    return ArchiveCoord(
        bucket=m.group("bucket"),
        source_family=source_family,
        year=year,
        month=month,
        day=day,
        sha256=m.group("sha256"),
        extension=m.group("extension"),
    )
