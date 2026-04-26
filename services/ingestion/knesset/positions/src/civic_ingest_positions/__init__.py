"""Phase-2.5 positions adapter.

Reads ``KNS_PersonToPosition`` (Tier-1 OData) and emits, per row,
zero-to-two relationship lanes:

* ``(:Person)-[:MEMBER_OF]->(:Party)`` when ``FactionID`` is populated.
* ``(:Person)-[:HELD_OFFICE]->(:Office)`` when ``PositionID`` is populated
  (always — ``PositionID`` is NOT NULL on every upstream row).

``KNS_PersonToPosition`` declares a ``CommitteeID`` column but 0 of
11,090 rows (April 2026) have it populated — committee memberships
live in a different source (oknesset ``mk_individual_committees.csv``,
ingested by :mod:`civic_ingest_committee_memberships`). This adapter
therefore emits no committee edges.
"""

from __future__ import annotations

from .normalize import (
    PHASE2_UUID_NAMESPACE,
    NormalizedOfficeHeld,
    NormalizedPartyMembership,
    NormalizedPositionBundle,
    normalize_position,
)
from .parse import parse_positions
from .upsert import upsert_position

__all__ = [
    "NormalizedOfficeHeld",
    "NormalizedPartyMembership",
    "NormalizedPositionBundle",
    "PHASE2_UUID_NAMESPACE",
    "normalize_position",
    "parse_positions",
    "upsert_position",
]
