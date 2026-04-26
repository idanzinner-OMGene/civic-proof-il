"""Tests for the StubProvider / EnvProvider seams."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from civic_claim_decomp import (
    EnvProvider,
    StubProvider,
    decompose,
    load_stub_provider_from_dir,
    statement_key,
)


def test_statement_key_is_deterministic() -> None:
    assert statement_key("hi", "en") == statement_key("hi", "en")
    assert statement_key("hi", "en") != statement_key("hi", "he")


def test_stub_provider_returns_empty_for_unknown_statement() -> None:
    provider = StubProvider({})
    assert provider.decompose("anything", "en") == []


def test_stub_provider_returns_canned_claims() -> None:
    key = statement_key("statement text", "en")
    provider = StubProvider(
        {
            key: {
                "claims": [
                    {
                        "claim_type": "vote_cast",
                        "speaker_person_id": "X",
                        "bill_id": "Y",
                        "vote_value": "for",
                        "normalized_text": "X voted for Y",
                    }
                ]
            }
        }
    )
    result = decompose("statement text", "en", llm_provider=provider)
    assert result.llm_invoked
    assert len(result.claims) == 1
    assert result.claims[0].method == "llm"


def test_load_stub_provider_from_dir(tmp_path: Path) -> None:
    key = statement_key("hello", "en")
    (tmp_path / f"{key}.json").write_text(
        json.dumps({"claims": [{"claim_type": "office_held", "speaker_person_id": "X", "office_id": "Y"}]}),
        encoding="utf-8",
    )
    provider = load_stub_provider_from_dir(tmp_path)
    assert provider.decompose("hello", "en")


def test_env_provider_defaults_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CIVIC_LLM_PROVIDER", raising=False)
    key = statement_key("statement", "en")
    stub = StubProvider(
        {
            key: {
                "claims": [
                    {
                        "claim_type": "vote_cast",
                        "speaker_person_id": "X",
                        "bill_id": "Y",
                        "vote_value": "for",
                    }
                ]
            }
        }
    )
    ep = EnvProvider(stub)
    assert ep.decompose("statement", "en")


def test_env_provider_unknown_name_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIVIC_LLM_PROVIDER", "openai")
    ep = EnvProvider(StubProvider({}))
    assert ep.decompose("anything", "en") == []
