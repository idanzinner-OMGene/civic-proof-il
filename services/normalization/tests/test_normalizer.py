"""Tests for civic_temporal.normalize_time_scope."""

from __future__ import annotations

from datetime import date

from civic_temporal import normalize_time_scope


def test_empty_phrase_is_unknown() -> None:
    ts = normalize_time_scope("")
    assert ts.granularity == "unknown"
    assert ts.start is None and ts.end is None


def test_bare_year() -> None:
    ts = normalize_time_scope("2024")
    assert ts.granularity == "year"
    assert ts.start is not None and ts.start.startswith("2024-01-01")
    assert ts.end is not None and ts.end.startswith("2024-12-31")


def test_iso_day() -> None:
    ts = normalize_time_scope("2024-05-07")
    assert ts.granularity == "day"
    assert ts.start is not None and ts.start.startswith("2024-05-07")


def test_hebrew_year_prefix() -> None:
    ts = normalize_time_scope("ב-2023")
    assert ts.granularity == "year"
    assert ts.start is not None and ts.start.startswith("2023-")


def test_hebrew_knesset_term() -> None:
    ts = normalize_time_scope("כנסת ה-25")
    assert ts.granularity == "term"
    assert ts.start is not None and ts.start.startswith("2022-11-15")


def test_english_knesset_term() -> None:
    ts = normalize_time_scope("the 25th Knesset", language="en")
    assert ts.granularity == "term"


def test_hebrew_month() -> None:
    ts = normalize_time_scope("ינואר 2024")
    assert ts.granularity == "month"
    assert ts.start is not None and ts.start.startswith("2024-01-01")


def test_last_year_relative_to_reference() -> None:
    ts = normalize_time_scope("last year", language="en", reference_date=date(2025, 5, 1))
    assert ts.granularity == "year"
    assert ts.start is not None and ts.start.startswith("2024-")


def test_nonsense_is_unknown() -> None:
    ts = normalize_time_scope("sometime")
    assert ts.granularity == "unknown"


def test_unknown_term_number_falls_back_to_unknown() -> None:
    ts = normalize_time_scope("כנסת 99")
    assert ts.granularity == "unknown"
