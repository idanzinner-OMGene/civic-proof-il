"""Prompt-card loader (pure Python, no LLM SDK)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

ALLOWED_CATEGORIES: frozenset[str] = frozenset(
    {
        "decomposition",
        "temporal_normalization",
        "summarize_evidence",
        "reviewer_explanation",
    }
)

_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class PromptCard:
    category: str
    version: str
    system: str
    user_template: str
    metadata: Mapping[str, Any]

    def render(self, **kwargs: Any) -> str:
        return self.user_template.format(**kwargs)


def _card_path(category: str, version: str) -> Path:
    return _ROOT / category / f"{version}.yaml"


def load_card(category: str, version: str = "v1") -> PromptCard:
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"prompt category {category!r} not in allowed set {sorted(ALLOWED_CATEGORIES)}"
        )
    path = _card_path(category, version)
    if not path.is_file():
        raise FileNotFoundError(f"no prompt card at {path}")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"prompt card at {path} must be a YAML mapping")
    return PromptCard(
        category=category,
        version=version,
        system=str(doc["system"]).rstrip(),
        user_template=str(doc["user_template"]),
        metadata={k: v for k, v in doc.items() if k not in {"system", "user_template"}},
    )


def available_cards() -> list[tuple[str, str]]:
    """List all committed prompt cards as ``(category, version)`` pairs."""

    cards: list[tuple[str, str]] = []
    for category in sorted(ALLOWED_CATEGORIES):
        cat_dir = _ROOT / category
        if not cat_dir.is_dir():
            continue
        for path in sorted(cat_dir.glob("*.yaml")):
            cards.append((category, path.stem))
    return cards
