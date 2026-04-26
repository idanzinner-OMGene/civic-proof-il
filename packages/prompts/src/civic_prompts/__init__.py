"""civic_prompts — versioned LLM prompt templates for the allowed roles.

Per plan lines 441-454, LLM use is restricted to exactly four categories:

1. ``decomposition`` — claim decomposition (rule-first, LLM fallback).
2. ``temporal_normalization`` — hard-to-parse Hebrew time phrases.
3. ``summarize_evidence`` — evidence summary for the reviewer note.
4. ``reviewer_explanation`` — reviewer-facing explanation.

Prompt cards live under ``civic_prompts/<category>/<version>.yaml`` and
are loaded deterministically by :func:`load_card`. The YAML body is
intentionally plain text + a few metadata keys so downstream consumers
can evolve the provider without touching the card format.
"""

from __future__ import annotations

from .loader import PromptCard, available_cards, load_card

__all__ = ["PromptCard", "available_cards", "load_card"]
