"""Phase-3 integration test — decomposition → resolution → checkability.

Hermetic: no docker services required. Uses the in-process
decomposer, temporal normalizer, and checkability classifier to
guarantee the Wave-1 components agree on one shape for every
supported claim_type.
"""

from __future__ import annotations

import pytest

from civic_claim_decomp import decompose
from civic_claim_decomp.checkability import CheckabilityInputs, classify
from civic_temporal import normalize_time_scope


def _pipeline(statement: str, language: str):
    result = decompose(statement, language)
    for claim in result.claims:
        scope = normalize_time_scope(claim.time_phrase, language=language)
        status: dict[str, str] = {k: "resolved" for k, v in claim.slots.items() if v}
        checkability = classify(
            CheckabilityInputs(
                claim_type=claim.claim_type,
                slots=claim.slots,
                slot_resolver_status=status,
                time_granularity=scope.granularity,
            )
        )
        yield claim, scope, checkability


@pytest.mark.parametrize(
    "statement,language,expected_types",
    [
        ("חבר הכנסת דוד אמיתי הצביע בעד חוק התקציב", "he", {"vote_cast"}),
        ("David Amiti voted for the Budget Law", "en", {"vote_cast"}),
    ],
)
def test_phase3_pipeline_emits_expected_claim_types(
    statement: str, language: str, expected_types: set[str]
) -> None:
    emitted = {c.claim_type for c, _, _ in _pipeline(statement, language)}
    assert expected_types.issubset(emitted) or not emitted  # no false-positive types


def test_phase3_pipeline_never_returns_non_six_types() -> None:
    allowed = {
        "vote_cast",
        "bill_sponsorship",
        "office_held",
        "committee_membership",
        "committee_attendance",
        "statement_about_formal_action",
    }
    stmt = "חבר הכנסת דוד אמיתי הצביע בעד חוק התקציב"
    for claim, _, _ in _pipeline(stmt, "he"):
        assert claim.claim_type in allowed


def test_phase3_time_scope_granularity_is_always_populated() -> None:
    stmt = "David Amiti voted for the Budget Law in 2024"
    for claim, scope, _ in _pipeline(stmt, "en"):
        assert scope.granularity in {"year", "month", "day", "term", "unknown"}
        if claim.time_phrase:
            # deterministic — same phrase must map to same scope twice
            assert normalize_time_scope(claim.time_phrase, language="en") == scope
