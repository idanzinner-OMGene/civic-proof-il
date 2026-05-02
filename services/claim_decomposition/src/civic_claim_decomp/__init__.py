"""civic_claim_decomp — rule-first claim decomposition with LLM fallback.

Plan mapping (``docs/political_verifier_v_1_plan.md``):

- Phase 3, ticket 11 — rule-based decomposition for the main templates.
- Phase 3, ticket 12 — LLM fallback decomposition behind schema validation.
- Rule: "rules first, LLM second, schema validation last" (line 372).

V2 additions (PR-2):

- :class:`DeclarationDecomposer` — wraps v1 ``decompose`` and always emits a
  first-class ``Declaration`` plus derived claims + classifications.
- :func:`classify_family` — maps claim types to ``ClaimFamily``.
- :func:`classify_declaration_checkability` — aggregates per-claim checkability
  into a declaration-level value.
- :func:`extract_utterance_time` / :func:`extract_time_scope` — temporal helpers.
"""

from __future__ import annotations

from .checkability import TIME_REQUIRED_CLAIM_TYPES, CheckabilityInputs, classify
from .claim_family_classifier import (
    FORMAL_ACTION_CLAIM_TYPES,
    POSITION_CLAIM_TYPES,
    classify_family,
    classify_family_from_types,
)
from .declaration_checkability import classify_declaration_checkability
from .declaration_decomposer import (
    DeclarationDecomposer,
    DeclarationDecompositionResult,
)
from .decomposer import DecomposedClaim, DecompositionResult, LLMProvider, decompose
from .llm import EnvProvider, StubProvider, load_stub_provider_from_dir, statement_key
from .persistence import StatementRecord, persist_statement
from .rules import RULE_TEMPLATES, RuleMatch, RuleTemplate
from .temporal_scope_extractor import extract_time_scope, extract_utterance_time

__all__ = [
    # v1 public surface (unchanged)
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
    # V2 additions (PR-2)
    "DeclarationDecomposer",
    "DeclarationDecompositionResult",
    "FORMAL_ACTION_CLAIM_TYPES",
    "POSITION_CLAIM_TYPES",
    "classify_declaration_checkability",
    "classify_family",
    "classify_family_from_types",
    "extract_time_scope",
    "extract_utterance_time",
]
