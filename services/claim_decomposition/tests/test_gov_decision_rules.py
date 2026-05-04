"""Rule decomposition for ``government_decision`` claims (structure only).

No synthetic domain data — these tests exercise the pure regex patterns
against fabricated rule-level inputs (plain Hebrew/English sentences that
contain a decision number). The decision numbers used here are real numbers
that appear in the cassette (e.g. 2084), but the surrounding sentence
context is a minimal template, not an invented domain fact.
"""

from __future__ import annotations

from civic_claim_decomp import decompose
from civic_claim_decomp.rules import _HE_GOV_DECISION_NUMBER, _HE_GOV_DECISION_REF, _EN_GOV_DECISION_NUMBER


# ---------------------------------------------------------------------------
# Raw regex match tests (no decomposer, no slot validation)
# ---------------------------------------------------------------------------


def test_he_gov_decision_number_matches_standard_form() -> None:
    text = "החלטת ממשלה מספר 2084"
    m = _HE_GOV_DECISION_NUMBER.search(text)
    assert m is not None
    assert m.group("decision_number") == "2084"
    assert m.group("government_number") is None


def test_he_gov_decision_number_matches_cabinet_decided() -> None:
    text = "הממשלה החליטה 712"
    m = _HE_GOV_DECISION_NUMBER.search(text)
    assert m is not None
    assert m.group("decision_number") == "712"


def test_he_gov_decision_ref_matches_behahlatah() -> None:
    text = "בהחלטה מספר 2084"
    m = _HE_GOV_DECISION_REF.search(text)
    assert m is not None
    assert m.group("decision_number") == "2084"


def test_he_gov_decision_ref_matches_lehahlatah() -> None:
    text = "להחלטה מספר 400"
    m = _HE_GOV_DECISION_REF.search(text)
    assert m is not None
    assert m.group("decision_number") == "400"


def test_en_gov_decision_number_matches_standard_form() -> None:
    text = "Government decision number 2084"
    m = _EN_GOV_DECISION_NUMBER.search(text)
    assert m is not None
    assert m.group("decision_number") == "2084"


def test_en_cabinet_decision_matches() -> None:
    text = "Cabinet decision 712"
    m = _EN_GOV_DECISION_NUMBER.search(text)
    assert m is not None
    assert m.group("decision_number") == "712"


def test_en_cabinet_resolution_matches() -> None:
    text = "Government resolution number 500"
    m = _EN_GOV_DECISION_NUMBER.search(text)
    assert m is not None
    assert m.group("decision_number") == "500"


# ---------------------------------------------------------------------------
# Full decompose() integration
# ---------------------------------------------------------------------------


def test_decompose_hebrew_gov_decision_number_emits_claim() -> None:
    result = decompose("החלטת ממשלה מספר 2084", "he")
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.claim_type == "government_decision"
    assert c.slots["government_decision_id"] == "2084"


def test_decompose_hebrew_gov_decision_ref_emits_claim() -> None:
    result = decompose("בהחלטה מספר 712", "he")
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.claim_type == "government_decision"
    assert c.slots["government_decision_id"] == "712"


def test_decompose_english_gov_decision_emits_claim() -> None:
    result = decompose("Government decision number 2084", "en")
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c.claim_type == "government_decision"
    assert c.slots["government_decision_id"] == "2084"


def test_decompose_gov_decision_does_not_match_unrelated() -> None:
    result = decompose("הצביע בעד הצעת חוק הבריאות", "he")
    # Must not be misclassified as a government_decision
    gov_claims = [c for c in result.claims if c.claim_type == "government_decision"]
    assert not gov_claims
