"""Tests for DeclarationDecomposer — the V2 declaration-first entry point.

Per ``.cursor/rules/real-data-tests.mdc``, these tests assert on structural
decomposition behavior: shape of the returned ``Declaration``, claim counts,
family / checkability values, field presence. They do not use real MK names,
bill numbers, or other domain entities.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from civic_claim_decomp import DeclarationDecomposer, DeclarationDecompositionResult
from civic_ontology.models.declaration import Declaration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXED_SOURCE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


def _decomp(
    text: str,
    language: str = "en",
    *,
    source_kind: str = "other",
    utterance_time: datetime | None = None,
    speaker_person_id: uuid.UUID | None = None,
) -> DeclarationDecompositionResult:
    decomposer = DeclarationDecomposer()
    return decomposer.decompose(
        text,
        language,  # type: ignore[arg-type]
        source_document_id=_FIXED_SOURCE_ID,
        source_kind=source_kind,  # type: ignore[arg-type]
        utterance_time=utterance_time,
        speaker_person_id=speaker_person_id,
    )


# ---------------------------------------------------------------------------
# Declaration shape invariants
# ---------------------------------------------------------------------------


def test_result_always_contains_a_declaration() -> None:
    result = _decomp("sky is blue", "en")
    assert isinstance(result.declaration, Declaration)


def test_declaration_has_all_required_fields_populated() -> None:
    result = _decomp("sky is blue", "en")
    d = result.declaration
    assert isinstance(d.declaration_id, uuid.UUID)
    assert d.utterance_text == "sky is blue"
    assert d.utterance_language == "en"
    assert d.source_document_id == _FIXED_SOURCE_ID
    assert d.source_kind == "other"
    assert isinstance(d.created_at, datetime)
    assert d.created_at.tzinfo is not None


def test_empty_utterance_produces_not_checkable_declaration() -> None:
    result = _decomp("", "en")
    assert result.declaration.checkability == "not_checkable"
    assert result.claims == []
    assert result.family == "unknown"


def test_non_recognisable_text_produces_not_checkable_declaration() -> None:
    result = _decomp("The weather was nice yesterday.", "en")
    assert result.declaration.checkability == "not_checkable"
    assert result.claims == []


def test_recognisable_vote_statement_produces_checkable_declaration() -> None:
    result = _decomp(
        "John Doe voted against the budget bill in 2024.",
        "en",
    )
    assert len(result.claims) >= 1
    assert result.family == "formal_action"
    assert result.declaration.claim_family == "formal_action"
    # With a year anchor and no resolver, the claim should be checkable offline.
    assert result.declaration.checkability == "checkable_formal_action"


def test_recognisable_office_statement_produces_position_claim_declaration() -> None:
    result = _decomp(
        "Jane Roe served as Minister of Finance in 2022.",
        "en",
    )
    assert len(result.claims) >= 1
    assert result.family == "position_claim"
    assert result.declaration.claim_family == "position_claim"


def test_derived_atomic_claim_ids_match_returned_claims() -> None:
    result = _decomp("John Doe voted for the reform bill in 2023.", "en")
    claim_ids = {c.claim_id for c in result.claims}
    declaration_ids = set(result.declaration.derived_atomic_claim_ids)
    assert claim_ids == declaration_ids


def test_explicit_utterance_time_is_preserved() -> None:
    ts = datetime(2024, 5, 1, tzinfo=timezone.utc)
    result = _decomp("any text", "en", utterance_time=ts)
    assert result.declaration.utterance_time == ts


def test_utterance_time_extracted_from_text_when_not_provided() -> None:
    result = _decomp("The vote happened in 2021.", "en")
    # Should extract year 2021 as Jan 1 2021 UTC.
    assert result.declaration.utterance_time is not None
    assert result.declaration.utterance_time.year == 2021


def test_utterance_time_is_none_when_no_cue_in_text() -> None:
    result = _decomp("Nothing temporal here.", "en")
    assert result.declaration.utterance_time is None


def test_speaker_person_id_forwarded_to_declaration() -> None:
    speaker_id = uuid.uuid4()
    result = _decomp("some text", "en", speaker_person_id=speaker_id)
    assert result.declaration.speaker_person_id == speaker_id


def test_source_kind_forwarded_to_declaration() -> None:
    result = _decomp("some text", "en", source_kind="plenum_transcript")
    assert result.declaration.source_kind == "plenum_transcript"


# ---------------------------------------------------------------------------
# LLM fallback path
# ---------------------------------------------------------------------------


class _StubLLMProvider:
    """Minimal stub that returns a canned claim list for any input."""

    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload
        self.calls = 0

    def decompose(self, statement: str, language: str) -> list[dict]:
        self.calls += 1
        return self.payload


def test_llm_fallback_path_produces_declaration_with_derived_claims() -> None:
    provider = _StubLLMProvider(
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
    decomposer = DeclarationDecomposer(llm_provider=provider)
    result = decomposer.decompose(
        "unparseable free-form utterance",
        "en",
        source_document_id=_FIXED_SOURCE_ID,
    )
    assert provider.calls == 1
    assert result.decomposition.llm_invoked is True
    assert len(result.claims) == 1
    assert result.claims[0].claim_type == "vote_cast"
    assert result.family == "formal_action"
    assert isinstance(result.declaration, Declaration)
    assert len(result.declaration.derived_atomic_claim_ids) == 1


def test_llm_fallback_not_invoked_when_rules_match() -> None:
    provider = _StubLLMProvider([])
    decomposer = DeclarationDecomposer(llm_provider=provider)
    result = decomposer.decompose(
        "John Doe voted for the reform bill in 2024.",
        "en",
        source_document_id=_FIXED_SOURCE_ID,
    )
    assert provider.calls == 0
    assert result.decomposition.llm_invoked is False


# ---------------------------------------------------------------------------
# Decomposition result consistency
# ---------------------------------------------------------------------------


def test_decomposition_result_preserved_on_result() -> None:
    result = _decomp("John Doe voted against the budget bill in 2024.", "en")
    assert result.decomposition.rule_matches >= 1
    assert not result.decomposition.llm_invoked


def test_checkability_on_declaration_matches_result_attribute() -> None:
    result = _decomp("John Doe voted against the budget bill in 2024.", "en")
    assert result.declaration.checkability == result.checkability


def test_family_on_declaration_matches_result_attribute() -> None:
    result = _decomp("John Doe voted against the budget bill in 2024.", "en")
    assert result.declaration.claim_family == result.family
