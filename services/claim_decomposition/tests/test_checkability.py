"""Tests for the checkability classifier."""

from __future__ import annotations

from civic_claim_decomp import CheckabilityInputs, classify


def _slots(**overrides):
    base = {
        "speaker_person_id": "p1",
        "target_person_id": None,
        "bill_id": "b1",
        "committee_id": None,
        "office_id": None,
        "vote_value": "for",
    }
    base.update(overrides)
    return base


def test_happy_path_vote_cast() -> None:
    inputs = CheckabilityInputs(
        claim_type="vote_cast",
        slots=_slots(),
        slot_resolver_status={"speaker_person_id": "resolved", "bill_id": "resolved"},
        time_granularity="year",
    )
    assert classify(inputs) == "checkable"


def test_unknown_claim_type() -> None:
    inputs = CheckabilityInputs(
        claim_type="nonsense",
        slots={},
        time_granularity="year",
    )
    assert classify(inputs) == "non_checkable"


def test_missing_required_slot() -> None:
    inputs = CheckabilityInputs(
        claim_type="vote_cast",
        slots=_slots(bill_id=None),
        time_granularity="year",
    )
    assert classify(inputs) == "insufficient_entity_resolution"


def test_forbidden_slot_present() -> None:
    inputs = CheckabilityInputs(
        claim_type="vote_cast",
        slots=_slots(office_id="o1"),
        time_granularity="year",
    )
    assert classify(inputs) == "insufficient_entity_resolution"


def test_ambiguous_speaker_resolver() -> None:
    inputs = CheckabilityInputs(
        claim_type="vote_cast",
        slots=_slots(),
        slot_resolver_status={"speaker_person_id": "ambiguous"},
        time_granularity="year",
    )
    assert classify(inputs) == "insufficient_entity_resolution"


def test_unknown_time_for_vote_cast() -> None:
    inputs = CheckabilityInputs(
        claim_type="vote_cast",
        slots=_slots(),
        slot_resolver_status={"speaker_person_id": "resolved", "bill_id": "resolved"},
        time_granularity="unknown",
    )
    assert classify(inputs) == "insufficient_time_scope"


def test_unknown_time_ok_for_office_held() -> None:
    inputs = CheckabilityInputs(
        claim_type="office_held",
        slots={
            "speaker_person_id": "p1",
            "target_person_id": None,
            "bill_id": None,
            "committee_id": None,
            "office_id": "o1",
            "vote_value": None,
        },
        slot_resolver_status={"speaker_person_id": "resolved", "office_id": "resolved"},
        time_granularity="unknown",
    )
    assert classify(inputs) == "checkable"
