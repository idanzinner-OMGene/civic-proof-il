"""Unit tests for civic_ingest.manifest."""

from __future__ import annotations

from pathlib import Path

import pytest

from civic_ingest.manifest import SourceManifest, load_all_manifests, load_manifest

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_load_knesset_people_manifest():
    m = load_manifest(REPO_ROOT / "services/ingestion/knesset/manifests/people.yaml")
    assert m.family == "knesset"
    assert m.adapter == "people"
    assert m.source_tier == 1
    assert m.parser == "odata_json"
    assert m.entity_hints.locale == "he"


def test_load_all_manifests_covers_five_adapters():
    all_manifests = load_all_manifests(REPO_ROOT / "services/ingestion")
    adapters = sorted(m.adapter for m in all_manifests)
    assert adapters == sorted(
        ["people", "committees", "votes", "sponsorships", "attendance"]
    )


def test_manifest_rejects_unknown_parser(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
family: knesset
adapter: people
source_url: https://example.com/data
source_tier: 1
parser: magic_parser
cadence_cron: "0 4 * * *"
entity_hints:
  locale: he
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        load_manifest(bad)


def test_manifest_forbids_extra_fields():
    with pytest.raises(Exception):
        SourceManifest.model_validate(
            {
                "family": "knesset",
                "adapter": "people",
                "source_url": "https://example.com/",
                "source_tier": 1,
                "parser": "odata_json",
                "cadence_cron": "0 4 * * *",
                "entity_hints": {"locale": "he"},
                "unexpected": "boom",
            }
        )
