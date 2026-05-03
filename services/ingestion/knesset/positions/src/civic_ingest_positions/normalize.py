"""Normalize ``KNS_PersonToPosition`` rows → :class:`NormalizedPositionBundle`.

Each upstream row expands into at most two lanes that the upsert step
writes to Neo4j:

* ``party`` — present iff ``FactionID`` is populated.
* ``office`` — present iff ``PositionID`` is populated (always true in
  practice). Minister / deputy-minister appointments carry an extra
  ``GovMinistryID`` that makes the office distinct per ministry, so the
  office UUID is ``uuid5("knesset_office:{PositionID}:{GovMinistryID or '-'}")``.
* ``position_term`` — present iff the office lane is present.  A
  first-class V2 ``PositionTerm`` node keyed by
  ``uuid5("knesset_position_term:{PersonToPositionID}")`` so that
  date-aware office claims can be verified against time-bounded holdings
  rather than a bare ``HELD_OFFICE`` edge.

Deterministic UUIDs share the same ``PHASE2_UUID_NAMESPACE`` as every
other Phase-2 adapter, so stubs created by the votes / committee
memberships / attendance adapters for the same underlying ``PersonID``
/ ``FactionID`` / ``CommitteeID`` collapse into one node under MERGE.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable

__all__ = [
    "NormalizedOfficeHeld",
    "NormalizedPartyMembership",
    "NormalizedPositionBundle",
    "NormalizedPositionTerm",
    "PHASE2_UUID_NAMESPACE",
    "normalize_position",
]


PHASE2_UUID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def _ext_uuid(kind: str, ext_id: str) -> uuid.UUID:
    return uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}")


# PositionID → controlled-vocabulary office_type. Values observed in the
# live table: 43 (historical MK), 48 (deputy Knesset speaker / similar),
# 50 (Deputy Prime Minister and similar), 54 (MK / Knesset member),
# 61 (historical role), etc. Unknown IDs fall back to the row's
# ``duty_desc`` string or "unknown".
_POSITION_TYPE: dict[int, str] = {
    30: "prime_minister",
    39: "committee_chair",
    42: "committee_member",
    43: "mk",
    48: "deputy_speaker",
    49: "minister",
    50: "deputy_prime_minister",
    51: "deputy_minister",
    54: "mk",
    61: "mk",
    65: "committee_chair",
    67: "committee_member",
}

# office_type values that indicate a government appointment (as opposed to
# a Knesset role). Used to populate ``appointing_body`` on PositionTerm.
_GOVERNMENT_OFFICE_TYPES = frozenset(
    {"prime_minister", "minister", "deputy_prime_minister", "deputy_minister"}
)


def _office_type(position_id: int | None, duty_desc: str | None) -> str:
    if position_id is not None and position_id in _POSITION_TYPE:
        return _POSITION_TYPE[position_id]
    if duty_desc:
        return duty_desc.strip()
    return "unknown"


def _office_canonical_name(
    position_type: str,
    gov_ministry_name: str | None,
    duty_desc: str | None,
) -> str | None:
    if gov_ministry_name and position_type in (
        "minister",
        "deputy_minister",
        "deputy_prime_minister",
        "prime_minister",
    ):
        return gov_ministry_name
    if duty_desc:
        return duty_desc
    return None


@dataclass(frozen=True, slots=True)
class NormalizedPartyMembership:
    party_id: uuid.UUID
    party_name: str
    valid_from: str
    valid_to: str | None


@dataclass(frozen=True, slots=True)
class NormalizedOfficeHeld:
    office_id: uuid.UUID
    canonical_name: str | None
    office_type: str
    scope: str
    valid_from: str
    valid_to: str | None


@dataclass(frozen=True, slots=True)
class NormalizedPositionTerm:
    """V2 first-class time-bounded role holding.

    Keyed by ``knesset_position_term:{PersonToPositionID}`` so every row in
    ``KNS_PersonToPosition`` maps to exactly one ``PositionTerm`` node.
    Only emitted when the office lane is present (``PositionID`` populated).
    """

    position_term_id: uuid.UUID
    person_id: uuid.UUID
    office_id: uuid.UUID
    appointing_body: str | None
    valid_from: str
    valid_to: str | None
    is_acting: bool


@dataclass(frozen=True, slots=True)
class NormalizedPositionBundle:
    person_id: uuid.UUID
    person_to_position_id_external: str
    party: NormalizedPartyMembership | None = None
    office: NormalizedOfficeHeld | None = None
    position_term: NormalizedPositionTerm | None = None


def normalize_position(row: dict) -> Iterable[NormalizedPositionBundle]:
    person_ext = row["person_id_external"]
    person_id = _ext_uuid("knesset_person", person_ext)

    start = row.get("start_date")
    finish = row.get("finish_date")
    if not start:
        # ``valid_from`` is required by both member_of.cypher and
        # held_office.cypher (WHERE valid_from IS NOT NULL). A row
        # without StartDate cannot produce either edge.
        return

    party: NormalizedPartyMembership | None = None
    if row.get("faction_id_external"):
        party = NormalizedPartyMembership(
            party_id=_ext_uuid("knesset_party", row["faction_id_external"]),
            party_name=(row.get("faction_name") or "").strip()
            or f"party:{row['faction_id_external']}",
            valid_from=start,
            valid_to=finish,
        )

    office: NormalizedOfficeHeld | None = None
    position_term: NormalizedPositionTerm | None = None
    position_id = row.get("position_id")
    if position_id is not None:
        gov_id = row.get("gov_ministry_id")
        office_ext = f"{position_id}:{gov_id or '-'}"
        office_type = _office_type(position_id, row.get("duty_desc"))
        office_id = _ext_uuid("knesset_office", office_ext)
        office = NormalizedOfficeHeld(
            office_id=office_id,
            canonical_name=_office_canonical_name(
                office_type,
                row.get("gov_ministry_name"),
                row.get("duty_desc"),
            ),
            office_type=office_type,
            scope="national",
            valid_from=start,
            valid_to=finish,
        )
        appointing_body = (
            "government" if office_type in _GOVERNMENT_OFFICE_TYPES else "knesset"
        )
        position_term = NormalizedPositionTerm(
            position_term_id=_ext_uuid(
                "knesset_position_term", row["person_to_position_id_external"]
            ),
            person_id=person_id,
            office_id=office_id,
            appointing_body=appointing_body,
            valid_from=start,
            valid_to=finish,
            is_acting=False,
        )

    if party is None and office is None:
        return

    yield NormalizedPositionBundle(
        person_id=person_id,
        person_to_position_id_external=row["person_to_position_id_external"],
        party=party,
        office=office,
        position_term=position_term,
    )
