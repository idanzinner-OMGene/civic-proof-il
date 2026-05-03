"""Rule decomposition for ``election_result`` claims (structure only)."""

from __future__ import annotations

from civic_claim_decomp import decompose


def test_hebrew_seats_rule_emits_election_result() -> None:
    result = decompose("הרשימה זכתה ב-5 מנדטים", "he")
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.claim_type == "election_result"
    assert c.slots["party_id"] == "הרשימה"
    assert c.slots["expected_seats"] == "5"
    assert c.slots["expect_passed_threshold"] is None


def test_hebrew_threshold_below_sets_expect_passed_false() -> None:
    result = decompose("מרצ לא עברה את אחוז החסימה", "he")
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.claim_type == "election_result"
    assert c.slots["party_id"] == "מרצ"
    assert c.slots["expect_passed_threshold"] == "false"
    assert c.slots["expected_seats"] is None


def test_english_seats_rule() -> None:
    result = decompose("The List won 5 seats", "en")
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.claim_type == "election_result"
    assert c.slots["party_id"] == "The List"
    assert c.slots["expected_seats"] == "5"


def test_english_threshold_below() -> None:
    result = decompose("Meretz did not pass the electoral threshold", "en")
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.claim_type == "election_result"
    assert c.slots["party_id"] == "Meretz"
    assert c.slots["expect_passed_threshold"] == "false"
