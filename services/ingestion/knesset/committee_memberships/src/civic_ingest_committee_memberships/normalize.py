"""Normalize ``mk_individual_committees.csv`` rows → :class:`NormalizedCommitteeMembership`.

Emits one membership per row, dropping rows whose ``mk_individual_id``
can't be resolved to a canonical ``PersonID`` via the
:class:`civic_ingest.MkIndividualLookup`.

Dates on the upstream CSV are calendar dates (``YYYY-MM-DD``). Neo4j's
``datetime()`` constructor only accepts full ISO-8601 timestamps, so we
promote dates to midnight UTC on the valid_from / valid_to properties.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable

from civic_ingest import MkIndividualLookup

__all__ = [
    "NormalizedCommitteeMembership",
    "PHASE2_UUID_NAMESPACE",
    "normalize_committee_membership",
]


PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


def _as_iso_datetime(date_str: str | None) -> str | None:
    if date_str is None:
        return None
    date_str = date_str.strip()
    if not date_str:
        return None
    if "T" in date_str:
        return date_str
    if len(date_str) == 10:
        return f"{date_str}T00:00:00"
    return date_str


@dataclass(frozen=True, slots=True)
class NormalizedCommitteeMembership:
    person_id: uuid.UUID
    committee_id: uuid.UUID
    mk_individual_id: str
    committee_id_external: str
    committee_name: str | None
    position_name: str | None
    valid_from: str
    valid_to: str | None
    knesset: int | None


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_committee_membership(
    row: dict,
    *,
    lookup: MkIndividualLookup,
) -> Iterable[NormalizedCommitteeMembership]:
    mk_id = row["mk_individual_id"]
    person_external = lookup.get(mk_id)
    if person_external is None:
        return

    valid_from = _as_iso_datetime(row.get("start_date"))
    if valid_from is None:
        return

    yield NormalizedCommitteeMembership(
        person_id=_ext_uuid("knesset_person", person_external),
        committee_id=_ext_uuid(
            "knesset_committee", row["committee_id_external"]
        ),
        mk_individual_id=mk_id,
        committee_id_external=row["committee_id_external"],
        committee_name=row.get("committee_name"),
        position_name=row.get("position_name"),
        valid_from=valid_from,
        valid_to=_as_iso_datetime(row.get("finish_date")),
        knesset=_coerce_int(row.get("knesset")),
    )
