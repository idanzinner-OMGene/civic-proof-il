"""Normalize a ``KNS_Committee`` row into a graph-ready bundle.

The real Knesset OData feed does not embed members on a committee
row (membership lives on ``KNS_PersonToPosition``). A normalized
committee therefore always has an empty ``memberships`` tuple; the
Phase-3 pipeline fills it in by joining the positions feed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterable

PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


@dataclass(frozen=True, slots=True)
class NormalizedMembership:
    membership_term_id: uuid.UUID
    person_id: uuid.UUID
    committee_id: uuid.UUID
    valid_from: str | None
    valid_to: str | None


@dataclass(frozen=True, slots=True)
class NormalizedCommittee:
    committee_id: uuid.UUID
    canonical_name: str
    hebrew_name: str | None
    knesset_number: int | None = None
    committee_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    memberships: tuple[NormalizedMembership, ...] = field(default=())


def normalize_committee(row: dict) -> Iterable[NormalizedCommittee]:
    ext = row["committee_id_external"]
    committee_id = _ext_uuid("knesset_committee", ext)

    yield NormalizedCommittee(
        committee_id=committee_id,
        canonical_name=row.get("name_he") or f"committee:{ext}",
        hebrew_name=row.get("name_he"),
        knesset_number=row.get("knesset_number"),
        committee_type=row.get("committee_type"),
        start_date=row.get("start_date"),
        end_date=row.get("end_date"),
        is_current=bool(row.get("is_current") or False),
        memberships=(),
    )
