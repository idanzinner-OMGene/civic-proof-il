"""Unit tests for the rule-first decomposer.

Per ``.cursor/rules/real-data-tests.mdc``, these tests do NOT assert on
domain entities (real MK names, real bill numbers). They assert on the
structural decomposition behavior: which claim_type came out, which
slots were extracted, and which slot invariants held. The real-data
gold set (Wave 1 A8) exercises end-to-end correctness with recorded
statements.
"""

from __future__ import annotations

from civic_claim_decomp import decompose


def test_empty_statement_yields_no_claims() -> None:
    result = decompose("", "he")
    assert result.claims == []
    assert result.rule_matches == 0


def test_unknown_shape_falls_through_to_nothing() -> None:
    result = decompose("sky is blue", "en")
    assert result.claims == []
    assert result.rule_matches == 0
    assert not result.llm_invoked


class _StubProvider:
    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload
        self.calls = 0

    def decompose(self, statement: str, language: str) -> list[dict]:
        self.calls += 1
        return self.payload


def test_llm_fallback_runs_when_rules_find_nothing() -> None:
    provider = _StubProvider(
        [
            {
                "claim_type": "vote_cast",
                "speaker_person_id": "subject text",
                "bill_id": "bill text",
                "vote_value": "for",
                "normalized_text": "subject voted for bill",
            }
        ]
    )
    result = decompose("some unparseable free-text", "en", llm_provider=provider)
    assert provider.calls == 1
    assert result.llm_invoked is True
    assert len(result.claims) == 1
    claim = result.claims[0]
    assert claim.method == "llm"
    assert claim.claim_type == "vote_cast"
    assert claim.slots["vote_value"] == "for"


def test_llm_fallback_rejected_if_slots_invalid() -> None:
    provider = _StubProvider(
        [{"claim_type": "vote_cast", "bill_id": "x"}]  # missing speaker + vote_value
    )
    result = decompose("some free text", "en", llm_provider=provider)
    assert provider.calls == 1
    assert result.claims == []
    assert result.validation_errors


def test_llm_not_called_when_rules_succeed() -> None:
    provider = _StubProvider([])
    # English vote rule is the simplest to trigger deterministically.
    result = decompose(
        "John Doe voted for the landmark reform bill in 2024.",
        "en",
        llm_provider=provider,
    )
    assert provider.calls == 0
    assert result.rule_matches >= 1
    assert not result.llm_invoked


def test_english_vote_rule_extracts_slots() -> None:
    result = decompose(
        "John Doe voted against the budget bill in 2024.",
        "en",
    )
    assert len(result.claims) == 1
    claim = result.claims[0]
    assert claim.claim_type == "vote_cast"
    assert claim.slots["vote_value"] == "against"
    assert claim.slots["bill_id"]
    assert claim.slots["speaker_person_id"]
    assert claim.time_phrase == "2024"


def test_english_sponsorship_rule_extracts_slots() -> None:
    result = decompose(
        "Jane Roe sponsored the reform bill in 2023.",
        "en",
    )
    assert len(result.claims) >= 1
    claim = result.claims[0]
    assert claim.claim_type == "bill_sponsorship"
    assert claim.slots["bill_id"]


def test_english_committee_membership_rule() -> None:
    result = decompose(
        "Alex Vote was a member of the Finance committee in 2022.",
        "en",
    )
    assert any(c.claim_type == "committee_membership" for c in result.claims)


def test_method_is_rules_when_rules_match() -> None:
    result = decompose("John Doe voted for the reform bill.", "en")
    assert result.claims
    assert all(c.method == "rules" for c in result.claims)
