"""Rule-first (+ optional LLM fallback) claim decomposer.

Public surface:

* :func:`decompose(statement, language, *, llm_provider=None)` — runs the
  rule-based templates, then falls back to the LLM provider if nothing
  matched and a provider was supplied. Every candidate is schema-
  validated against ``AtomicClaim`` slot templates before being
  returned.

No side effects. Callers (the API layer) are responsible for:

* resolving the ``subject`` text to a canonical person UUID (entity resolver),
* normalizing the ``time_scope`` raw phrase (temporal normalizer),
* persisting to Postgres / Neo4j / OpenSearch,
* and calling the checkability classifier.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from civic_ontology import SLOT_TEMPLATES
from civic_ontology.claim_slots import validate_slots
from civic_ontology.models.atomic_claim import ClaimType

from .rules import RuleMatch, iter_matches

Language = Literal["he", "en"]
Method = Literal["rules", "llm", "rules+llm"]


class LLMProvider(Protocol):
    """Narrow protocol for the LLM fallback seam (ticket #12).

    Providers return zero or more *raw* slot dicts; the decomposer
    validates them. Providers must not touch the database or call any
    Tier-1 records directly.
    """

    def decompose(self, statement: str, language: Language) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True, slots=True)
class DecomposedClaim:
    """A candidate claim emitted by rule or LLM, before DB resolution."""

    claim_id: uuid.UUID
    raw_text: str
    normalized_text: str
    claim_type: ClaimType
    slots: dict[str, Any]
    time_phrase: str | None
    method: Method
    source_rule: str | None = None


@dataclass(frozen=True, slots=True)
class DecompositionResult:
    """Outcome of a full decomposition run."""

    claims: list[DecomposedClaim] = field(default_factory=list)
    rule_matches: int = 0
    llm_invoked: bool = False
    validation_errors: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return bool(self.claims)


_SUBJECT_SLOT = "speaker_person_id"


def _rule_match_to_claim(match: RuleMatch, statement: str) -> DecomposedClaim:
    groups = dict(match.groups)
    subject = groups.get("subject", "").strip()
    expect_passed_threshold: str | None = None
    if match.template.election_threshold_below:
        expect_passed_threshold = "false"
    # For government_decision rules, `decision_number` is the raw lookup key.
    # Entity resolution will later replace it with a canonical UUID.
    decision_number = (groups.get("decision_number") or "").strip() or None
    government_number = (groups.get("government_number") or "").strip() or None
    slots: dict[str, Any] = {
        "speaker_person_id": subject or None,
        "target_person_id": None,
        "bill_id": groups.get("bill", "").strip() or None,
        "committee_id": groups.get("committee", "").strip() or None,
        "office_id": groups.get("office", "").strip() or None,
        "vote_value": _normalize_vote_value(groups.get("vote_value")),
        "party_id": (groups.get("party") or "").strip() or None,
        "expected_seats": (groups.get("seats") or "").strip() or None,
        "expect_passed_threshold": expect_passed_threshold,
        # Government decision: decision_number used as pre-resolution stand-in for UUID.
        "government_decision_id": decision_number,
        # Carry government_number as an extra hint for retrieval (not a formal slot).
        "government_number": government_number,
    }
    return DecomposedClaim(
        claim_id=uuid.uuid4(),
        raw_text=statement,
        normalized_text=statement[match.span[0] : match.span[1]].strip(),
        claim_type=match.template.claim_type,
        slots=slots,
        time_phrase=groups.get("time"),
        method="rules",
        source_rule=match.template.description,
    )


def _normalize_vote_value(raw: str | None) -> str | None:
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in {"בעד", "for", "in favor of", "in favour of"}:
        return "for"
    if val in {"נגד", "against", "opposed"}:
        return "against"
    if val in {"נמנע", "נמנעה", "abstained", "to abstain"}:
        return "abstain"
    return None


def decompose(
    statement: str,
    language: Language,
    *,
    llm_provider: LLMProvider | None = None,
) -> DecompositionResult:
    """Rules-first claim decomposition with optional LLM fallback.

    Returns every candidate claim that passed slot-template validation.
    Overlapping rule matches are resolved by preferring the longer
    span; equally long spans are resolved by template declaration
    order (``RULE_TEMPLATES``).
    """

    statement = statement.strip()
    if not statement:
        return DecompositionResult()

    matches: list[RuleMatch] = list(iter_matches(statement, language))
    matches.sort(
        key=lambda m: (
            -(m.span[1] - m.span[0]),
            m.span[0],
        )
    )
    selected: list[RuleMatch] = []
    used: list[tuple[int, int]] = []
    for m in matches:
        if any(_overlaps(m.span, s) for s in used):
            continue
        selected.append(m)
        used.append(m.span)

    claims: list[DecomposedClaim] = []
    errors: list[str] = []
    for match in selected:
        claim = _rule_match_to_claim(match, statement)
        violations = validate_slots(claim.claim_type, claim.slots)
        if violations:
            errors.extend(violations)
            continue
        claims.append(claim)

    llm_used = False
    if not claims and llm_provider is not None:
        llm_used = True
        for raw in llm_provider.decompose(statement, language):
            claim = _llm_raw_to_claim(statement, raw)
            if claim is None:
                errors.append("llm output rejected by slot validator")
                continue
            claims.append(claim)

    return DecompositionResult(
        claims=claims,
        rule_matches=len(selected),
        llm_invoked=llm_used,
        validation_errors=errors,
    )


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return not (a[1] <= b[0] or b[1] <= a[0])


def _llm_raw_to_claim(statement: str, raw: dict[str, Any]) -> DecomposedClaim | None:
    """Validate and box a raw LLM slot dict into a ``DecomposedClaim``."""

    claim_type = raw.get("claim_type")
    if claim_type not in SLOT_TEMPLATES:
        return None
    slots = {
        "speaker_person_id": raw.get("speaker_person_id"),
        "target_person_id": raw.get("target_person_id"),
        "bill_id": raw.get("bill_id"),
        "committee_id": raw.get("committee_id"),
        "office_id": raw.get("office_id"),
        "vote_value": _normalize_vote_value(raw.get("vote_value"))
        if raw.get("vote_value") is not None
        else None,
        "party_id": raw.get("party_id"),
        "expected_seats": raw.get("expected_seats"),
        "expect_passed_threshold": raw.get("expect_passed_threshold"),
        "government_decision_id": raw.get("government_decision_id"),
        "government_number": raw.get("government_number"),
    }
    violations = validate_slots(claim_type, slots)
    if violations:
        return None
    normalized_text = (raw.get("normalized_text") or statement).strip()
    time_phrase = raw.get("time_phrase")
    return DecomposedClaim(
        claim_id=uuid.uuid4(),
        raw_text=statement,
        normalized_text=normalized_text,
        claim_type=claim_type,
        slots=slots,
        time_phrase=time_phrase,
        method="llm",
        source_rule=None,
    )


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)
