"""Tests for per-claim_type slot templates."""

from __future__ import annotations

from typing import get_args

import pytest

from civic_ontology import SLOT_TEMPLATES, validate_slots
from civic_ontology.claim_slots import ALL_SLOTS
from civic_ontology.models.atomic_claim import ClaimType


def test_every_claim_type_has_a_slot_template() -> None:
    for claim_type in get_args(ClaimType):
        assert claim_type in SLOT_TEMPLATES


def test_templates_cover_only_known_slots() -> None:
    for tmpl in SLOT_TEMPLATES.values():
        assert tmpl.required <= ALL_SLOTS
        assert tmpl.optional <= ALL_SLOTS
        assert not (tmpl.required & tmpl.optional), (
            f"{tmpl.claim_type}: required and optional overlap"
        )


def test_vote_cast_requires_bill_and_value() -> None:
    tmpl = SLOT_TEMPLATES["vote_cast"]
    assert "bill_id" in tmpl.required
    assert "vote_value" in tmpl.required
    assert "speaker_person_id" in tmpl.required
    assert "office_id" in tmpl.forbidden
    assert "committee_id" in tmpl.forbidden


@pytest.mark.parametrize("claim_type", list(get_args(ClaimType)))
def test_forbidden_is_complement_of_required_plus_optional(claim_type: str) -> None:
    tmpl = SLOT_TEMPLATES[claim_type]
    assert tmpl.forbidden == ALL_SLOTS - tmpl.required - tmpl.optional


def test_validate_slots_happy_path_vote_cast() -> None:
    violations = validate_slots(
        "vote_cast",
        {
            "speaker_person_id": "x",
            "bill_id": "y",
            "vote_value": "for",
        },
    )
    assert violations == []


def test_validate_slots_missing_required() -> None:
    violations = validate_slots(
        "vote_cast",
        {"speaker_person_id": "x", "bill_id": "y"},
    )
    assert any("vote_value" in v for v in violations)


def test_validate_slots_forbidden_present() -> None:
    violations = validate_slots(
        "vote_cast",
        {
            "speaker_person_id": "x",
            "bill_id": "y",
            "vote_value": "for",
            "office_id": "z",
        },
    )
    assert any("office_id" in v for v in violations)


def test_validate_slots_unknown_claim_type() -> None:
    violations = validate_slots("not_a_real_type", {})  # type: ignore[arg-type]
    assert any("unknown claim_type" in v for v in violations)
