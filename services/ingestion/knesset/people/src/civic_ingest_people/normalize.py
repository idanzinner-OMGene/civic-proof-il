"""Normalizer: raw ``KNS_Person`` row → validated ``NormalizedPerson``.

Uses deterministic UUIDs (``uuid5`` on the Knesset ``PersonID``) so
every run produces the same UUID for the same upstream record —
this is what makes the idempotent Neo4j ``MERGE`` actually idempotent
across re-runs.

Party + office joins live in a separate adapter (``KNS_Faction`` /
``KNS_PersonToPosition``, Phase-3), so the Person pipeline emits
``party=None`` / ``office=None`` for every row coming off
``KNS_Person`` — this matches the real upstream shape, not a
synthesised denormalised one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable

from civic_entity_resolution.normalize import normalize_hebrew

__all__ = [
    "NormalizedOffice",
    "NormalizedParty",
    "NormalizedPerson",
    "normalize_person",
    "PHASE2_UUID_NAMESPACE",
]


PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


@dataclass(frozen=True, slots=True)
class NormalizedParty:
    party_id: uuid.UUID
    canonical_name: str
    hebrew_name: str | None
    external_ids: dict[str, str]


@dataclass(frozen=True, slots=True)
class NormalizedOffice:
    office_id: uuid.UUID
    canonical_name: str
    office_type: str
    scope: str = "national"


@dataclass(frozen=True, slots=True)
class NormalizedPerson:
    person_id: uuid.UUID
    canonical_name: str
    hebrew_name: str | None
    external_ids: dict[str, str]
    is_current: bool = False
    party: NormalizedParty | None = None
    office: NormalizedOffice | None = None


def normalize_person(row: dict) -> Iterable[NormalizedPerson]:
    """Produce one :class:`NormalizedPerson` per row.

    ``party`` / ``office`` remain ``None`` because the source
    ``KNS_Person`` feed does not include them — those relationships
    are Phase-3 joins against ``KNS_PersonToPosition``.
    """

    ext_id = row["person_id_external"]
    hebrew = _hebrew_name(row)

    yield NormalizedPerson(
        person_id=_ext_uuid("knesset_person", ext_id),
        canonical_name=hebrew or f"person:{ext_id}",
        hebrew_name=hebrew,
        external_ids={"knesset_person_id": ext_id},
        is_current=bool(row.get("is_current") or False),
    )


def _hebrew_name(row: dict) -> str | None:
    first = normalize_hebrew(row.get("first_name_he") or "")
    last = normalize_hebrew(row.get("last_name_he") or "")
    pieces = [p for p in (first, last) if p]
    return " ".join(pieces) if pieces else None
