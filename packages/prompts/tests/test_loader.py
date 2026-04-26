"""Tests for civic_prompts.loader."""

from __future__ import annotations

import pytest

from civic_prompts import available_cards, load_card


def test_all_four_categories_have_v1_cards() -> None:
    cards = available_cards()
    categories = {c for c, _ in cards}
    assert categories == {
        "decomposition",
        "temporal_normalization",
        "summarize_evidence",
        "reviewer_explanation",
    }


def test_load_card_decomposition_v1() -> None:
    card = load_card("decomposition", "v1")
    assert card.category == "decomposition"
    assert card.version == "v1"
    assert "claim_type" in card.system
    assert "{statement}" in card.user_template
    rendered = card.render(statement="X voted for Y", language="en")
    assert "X voted for Y" in rendered


def test_load_card_unknown_category_raises() -> None:
    with pytest.raises(ValueError):
        load_card("not_allowed", "v1")


def test_load_card_unknown_version_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_card("decomposition", "v999")
