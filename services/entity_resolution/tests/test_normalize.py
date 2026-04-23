from __future__ import annotations

from civic_entity_resolution.normalize import normalize_hebrew, transliterate_hebrew


def test_normalize_strips_niqqud_and_collapses_whitespace():
    raw = "  אַבְרָהָם   בֶן דָוִד\t "
    assert normalize_hebrew(raw) == "אברהם בן דוד"


def test_normalize_returns_empty_for_empty_input():
    assert normalize_hebrew("") == ""
    assert normalize_hebrew(None) == ""  # type: ignore[arg-type]


def test_transliterate_hebrew_is_deterministic():
    assert transliterate_hebrew("שלום") == "shlvm"
    assert transliterate_hebrew("ישראל") == "yshral"


def test_transliterate_preserves_unknown_chars():
    assert transliterate_hebrew("בית 12") == "byt 12"
