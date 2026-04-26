"""Shared ``mk_individual_id`` → ``PersonID`` lookup.

Two Phase-2.5 adapters (``committee_memberships`` and ``attendance``)
consume oknesset CSVs whose people-keyed columns store
``mk_individual_id`` — a local identifier on the oknesset pipeline
that is NOT the same as the canonical Knesset ``PersonID``. The
``mk_individual.csv`` dimension table at
``https://production.oknesset.org/pipelines/data/members/mk_individual/``
publishes both identifiers on every row and is the join key.

This helper caches the in-memory dict so adapters that resolve
thousands of ``mk_individual_id``\u00A0values per session pay the CSV
parse cost once per process.
"""

from __future__ import annotations

import csv
import io
from functools import lru_cache
from pathlib import Path

__all__ = ["LookupUnresolved", "MkIndividualLookup", "load_mk_individual_lookup"]


class LookupUnresolved(KeyError):
    """Raised when an ``mk_individual_id`` has no entry in the lookup."""


class MkIndividualLookup:
    """In-memory ``mk_individual_id`` → ``PersonID`` resolver.

    Construct via :func:`load_mk_individual_lookup`; callers should
    treat instances as immutable.
    """

    __slots__ = ("_by_mk_individual",)

    def __init__(self, by_mk_individual: dict[str, str]) -> None:
        self._by_mk_individual = by_mk_individual

    def __len__(self) -> int:
        return len(self._by_mk_individual)

    def __contains__(self, mk_individual_id: object) -> bool:
        return str(mk_individual_id) in self._by_mk_individual

    def resolve(self, mk_individual_id: str | int) -> str:
        """Return the canonical ``PersonID`` or raise :class:`LookupUnresolved`."""

        key = str(mk_individual_id)
        try:
            return self._by_mk_individual[key]
        except KeyError as exc:
            raise LookupUnresolved(key) from exc

    def get(self, mk_individual_id: str | int, default: str | None = None) -> str | None:
        """Return the ``PersonID`` if known, else ``default``."""

        return self._by_mk_individual.get(str(mk_individual_id), default)


def _parse_csv(payload: bytes | str) -> dict[str, str]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8-sig")
    out: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(payload)):
        mk_id = (row.get("mk_individual_id") or "").strip()
        person_id = (row.get("PersonID") or "").strip()
        if not mk_id or not person_id:
            continue
        out[mk_id] = person_id
    return out


def load_mk_individual_lookup(
    source: bytes | str | Path | None = None,
) -> MkIndividualLookup:
    """Load the lookup from bytes / a string path / or the default fixture.

    * ``source=None`` resolves to
      ``tests/fixtures/phase2/lookups/mk_individual/sample.csv`` — the
      version-controlled recording used by unit and integration tests.
      Production CLIs pass a freshly fetched ``bytes`` payload instead.
    * Callers that always want the default fixture path can use
      :func:`_load_default_lookup` (cached).
    """

    if source is None:
        return _load_default_lookup()
    if isinstance(source, (bytes, str)) and not _looks_like_path(source):
        return MkIndividualLookup(_parse_csv(source))
    path = Path(source)
    return MkIndividualLookup(_parse_csv(path.read_bytes()))


def _looks_like_path(payload: bytes | str) -> bool:
    if isinstance(payload, bytes):
        return False
    return "\n" not in payload and len(payload) < 1024


@lru_cache(maxsize=1)
def _load_default_lookup() -> MkIndividualLookup:
    default_path = (
        Path(__file__).resolve().parents[5]
        / "tests/fixtures/phase2/lookups/mk_individual/sample.csv"
    )
    return MkIndividualLookup(_parse_csv(default_path.read_bytes()))
