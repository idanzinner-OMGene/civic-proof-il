"""civic_temporal — temporal normalization for Hebrew + English statements.

Emits :class:`civic_ontology.TimeScope`-shaped objects (``start``, ``end``,
``granularity``). Handles:

* ISO-8601 fragments (``2024-01-15`` → day granularity, exact match).
* Bare year (``2024`` / ``ב-2024``) → year granularity, Jan-1 … Dec-31.
* Hebrew month names (``ינואר 2024``) → month granularity.
* Knesset term phrases (``כנסת ה-25`` / ``the 25th Knesset``) → term granularity.
* Relative phrases (``בשנה שעברה`` / ``last year``) → year granularity
  relative to an injectable reference date.
* Unknown → ``"unknown"`` granularity with null bounds.

Knesset term boundaries live in :data:`KNESSET_TERMS`. Only the terms
covered by the Phase-2 KNS_Person cassette are represented; anything
outside that range falls back to ``unknown``.
"""

from __future__ import annotations

from .knesset_terms import KNESSET_TERMS, KnessetTerm
from .normalizer import TimeScope, normalize_time_scope

__all__ = ["KNESSET_TERMS", "KnessetTerm", "TimeScope", "normalize_time_scope"]
