"""LLM fallback provider implementations.

Two concrete providers ship in this module:

* :class:`StubProvider` — deterministic, no network. Wraps a mapping from
  statement-hash → canned JSON. Used in tests and fixtures. This is the
  ONLY fixture-like JSON allowed in the repo per
  ``.cursor/rules/real-data-tests.mdc`` because it models the LLM's
  response envelope, not domain data; every stub fixture must be
  labelled ``not-domain-data`` in its SOURCE.md.
* :class:`EnvProvider` — reads the active LLM provider name from
  ``CIVIC_LLM_PROVIDER`` and constructs it lazily. Default ``"stub"``.
  A real SDK seam (``openai``, ``anthropic``, etc.) is intentionally
  NOT added here — hook it in behind a narrow Protocol and gate it on
  user approval per the repo's dependency-addition rule.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from .decomposer import LLMProvider

__all__ = [
    "StubProvider",
    "EnvProvider",
    "load_stub_provider_from_dir",
    "statement_key",
]


def statement_key(statement: str, language: str) -> str:
    h = hashlib.sha256()
    h.update(language.encode("utf-8"))
    h.update(b"::")
    h.update(statement.encode("utf-8"))
    return h.hexdigest()[:16]


class StubProvider:
    """Deterministic LLM provider backed by a precomputed mapping.

    Keys are ``statement_key(statement, language)``. Values are the raw
    JSON object the real LLM would have returned (a dict with a
    ``"claims"`` list).
    """

    def __init__(self, canned: Mapping[str, Mapping[str, Any]]) -> None:
        self._canned = dict(canned)

    def decompose(self, statement: str, language: str) -> list[dict[str, Any]]:
        key = statement_key(statement, language)
        payload = self._canned.get(key)
        if payload is None:
            return []
        return list(payload.get("claims", []))

    def known_keys(self) -> Iterable[str]:
        return self._canned.keys()


def load_stub_provider_from_dir(directory: Path) -> StubProvider:
    """Load every ``<statement_key>.json`` in ``directory`` into a provider.

    File format::

        {"claims": [{"claim_type": "vote_cast", ...}, ...]}
    """

    canned: dict[str, Mapping[str, Any]] = {}
    if not directory.is_dir():
        return StubProvider(canned)
    for path in sorted(directory.glob("*.json")):
        canned[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return StubProvider(canned)


class EnvProvider:
    """Env-gated provider picker. Defaults to ``stub``.

    The real ``openai`` / ``anthropic`` / etc. SDK seams live in a
    subclass chosen via ``CIVIC_LLM_PROVIDER`` once the dependency is
    user-approved. Until then, ``EnvProvider`` always returns ``[]`` for
    unknown providers rather than raising — the decomposer treats that
    as "LLM unavailable, move on."
    """

    def __init__(self, stub: StubProvider | None = None) -> None:
        self._stub = stub or StubProvider({})

    def decompose(self, statement: str, language: str) -> list[dict[str, Any]]:
        name = os.environ.get("CIVIC_LLM_PROVIDER", "stub").lower()
        if name == "stub":
            return self._stub.decompose(statement, language)
        return []


# Type check at import time; surfaces if LLMProvider Protocol drifts.
_provider_check: LLMProvider = StubProvider({})  # noqa: F841
