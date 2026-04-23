"""Normalize a ``KNS_Bill`` row → ``NormalizedBill``.

The real OData feed returns flat bill metadata only — initiators live
on ``KNS_BillInitiator`` and are joined by Phase-3. The normalized
bundle therefore always has an empty ``sponsorships`` tuple, matching
the real upstream shape.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterable

PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


@dataclass(frozen=True, slots=True)
class NormalizedSponsorship:
    person_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class NormalizedBill:
    bill_id: uuid.UUID
    title: str
    knesset_number: int | None
    status: str | None
    sub_type: str | None = None
    publication_date: str | None = None
    sponsorships: tuple[NormalizedSponsorship, ...] = field(default=())


def normalize_bill(row: dict) -> Iterable[NormalizedBill]:
    ext = row["bill_id_external"]
    bill_id = _ext_uuid("knesset_bill", ext)

    yield NormalizedBill(
        bill_id=bill_id,
        title=(row.get("title_he") or f"bill:{ext}").strip(),
        knesset_number=row.get("knesset_number"),
        status=None
        if row.get("status_id") is None
        else f"status:{row['status_id']}",
        sub_type=row.get("sub_type"),
        publication_date=row.get("publication_date"),
        sponsorships=(),  # KNS_BillInitiator join is Phase-3.
    )
