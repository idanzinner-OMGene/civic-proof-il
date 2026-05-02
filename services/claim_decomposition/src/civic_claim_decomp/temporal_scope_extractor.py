"""Temporal scope extractor.

Provides two utilities for the declaration layer:

1. :func:`extract_utterance_time` — scans raw utterance text for a temporal
   anchor and returns a best-effort ``datetime`` that can populate
   ``Declaration.utterance_time`` when no explicit timestamp is available
   from the source metadata.

2. :func:`extract_time_scope` — thin wrapper around
   :func:`civic_temporal.normalize_time_scope` that accepts the raw
   ``time_phrase`` string extracted by the decomposition rules.

Both functions are **deterministic and side-effect-free**. They delegate the
actual temporal parsing to ``civic_temporal``; this module is only the
declaration-layer glue.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from civic_temporal import normalize_time_scope
from civic_ontology.models.common import TimeScope

Language = Literal["he", "en"]

__all__ = [
    "extract_utterance_time",
    "extract_time_scope",
]

# Lightweight year-extraction pattern — does not need to be as thorough as
# the civic_temporal normalizer because we only want a rough anchor datetime.
_YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")

# Hebrew and English ISO-8601 date-like patterns that appear in transcripts.
_ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def extract_utterance_time(
    utterance_text: str,
    language: Language = "he",
) -> datetime | None:
    """Return a best-effort ``datetime`` extracted from raw utterance text.

    Priority order:

    1. ISO-8601 date literal inside the text (``YYYY-MM-DD``).
    2. Four-digit year anywhere in the text → January 1st of that year (UTC).

    Returns ``None`` when no temporal cue is found so the caller can leave
    ``Declaration.utterance_time`` as ``None`` rather than fabricating a date.
    """
    text = utterance_text.strip()

    m = _ISO_DATE_RE.search(text)
    if m:
        try:
            return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    m = _YEAR_RE.search(text)
    if m:
        year = int(m.group(1))
        return datetime(year, 1, 1, tzinfo=timezone.utc)

    return None


def extract_time_scope(
    time_phrase: str | None,
    language: Language = "he",
) -> TimeScope:
    """Normalize a raw time phrase from decomposition rules into a ``TimeScope``.

    Delegates entirely to :func:`civic_temporal.normalize_time_scope`; exists
    as a named entry point so the declaration layer has a stable import path
    that does not need to know about ``civic_temporal`` directly.

    Returns an ``"unknown"`` granularity scope when ``time_phrase`` is ``None``
    or unrecognisable.
    """
    return normalize_time_scope(time_phrase, language=language)
