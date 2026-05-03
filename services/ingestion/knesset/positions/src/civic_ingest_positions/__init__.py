"""Phase-2.5 positions adapter — V2 extended.

Reads ``KNS_PersonToPosition`` (Tier-1 OData) and emits, per row,
zero-to-three relationship lanes:

* ``(:Person)-[:MEMBER_OF]->(:Party)`` when ``FactionID`` is populated.
* ``(:Person)-[:HELD_OFFICE]->(:Office)`` when ``PositionID`` is populated
  (always — ``PositionID`` is NOT NULL on every upstream row).
* ``(:Person)-[:HAS_POSITION_TERM]->(:PositionTerm)-[:ABOUT_OFFICE]->(:Office)``
  when ``PositionID`` is populated (V2 first-class time-bounded role node).

The ``PositionTerm`` node is keyed by
``uuid5(PHASE2_UUID_NAMESPACE, "knesset_position_term:{PersonToPositionID}")``,
which is deterministic per source row.  It carries ``valid_from``,
``valid_to``, ``appointing_body`` (``"government"`` for ministerial roles,
``"knesset"`` for MK / committee roles), and ``is_acting=False`` (Knesset
OData does not expose an acting-role flag).

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
    NormalizedPositionTerm,
    normalize_position,
)
from .parse import parse_positions
from .upsert import upsert_position

__all__ = [
    "NormalizedOfficeHeld",
    "NormalizedPartyMembership",
    "NormalizedPositionBundle",
    "NormalizedPositionTerm",
    "PHASE2_UUID_NAMESPACE",
    "normalize_position",
    "parse_positions",
    "upsert_position",
]
