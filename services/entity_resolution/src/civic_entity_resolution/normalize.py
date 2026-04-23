"""Hebrew name normalization + simple transliteration.

Both functions are deterministic; neither allocates unbounded state.
The transliteration table covers letters only (no niqqud); the resolver
falls back to an alias lookup when transliteration misses.
"""

from __future__ import annotations

import unicodedata

__all__ = ["normalize_hebrew", "transliterate_hebrew"]


_HEBREW_TO_LATIN = {
    "א": "a",
    "ב": "b",
    "ג": "g",
    "ד": "d",
    "ה": "h",
    "ו": "v",
    "ז": "z",
    "ח": "ch",
    "ט": "t",
    "י": "y",
    "כ": "k",
    "ך": "k",
    "ל": "l",
    "מ": "m",
    "ם": "m",
    "נ": "n",
    "ן": "n",
    "ס": "s",
    "ע": "a",
    "פ": "p",
    "ף": "f",
    "צ": "tz",
    "ץ": "tz",
    "ק": "k",
    "ר": "r",
    "ש": "sh",
    "ת": "t",
}


def normalize_hebrew(text: str) -> str:
    """Collapse whitespace, strip niqqud, and NFC-normalize ``text``.

    Returns an empty string for ``None``-like input — callers decide
    whether that's an error.
    """

    if not text:
        return ""
    stripped = "".join(
        ch for ch in text if not (0x0591 <= ord(ch) <= 0x05C7)
    )
    normalized = unicodedata.normalize("NFC", stripped)
    return " ".join(normalized.strip().split())


def transliterate_hebrew(text: str) -> str:
    """Deterministic Hebrew → Latin transliteration.

    Unknown characters are preserved verbatim (callers treat the result
    as a search key, never as a display string).
    """

    normalized = normalize_hebrew(text)
    out: list[str] = []
    for ch in normalized:
        out.append(_HEBREW_TO_LATIN.get(ch, ch))
    return "".join(out).strip().lower()
