"""DeclarationDecomposer — V2 entry point for utterance decomposition.

This module wraps the v1 rule-first decomposer and always emits a first-class
:class:`~civic_ontology.models.declaration.Declaration` object, even for
utterances that produce no checkable atomic claims.

Public surface::

    result = DeclarationDecomposer().decompose(
        utterance_text="...",
        language="he",
        source_document_id=uuid.UUID("..."),
        source_kind="plenum_transcript",
    )
    # result.declaration   — Declaration (always present)
    # result.claims        — list[DecomposedClaim] (zero or more)
    # result.family        — ClaimFamily
    # result.checkability  — DeclarationCheckability

Design invariants:
- **Wrap, don't replace**: delegates all rule matching to
  :func:`civic_claim_decomp.decomposer.decompose`.
- **No persistence**: callers are responsible for writing to Postgres / Neo4j.
- **No entity resolution**: slots remain as raw text strings; resolution happens
  in the pipeline layer (``VerifyPipeline`` or its future declaration-aware successor).
- **No LLM by default**: the ``llm_provider`` is optional, forwarded unchanged
  to ``decompose``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from civic_ontology.models.declaration import (
    ClaimFamily,
    Declaration,
    DeclarationCheckability,
    SourceKind,
)

from .checkability import CheckabilityInputs, classify
from .claim_family_classifier import classify_family
from .declaration_checkability import classify_declaration_checkability
from .decomposer import DecomposedClaim, DecompositionResult, LLMProvider, decompose
from .temporal_scope_extractor import extract_utterance_time

Language = Literal["he", "en"]

__all__ = ["DeclarationDecomposer", "DeclarationDecompositionResult"]


@dataclass(frozen=True)
class DeclarationDecompositionResult:
    """Full output of a single :meth:`DeclarationDecomposer.decompose` call.

    Attributes
    ----------
    declaration:
        The first-class Declaration object. Always present.
    claims:
        Zero or more raw ``DecomposedClaim`` objects derived from the
        utterance. Slots are still unresolved text strings at this stage.
    decomposition:
        The underlying ``DecompositionResult`` from the v1 decomposer,
        preserved for callers that need rule match counts, LLM-invoked
        flags, or validation errors.
    family:
        The ``ClaimFamily`` computed from the derived claim types.
    checkability:
        The declaration-level checkability computed by aggregating per-claim
        checkability values. Uses *offline* checkability (no entity resolver,
        time granularity from the raw time_phrase only) so callers with a
        live resolver can recompute if needed.
    """

    declaration: Declaration
    claims: list[DecomposedClaim] = field(default_factory=list)
    decomposition: DecompositionResult = field(
        default_factory=DecompositionResult
    )
    family: ClaimFamily = "unknown"
    checkability: DeclarationCheckability = "not_checkable"


class DeclarationDecomposer:
    """Wraps the v1 rule-first decomposer, emitting a ``Declaration`` for every utterance.

    Parameters
    ----------
    llm_provider:
        Optional LLM fallback provider forwarded to :func:`decompose`. Defaults
        to ``None`` (rules-only mode).
    """

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self._llm_provider = llm_provider

    def decompose(
        self,
        utterance_text: str,
        language: Language,
        *,
        source_document_id: uuid.UUID,
        source_kind: SourceKind = "other",
        speaker_person_id: uuid.UUID | None = None,
        utterance_time: datetime | None = None,
        quoted_span: str | None = None,
        canonicalized_text: str | None = None,
    ) -> DeclarationDecompositionResult:
        """Decompose an utterance into a Declaration + derived claims.

        Parameters
        ----------
        utterance_text:
            Raw utterance string. May be empty; an empty utterance still
            produces a ``Declaration`` with ``not_checkable``.
        language:
            ``"he"`` or ``"en"``.
        source_document_id:
            UUID of the ``SourceDocument`` this utterance came from.
        source_kind:
            One of the ``SourceKind`` literals. Defaults to ``"other"``.
        speaker_person_id:
            Pre-resolved speaker UUID if known, ``None`` otherwise.
        utterance_time:
            Explicit timestamp from the source metadata. If ``None``, a
            best-effort time is extracted from the utterance text.
        quoted_span:
            The exact verbatim quote extracted from the source, when available.
        canonicalized_text:
            A pre-normalised form of the utterance, when available.
        """
        now = datetime.now(tz=timezone.utc)

        # --- v1 decomposition ------------------------------------------------
        decomp = decompose(
            utterance_text.strip(),
            language,
            llm_provider=self._llm_provider,
        )

        # --- per-claim offline checkability ----------------------------------
        claim_checkabilities: list[str] = []
        for claim in decomp.claims:
            check = classify(
                CheckabilityInputs(
                    claim_type=claim.claim_type,
                    slots=claim.slots,
                    # No resolver in this layer; treat all present slots as
                    # "not_applicable" so resolution failures do not downgrade
                    # offline classification.
                    slot_resolver_status={},
                    time_granularity=self._time_granularity(
                        claim.time_phrase, language
                    ),
                )
            )
            claim_checkabilities.append(check)

        # --- classification --------------------------------------------------
        family: ClaimFamily = classify_family(decomp)
        declaration_check: DeclarationCheckability = (
            classify_declaration_checkability(claim_checkabilities)
        )

        # --- utterance_time fallback -----------------------------------------
        resolved_time = utterance_time
        if resolved_time is None:
            resolved_time = extract_utterance_time(utterance_text, language)

        # --- build Declaration -----------------------------------------------
        declaration = Declaration(
            declaration_id=uuid.uuid4(),
            speaker_person_id=speaker_person_id,
            utterance_text=utterance_text,
            utterance_language=language,
            utterance_time=resolved_time,
            source_document_id=source_document_id,
            source_kind=source_kind,
            quoted_span=quoted_span,
            canonicalized_text=canonicalized_text,
            claim_family=family,
            checkability=declaration_check,
            derived_atomic_claim_ids=[c.claim_id for c in decomp.claims],
            created_at=now,
        )

        return DeclarationDecompositionResult(
            declaration=declaration,
            claims=decomp.claims,
            decomposition=decomp,
            family=family,
            checkability=declaration_check,
        )

    @staticmethod
    def _time_granularity(time_phrase: str | None, language: Language) -> str:
        """Return the granularity string for a raw time phrase.

        Used only for offline checkability classification inside this layer.
        Delegates to :func:`~civic_claim_decomp.temporal_scope_extractor.extract_time_scope`
        to avoid direct coupling to ``civic_temporal``.
        """
        from .temporal_scope_extractor import extract_time_scope

        if not time_phrase:
            return "unknown"
        return extract_time_scope(time_phrase, language).granularity
