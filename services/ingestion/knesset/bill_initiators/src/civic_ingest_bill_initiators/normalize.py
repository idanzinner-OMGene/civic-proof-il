"""Normalize ``KNS_BillInitiator`` rows → :class:`NormalizedBillSponsorship`.

Deterministic UUIDs share the same namespace as ``civic_ingest_people``
and ``civic_ingest_sponsorships``, so MERGE on ``person_id`` / ``bill_id``
collapses this adapter's stubs onto the full nodes ingested by those
earlier adapters.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable

__all__ = [
    "NormalizedBillSponsorship",
    "PHASE2_UUID_NAMESPACE",
    "normalize_bill_initiator",
]


PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


@dataclass(frozen=True, slots=True)
class NormalizedBillSponsorship:
    bill_id: uuid.UUID
    person_id: uuid.UUID
    bill_id_external: str
    person_id_external: str
    ordinal: int | None = None


def normalize_bill_initiator(row: dict) -> Iterable[NormalizedBillSponsorship]:
    bill_ext = row["bill_id_external"]
    person_ext = row["person_id_external"]
    yield NormalizedBillSponsorship(
        bill_id=_ext_uuid("knesset_bill", bill_ext),
        person_id=_ext_uuid("knesset_person", person_ext),
        bill_id_external=bill_ext,
        person_id_external=person_ext,
        ordinal=row.get("ordinal"),
    )
