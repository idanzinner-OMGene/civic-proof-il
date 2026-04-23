"""civic_entity_resolution — deterministic resolver MVP.

Implements steps 1-4 of the plan's resolution order
(``docs/political_verifier_v_1_plan.md`` lines 357-363):

1. Official external IDs
2. Exact normalized Hebrew match
3. Curated aliases (``entity_aliases`` table)
4. Transliteration normalization

Steps 5 (fuzzy matching) and 6 (LLM fallback) are deferred to Phase 3.
"""

from __future__ import annotations

from .normalize import normalize_hebrew, transliterate_hebrew
from .resolver import Candidate, ResolveResult, resolve

__all__ = [
    "Candidate",
    "ResolveResult",
    "normalize_hebrew",
    "resolve",
    "transliterate_hebrew",
]
