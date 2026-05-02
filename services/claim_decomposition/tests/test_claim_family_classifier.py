"""Tests for the claim-family classifier.

Per ``.cursor/rules/real-data-tests.mdc``, these tests assert on structural
classification behavior only — which ``ClaimFamily`` value results from a given
set of ``claim_type`` values. They do not use domain entities (real MK names,
bill numbers, etc.).
"""

from __future__ import annotations

from civic_claim_decomp import classify_family_from_types


def test_empty_claim_types_yields_unknown() -> None:
    assert classify_family_from_types([]) == "unknown"


def test_vote_cast_yields_formal_action() -> None:
    assert classify_family_from_types(["vote_cast"]) == "formal_action"


def test_bill_sponsorship_yields_formal_action() -> None:
    assert classify_family_from_types(["bill_sponsorship"]) == "formal_action"


def test_committee_attendance_yields_formal_action() -> None:
    assert classify_family_from_types(["committee_attendance"]) == "formal_action"


def test_office_held_yields_position_claim() -> None:
    assert classify_family_from_types(["office_held"]) == "position_claim"


def test_committee_membership_yields_position_claim() -> None:
    assert classify_family_from_types(["committee_membership"]) == "position_claim"


def test_formal_action_wins_over_position_claim_in_mixed_set() -> None:
    # formal_action has higher priority; a mix that includes a direct action
    # claim should still report formal_action.
    assert classify_family_from_types(["office_held", "vote_cast"]) == "formal_action"


def test_statement_about_formal_action_yields_unknown() -> None:
    # statement_about_formal_action is not yet bucketed into a family —
    # it sits between formal_action and position_claim. Until a text-based
    # heuristic is added it falls through to "unknown".
    assert classify_family_from_types(["statement_about_formal_action"]) == "unknown"


def test_multiple_formal_action_types_yields_formal_action() -> None:
    types = ["vote_cast", "bill_sponsorship", "committee_attendance"]
    assert classify_family_from_types(types) == "formal_action"


def test_multiple_position_claim_types_yields_position_claim() -> None:
    types = ["office_held", "committee_membership"]
    assert classify_family_from_types(types) == "position_claim"
