"""Phase-2.5 committee-memberships adapter (Tier-2).

Reads the oknesset ``mk_individual_committees.csv`` pipeline CSV and
emits ``(:Person)-[:MEMBER_OF_COMMITTEE]->(:Committee)`` edges.

Why this source and not Tier-1 OData: the Knesset OData
``KNS_PersonToPosition`` feed declares ``CommitteeID`` /
``CommitteeName`` columns but 0 of 11,090 rows have them populated
(April 2026 data). Committee memberships are only published as
structured data through the oknesset open-government mirror.

Joining quirk: the CSV keys rows by ``mk_individual_id`` (an oknesset-
local identifier), NOT the canonical Knesset ``PersonID``. The
``mk_individual.csv`` dimension table resolves the two; see
:mod:`civic_ingest.mk_individual_lookup`.
"""

from __future__ import annotations

from .normalize import (
    PHASE2_UUID_NAMESPACE,
    NormalizedCommitteeMembership,
    normalize_committee_membership,
)
from .parse import parse_committee_memberships
from .upsert import upsert_committee_membership

__all__ = [
    "NormalizedCommitteeMembership",
    "PHASE2_UUID_NAMESPACE",
    "normalize_committee_membership",
    "parse_committee_memberships",
    "upsert_committee_membership",
]
