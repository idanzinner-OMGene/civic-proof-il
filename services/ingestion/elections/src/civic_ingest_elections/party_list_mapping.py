"""Party / list continuity mapping for Israeli elections.

Loads the curated YAML mapping (ballot_letters -> knesset_faction_id) and
exposes a lookup function used by the normalizer to resolve each election list
to an existing Knesset Party node in the graph.

Lists that ran below threshold and never entered the Knesset have no faction
ID — they receive a generated UUID keyed by ``cec_list:{knesset}:{letters}``
so they are stable across re-ingests while not colliding with real faction nodes.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

import yaml

from .types import PHASE2_UUID_NAMESPACE

__all__ = ["THRESHOLD_RULE", "get_election_date", "resolve_party_id"]

THRESHOLD_RULE = 0.0325

_MAPPING_PATH = Path(__file__).with_name("party_list_mapping.yaml")


@lru_cache(maxsize=1)
def _load() -> dict:
    return yaml.safe_load(_MAPPING_PATH.read_text(encoding="utf-8")) or {}


def _section(knesset_number: int) -> dict:
    key = f"knesset_{knesset_number}"
    data = _load()
    if key not in data:
        raise KeyError(f"No party mapping for knesset_number={knesset_number}")
    return data[key]


def get_election_date(knesset_number: int) -> str:
    """Return the ISO-8601 election date for the given Knesset number."""
    return _section(knesset_number)["election_date"]


def resolve_party_id(knesset_number: int, ballot_letters: str) -> uuid.UUID:
    """Return the canonical Party UUID for a list in a given election.

    If the list maps to a real Knesset faction (passed threshold, entered the
    Knesset), the UUID is ``uuid5(NS, "knesset_party:{faction_id}")`` — the
    same key used by the positions adapter — so the graph MERGE collapses to
    the same existing Party node.

    If the list has no faction mapping (below threshold or unknown), the UUID
    is ``uuid5(NS, "cec_list:{knesset}:{ballot_letters}")`` — a stable unique
    node for the electoral list that is not linked to any Knesset faction.
    """
    section = _section(knesset_number)
    lists = section.get("lists", {})
    faction_id = lists.get(ballot_letters)
    if faction_id is not None:
        return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"knesset_party:{faction_id}")
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"cec_list:{knesset_number}:{ballot_letters}")
