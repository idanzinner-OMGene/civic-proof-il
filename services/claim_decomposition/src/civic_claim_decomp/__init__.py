"""civic_claim_decomp — rule-first claim decomposition with LLM fallback.

Plan mapping (``docs/political_verifier_v_1_plan.md``):

- Phase 3, ticket 11 — rule-based decomposition for the main templates.
- Phase 3, ticket 12 — LLM fallback decomposition behind schema validation.
- Rule: "rules first, LLM second, schema validation last" (line 372).
"""

from __future__ import annotations

from .checkability import TIME_REQUIRED_CLAIM_TYPES, CheckabilityInputs, classify
from .decomposer import DecomposedClaim, DecompositionResult, LLMProvider, decompose
from .llm import EnvProvider, StubProvider, load_stub_provider_from_dir, statement_key
from .persistence import StatementRecord, persist_statement
from .rules import RULE_TEMPLATES, RuleMatch, RuleTemplate

__all__ = [
    "CheckabilityInputs",
    "DecomposedClaim",
    "DecompositionResult",
    "EnvProvider",
    "LLMProvider",
    "RULE_TEMPLATES",
    "RuleMatch",
    "RuleTemplate",
    "StatementRecord",
    "StubProvider",
    "TIME_REQUIRED_CLAIM_TYPES",
    "classify",
    "decompose",
    "load_stub_provider_from_dir",
    "persist_statement",
    "statement_key",
]
