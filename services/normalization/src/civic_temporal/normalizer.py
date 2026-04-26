"""Deterministic temporal normalizer.

``normalize_time_scope(phrase, *, language, reference_date=None)`` returns
a :class:`civic_ontology.TimeScope` (``start``, ``end``, ``granularity``).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Literal

from civic_ontology.models.common import TimeScope

from .knesset_terms import term_by_number

Language = Literal["he", "en"]

__all__ = ["TimeScope", "normalize_time_scope"]


_ISO_DATE = re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})$")
_YEAR = re.compile(r"(?<!\d)(?P<y>(?:19|20)\d{2})(?!\d)")
_HE_TERM = re.compile(r"כנסת(?:\s+ה[-]?)?\s*(?P<n>\d{1,2})")
_EN_TERM = re.compile(
    r"(?P<n>\d{1,2})(?:st|nd|rd|th)?\s+[Kk]nesset",
)
_HE_MONTHS = {
    "ינואר": 1,
    "פברואר": 2,
    "מרץ": 3,
    "אפריל": 4,
    "מאי": 5,
    "יוני": 6,
    "יולי": 7,
    "אוגוסט": 8,
    "ספטמבר": 9,
    "אוקטובר": 10,
    "נובמבר": 11,
    "דצמבר": 12,
}
_HE_MONTH = re.compile(
    r"(?P<m>" + "|".join(_HE_MONTHS.keys()) + r")\s+(?P<y>(?:19|20)\d{2})"
)
_HE_LAST_YEAR = re.compile(r"בשנה\s+שעברה")
_HE_LAST_TERM = re.compile(r"(?:ה)?קדנציה\s+הקודמת")
_EN_LAST_YEAR = re.compile(r"\blast\s+year\b", re.IGNORECASE)
_EN_LAST_TERM = re.compile(r"\blast\s+term\b", re.IGNORECASE)


def _unknown() -> TimeScope:
    return TimeScope(start=None, end=None, granularity="unknown")


def _year_bounds(year: int) -> TimeScope:
    return TimeScope(
        start=f"{year:04d}-01-01T00:00:00+00:00",
        end=f"{year:04d}-12-31T23:59:59+00:00",
        granularity="year",
    )


def _month_bounds(year: int, month: int) -> TimeScope:
    if month == 12:
        next_start = date(year + 1, 1, 1)
    else:
        next_start = date(year, month + 1, 1)
    end = next_start - timedelta(days=1)
    return TimeScope(
        start=f"{year:04d}-{month:02d}-01T00:00:00+00:00",
        end=f"{end.year:04d}-{end.month:02d}-{end.day:02d}T23:59:59+00:00",
        granularity="month",
    )


def _day(year: int, month: int, day: int) -> TimeScope:
    return TimeScope(
        start=f"{year:04d}-{month:02d}-{day:02d}T00:00:00+00:00",
        end=f"{year:04d}-{month:02d}-{day:02d}T23:59:59+00:00",
        granularity="day",
    )


def _term_scope(n: int) -> TimeScope | None:
    term = term_by_number(n)
    if term is None:
        return None
    start = f"{term.start_iso}T00:00:00+00:00"
    end = f"{term.end_iso}T23:59:59+00:00" if term.end_iso else None
    return TimeScope(start=start, end=end, granularity="term")


def normalize_time_scope(
    phrase: str | None,
    *,
    language: Language = "he",
    reference_date: date | None = None,
) -> TimeScope:
    """Return a :class:`TimeScope` for ``phrase``.

    If ``phrase`` is empty or cannot be normalized, returns an
    ``"unknown"`` granularity scope with null bounds. Never raises.
    """

    if not phrase:
        return _unknown()
    text = phrase.strip()
    if not text:
        return _unknown()

    m = _ISO_DATE.match(text)
    if m:
        return _day(int(m["y"]), int(m["m"]), int(m["d"]))

    m = _HE_MONTH.search(text)
    if m:
        return _month_bounds(int(m["y"]), _HE_MONTHS[m["m"]])

    m = _HE_TERM.search(text)
    if m:
        scope = _term_scope(int(m["n"]))
        if scope is not None:
            return scope

    m = _EN_TERM.search(text)
    if m:
        scope = _term_scope(int(m["n"]))
        if scope is not None:
            return scope

    ref = reference_date or date.today()
    if _HE_LAST_YEAR.search(text) or _EN_LAST_YEAR.search(text):
        return _year_bounds(ref.year - 1)
    if _HE_LAST_TERM.search(text) or _EN_LAST_TERM.search(text):
        current_term = None
        for t in term_by_number.__globals__["KNESSET_TERMS"]:
            start = date.fromisoformat(t.start_iso)
            end = date.fromisoformat(t.end_iso) if t.end_iso else ref
            if start <= ref <= end:
                current_term = t
                break
        if current_term and current_term.number > 1:
            scope = _term_scope(current_term.number - 1)
            if scope is not None:
                return scope

    m = _YEAR.search(text)
    if m:
        return _year_bounds(int(m["y"]))

    return _unknown()
