"""Phase-2 people-and-roles adapter.

Reads ``KNS_Person`` + ``KNS_PersonToPosition`` from Knesset OData V4,
normalizes each row, and upserts :class:`Person`, :class:`Party`,
:class:`Office` nodes plus ``MEMBER_OF`` / ``HELD_OFFICE`` relationships.
"""

from __future__ import annotations

from .normalize import NormalizedPerson, normalize_person
from .parse import parse_persons
from .upsert import upsert_person

__all__ = [
    "NormalizedPerson",
    "normalize_person",
    "parse_persons",
    "upsert_person",
]
