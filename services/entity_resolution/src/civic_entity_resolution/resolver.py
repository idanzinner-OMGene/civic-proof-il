"""Deterministic entity resolver MVP.

Consumes an entity-kind tag + a bag of candidate identifiers (external
IDs, Hebrew name, English name) and returns a :class:`ResolveResult`
indicating ``resolved`` / ``ambiguous`` / ``unresolved``. Ambiguous
results write to ``entity_candidates`` for the Phase-5 review queue.

Resolution order (steps 1-4 from the plan):

1. Official external IDs — lookup the Neo4j ``external_ids`` map on
   the appropriate label.
2. Exact normalized Hebrew match — Neo4j ``hebrew_name`` field.
3. Curated alias lookup (``entity_aliases`` table).
4. Transliteration normalization — fall back to English name / alias.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

import psycopg

from .normalize import normalize_hebrew, transliterate_hebrew

__all__ = ["Candidate", "ResolveResult", "resolve"]


EntityKind = Literal["person", "party", "office", "committee", "bill"]
Status = Literal["resolved", "ambiguous", "unresolved"]


_LABEL_BY_KIND = {
    "person": ("Person", "person_id"),
    "party": ("Party", "party_id"),
    "office": ("Office", "office_id"),
    "committee": ("Committee", "committee_id"),
    "bill": ("Bill", "bill_id"),
}


@dataclass(frozen=True, slots=True)
class Candidate:
    entity_id: uuid.UUID
    match_step: int
    match_reason: str
    score: int


@dataclass(frozen=True, slots=True)
class ResolveResult:
    status: Status
    entity_id: uuid.UUID | None
    candidates: tuple[Candidate, ...] = field(default=())

    def is_resolved(self) -> bool:
        return self.status == "resolved"


def resolve(
    kind: EntityKind,
    *,
    external_ids: dict[str, str] | None = None,
    hebrew_name: str | None = None,
    english_name: str | None = None,
    pg_conn: psycopg.Connection | None = None,
    neo4j_session: Any | None = None,
    record_ambiguous: bool = False,
) -> ResolveResult:
    """Resolve ``kind`` against the current canonical store.

    Parameters map 1:1 to the four resolution steps. Live DB connections
    are optional — callers may pass stubs in tests (see
    ``services/entity_resolution/tests/test_resolver.py``).
    """

    if kind not in _LABEL_BY_KIND:
        raise ValueError(f"unknown entity kind {kind!r}")

    candidates: list[Candidate] = []

    if external_ids and neo4j_session is not None:
        hit = _lookup_external_ids(neo4j_session, kind, external_ids)
        if hit:
            candidates.append(
                Candidate(
                    entity_id=hit,
                    match_step=1,
                    match_reason="external_id",
                    score=100,
                )
            )

    if not candidates and hebrew_name and neo4j_session is not None:
        normalized = normalize_hebrew(hebrew_name)
        hit = _lookup_hebrew_exact(neo4j_session, kind, normalized)
        if hit:
            candidates.append(
                Candidate(
                    entity_id=hit,
                    match_step=2,
                    match_reason="hebrew_exact",
                    score=95,
                )
            )

    if not candidates and hebrew_name and pg_conn is not None:
        alias_hits = _lookup_alias(
            pg_conn, kind, normalize_hebrew(hebrew_name), locale="he"
        )
        for entity_id, confidence in alias_hits:
            candidates.append(
                Candidate(
                    entity_id=entity_id,
                    match_step=3,
                    match_reason="alias_he",
                    score=confidence,
                )
            )

    if not candidates and english_name and pg_conn is not None:
        alias_hits = _lookup_alias(
            pg_conn, kind, english_name.strip().lower(), locale="en"
        )
        for entity_id, confidence in alias_hits:
            candidates.append(
                Candidate(
                    entity_id=entity_id,
                    match_step=3,
                    match_reason="alias_en",
                    score=confidence,
                )
            )

    if not candidates and hebrew_name and pg_conn is not None:
        translit = transliterate_hebrew(hebrew_name)
        if translit:
            alias_hits = _lookup_alias(pg_conn, kind, translit, locale="en")
            for entity_id, confidence in alias_hits:
                candidates.append(
                    Candidate(
                        entity_id=entity_id,
                        match_step=4,
                        match_reason="transliteration",
                        score=max(confidence - 10, 0),
                    )
                )

    if not candidates:
        return ResolveResult(status="unresolved", entity_id=None)

    unique_ids = {c.entity_id for c in candidates}
    if len(unique_ids) == 1:
        winner = max(candidates, key=lambda c: c.score)
        return ResolveResult(
            status="resolved",
            entity_id=winner.entity_id,
            candidates=tuple(candidates),
        )

    if record_ambiguous and pg_conn is not None:
        _write_entity_candidates(pg_conn, kind, candidates)

    return ResolveResult(
        status="ambiguous",
        entity_id=None,
        candidates=tuple(candidates),
    )


def _lookup_external_ids(
    session: Any,
    kind: EntityKind,
    external_ids: dict[str, str],
) -> uuid.UUID | None:
    label, id_field = _LABEL_BY_KIND[kind]
    for scheme, value in external_ids.items():
        cypher = (
            f"MATCH (n:{label}) "
            "WHERE n.external_ids IS NOT NULL "
            "  AND n.external_ids CONTAINS $needle "
            f"RETURN n.{id_field} AS id LIMIT 1"
        )
        needle = json.dumps({scheme: value})[1:-1]
        for record in session.run(cypher, needle=needle):
            return uuid.UUID(record["id"])
    return None


def _lookup_hebrew_exact(
    session: Any,
    kind: EntityKind,
    hebrew: str,
) -> uuid.UUID | None:
    label, id_field = _LABEL_BY_KIND[kind]
    cypher = (
        f"MATCH (n:{label} {{hebrew_name: $name}}) "
        f"RETURN n.{id_field} AS id LIMIT 2"
    )
    rows = list(session.run(cypher, name=hebrew))
    if len(rows) == 1:
        return uuid.UUID(rows[0]["id"])
    return None


def _lookup_alias(
    pg_conn: psycopg.Connection,
    kind: EntityKind,
    alias_text: str,
    *,
    locale: str,
) -> list[tuple[uuid.UUID, int]]:
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT canonical_entity_id, confidence
              FROM entity_aliases
             WHERE entity_kind = %s
               AND alias_text = %s
               AND alias_locale = %s
            """,
            (kind, alias_text, locale),
        )
        return [(uuid.UUID(str(r[0])), int(r[1])) for r in cur.fetchall()]


def _write_entity_candidates(
    pg_conn: psycopg.Connection,
    kind: EntityKind,
    candidates: Iterable[Candidate],
    *,
    mention_text: str | None = None,
) -> None:
    """Write ambiguous ``person`` candidates to the Phase-1 table.

    The Phase-1 ``entity_candidates`` schema (from
    ``0002_phase1_domain_schema.py`` lines 187-220) is person-scoped —
    columns ``mention_text``, ``resolved_person_id``, ``confidence``
    (0-1 REAL), ``method``, ``evidence``. For kinds other than
    ``person`` we skip the write; Phase-3 will extend the schema when
    review UIs exist.
    """

    if kind != "person":
        return

    with pg_conn.cursor() as cur:
        for c in candidates:
            cur.execute(
                """
                INSERT INTO entity_candidates
                  (candidate_id, mention_text, resolved_person_id,
                   confidence, method, evidence)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    mention_text or "",
                    str(c.entity_id),
                    c.score / 100.0,
                    c.match_reason,
                    json.dumps({"match_step": c.match_step}),
                ),
            )
