"""Knesset term boundaries.

Sourced from the Knesset's published start dates for each term. Term 25
end-date is open-ended (``None``) until the term concludes; end-bound
logic in the normalizer treats ``None`` as "today" for temporal-alignment
checks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnessetTerm:
    number: int
    start_iso: str  # ISO date of the first plenary session
    end_iso: str | None  # None = current (open)


KNESSET_TERMS: tuple[KnessetTerm, ...] = (
    KnessetTerm(1, "1949-02-14", "1951-08-20"),
    KnessetTerm(2, "1951-08-20", "1955-08-15"),
    KnessetTerm(3, "1955-08-15", "1959-12-04"),
    KnessetTerm(4, "1959-12-04", "1961-09-04"),
    KnessetTerm(5, "1961-09-04", "1965-11-22"),
    KnessetTerm(6, "1965-11-22", "1969-11-17"),
    KnessetTerm(7, "1969-11-17", "1974-01-21"),
    KnessetTerm(8, "1974-01-21", "1977-06-13"),
    KnessetTerm(9, "1977-06-13", "1981-07-20"),
    KnessetTerm(10, "1981-07-20", "1984-08-13"),
    KnessetTerm(11, "1984-08-13", "1988-11-21"),
    KnessetTerm(12, "1988-11-21", "1992-07-13"),
    KnessetTerm(13, "1992-07-13", "1996-06-17"),
    KnessetTerm(14, "1996-06-17", "1999-06-07"),
    KnessetTerm(15, "1999-06-07", "2003-02-17"),
    KnessetTerm(16, "2003-02-17", "2006-04-17"),
    KnessetTerm(17, "2006-04-17", "2009-02-24"),
    KnessetTerm(18, "2009-02-24", "2013-02-05"),
    KnessetTerm(19, "2013-02-05", "2015-03-31"),
    KnessetTerm(20, "2015-03-31", "2019-04-30"),
    KnessetTerm(21, "2019-04-30", "2019-10-03"),
    KnessetTerm(22, "2019-10-03", "2020-03-16"),
    KnessetTerm(23, "2020-03-16", "2020-12-22"),
    KnessetTerm(24, "2020-12-22", "2022-11-15"),
    KnessetTerm(25, "2022-11-15", None),
)


def term_by_number(n: int) -> KnessetTerm | None:
    for t in KNESSET_TERMS:
        if t.number == n:
            return t
    return None
