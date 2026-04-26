"""civic_entity_resolution — steps 1-5 + LLM step-6 seam (Phase 3).

Resolution order per plan lines 357-363:

1. Official external IDs
2. Exact normalized Hebrew match
3. Curated aliases (``entity_aliases`` table)
4. Transliteration normalization
5. Fuzzy Hebrew / English match via ``rapidfuzz`` (threshold + margin)
6. LLM tiebreaker — never invents; only picks from step-5 candidates.
"""

from __future__ import annotations

from .normalize import normalize_hebrew, transliterate_hebrew
from .resolver import (
    FUZZY_MARGIN,
    FUZZY_RESOLVE_THRESHOLD,
    Candidate,
    LLMEntityTiebreaker,
    ResolveResult,
    resolve,
)

__all__ = [
    "Candidate",
    "FUZZY_MARGIN",
    "FUZZY_RESOLVE_THRESHOLD",
    "LLMEntityTiebreaker",
    "ResolveResult",
    "normalize_hebrew",
    "resolve",
    "transliterate_hebrew",
]
