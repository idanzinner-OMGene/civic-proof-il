"""Phase-2 committees + memberships adapter.

Reads ``KNS_Committee`` + ``KNS_MemberCommittee`` from Knesset OData
V4, yields :class:`NormalizedCommittee` bundles containing the
Committee node plus zero-or-more MembershipTerm + MEMBER_OF_COMMITTEE
edges.
"""

from __future__ import annotations

from .normalize import NormalizedCommittee, NormalizedMembership, normalize_committee
from .parse import parse_committees
from .upsert import upsert_committee

__all__ = [
    "NormalizedCommittee",
    "NormalizedMembership",
    "normalize_committee",
    "parse_committees",
    "upsert_committee",
]
