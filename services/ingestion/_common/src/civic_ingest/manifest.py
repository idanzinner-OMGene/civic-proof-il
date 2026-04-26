"""Source manifests — one YAML file per (family, adapter).

The canonical shape is mirrored by
``data_contracts/jsonschemas/source_manifest.schema.json`` and the two
are kept aligned by ``tests/smoke/test_alignment.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

__all__ = [
    "EntityHints",
    "SourceManifest",
    "load_all_manifests",
    "load_manifest",
]


SourceFamily = Literal["knesset", "gov_il", "elections"]
ParserKind = Literal[
    "structured_json",
    "structured_csv",
    "csv",
    "html",
    "pdf",
    "odata_json",
]
AdapterKind = Literal[
    "people",
    "committees",
    "votes",
    "sponsorships",
    "attendance",
    "positions",
    "bill_initiators",
    "committee_memberships",
]


class EntityHints(BaseModel):
    """Hints the parser + entity resolver use on this adapter's payloads."""

    model_config = ConfigDict(extra="forbid")

    hebrew_name_field: str | None = Field(
        default=None,
        description="JSONPath-ish key where the Hebrew name lives in the payload.",
    )
    external_id_field: str | None = Field(
        default=None,
        description="Field containing the canonical external ID (e.g. MK ID).",
    )
    locale: Literal["he", "en"] = Field(default="he")


class SourceManifest(BaseModel):
    """Source manifest contract.

    The only authoritative source of an adapter's metadata — what to
    fetch, what tier it is, what parser to route to, and how to resolve
    entities in its payloads.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    family: SourceFamily
    adapter: AdapterKind
    source_url: HttpUrl
    source_tier: Literal[1, 2, 3]
    parser: ParserKind
    cadence_cron: str = Field(
        description="Crontab-style cadence (e.g. '0 3 * * *').",
    )
    entity_hints: EntityHints = Field(default_factory=EntityHints)


def load_manifest(path: str | Path) -> SourceManifest:
    """Load and validate a YAML manifest file."""

    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return SourceManifest.model_validate(data)


def load_all_manifests(root: str | Path = "services/ingestion") -> list[SourceManifest]:
    """Discover + load every ``manifests/*.yaml`` under ``root``.

    Silently skips files whose filename starts with ``_`` (reserved).
    Raises if any valid-looking manifest fails validation.
    """

    root = Path(root)
    out: list[SourceManifest] = []
    for manifest_path in sorted(root.rglob("manifests/*.yaml")):
        if manifest_path.name.startswith("_"):
            continue
        out.append(load_manifest(manifest_path))
    return out
