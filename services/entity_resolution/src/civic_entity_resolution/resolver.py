"""Entity resolver — deterministic steps 1-5 with an LLM step-6 seam.

Consumes an entity-kind tag + a bag of candidate identifiers (external
IDs, Hebrew name, English name) and returns a :class:`ResolveResult`
indicating ``resolved`` / ``ambiguous`` / ``unresolved``. Ambiguous
results write to ``entity_candidates`` (polymorphic as of migration
0005) for the review queue.

Resolution order (plan lines 357-363):

1. Official external IDs — lookup the Neo4j ``external_ids`` map on
   the appropriate label.
2. Exact normalized Hebrew match — Neo4j ``hebrew_name`` field.
3. Curated alias lookup (``entity_aliases`` table).
4. Transliteration normalization — fall back to English name / alias.
5. Fuzzy matching on Hebrew/English names via ``rapidfuzz``. Scored in
   [0, 100]; only returned as ``resolved`` when the top score clears
   ``FUZZY_RESOLVE_THRESHOLD`` AND the gap to second-best exceeds
   ``FUZZY_MARGIN``.
6. LLM fallback — optional ``LLMEntityTiebreaker`` protocol. ONLY
   picks between already-retrieved candidates; never invents a new
   entity. Gated on ``record_ambiguous=True``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Protocol, Sequence

import psycopg

from .normalize import normalize_hebrew, transliterate_hebrew

__all__ = [
    "Candidate",
    "LLMEntityTiebreaker",
    "ResolveResult",
    "resolve",
    "FUZZY_RESOLVE_THRESHOLD",
    "FUZZY_MARGIN",
]

FUZZY_RESOLVE_THRESHOLD: int = 88
FUZZY_MARGIN: int = 7


class LLMEntityTiebreaker(Protocol):
    """Protocol for the step-6 LLM fallback.

    Given a list of already-retrieved candidates (by step 5 fuzzy
    match), the tiebreaker returns the chosen ``entity_id`` or ``None``
    if it cannot confidently pick one. It MUST NOT invent a candidate
    that isn't already in the list.
    """

    def pick(
        self,
        kind: str,
        hebrew_name: str | None,
        english_name: str | None,
        candidates: Sequence["Candidate"],
    ) -> uuid.UUID | None:
        ...


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
    llm_tiebreaker: LLMEntityTiebreaker | None = None,
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

    if not candidates and neo4j_session is not None and (hebrew_name or english_name):
        fuzzy_hits = _lookup_fuzzy(neo4j_session, kind, hebrew_name, english_name)
        candidates.extend(fuzzy_hits)

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

    fuzzy = [c for c in candidates if c.match_step == 5]
    if fuzzy:
        sorted_fuzzy = sorted(fuzzy, key=lambda c: c.score, reverse=True)
        top = sorted_fuzzy[0]
        second = sorted_fuzzy[1].score if len(sorted_fuzzy) > 1 else 0
        if top.score >= FUZZY_RESOLVE_THRESHOLD and (top.score - second) >= FUZZY_MARGIN:
            return ResolveResult(
                status="resolved",
                entity_id=top.entity_id,
                candidates=tuple(candidates),
            )

    if llm_tiebreaker is not None:
        pick = llm_tiebreaker.pick(kind, hebrew_name, english_name, candidates)
        if pick is not None and pick in unique_ids:
            return ResolveResult(
                status="resolved",
                entity_id=pick,
                candidates=tuple(candidates),
            )

    if record_ambiguous and pg_conn is not None:
        _write_entity_candidates(
            pg_conn, kind, candidates, mention_text=hebrew_name or english_name
        )

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


def _lookup_fuzzy(
    session: Any,
    kind: EntityKind,
    hebrew_name: str | None,
    english_name: str | None,
) -> list[Candidate]:
    """Step 5: fuzzy Hebrew / English name match against Neo4j.

    Uses rapidfuzz's ``fuzz.ratio`` on normalized strings. Pulls the
    first 500 candidates for the label (labels are relatively small —
    hundreds-to-low-thousands in practice); scored and filtered
    in-process. Returns the top-5 candidates above a floor of 60 so
    the caller can inspect second-best for margin analysis.
    """

    try:  # rapidfuzz is a new Phase-3 dependency
        from rapidfuzz import fuzz  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return []

    label, id_field = _LABEL_BY_KIND[kind]
    cypher = (
        f"MATCH (n:{label}) "
        f"RETURN n.{id_field} AS id, n.hebrew_name AS he, "
        "n.canonical_name AS cn, n.english_name AS en "
        "LIMIT 500"
    )
    normalized_he = normalize_hebrew(hebrew_name) if hebrew_name else ""
    normalized_en = (english_name or "").strip().lower()
    scored: list[tuple[int, Candidate]] = []
    for record in session.run(cypher):
        node_id = record["id"]
        if node_id is None:
            continue
        node_he = normalize_hebrew(record.get("he") or "")
        node_cn = (record.get("cn") or "").strip().lower()
        node_en = (record.get("en") or "").strip().lower()

        score_he = fuzz.ratio(normalized_he, node_he) if normalized_he and node_he else 0
        score_cn = fuzz.ratio(normalized_en, node_cn) if normalized_en and node_cn else 0
        score_en = fuzz.ratio(normalized_en, node_en) if normalized_en and node_en else 0

        partial_he = (
            fuzz.partial_ratio(normalized_he, node_he)
            if normalized_he and node_he
            else 0
        )

        best_exact = max(score_he, score_cn, score_en)
        best = max(best_exact, int(partial_he * 0.92))

        if best < 60:
            continue

        reason = "fuzzy_he"
        if score_en >= score_he and score_en >= score_cn:
            reason = "fuzzy_en"
        elif score_cn > score_he:
            reason = "fuzzy_cn"
        if partial_he * 0.92 > best_exact:
            reason = "fuzzy_partial_he"

        scored.append(
            (
                best,
                Candidate(
                    entity_id=uuid.UUID(node_id),
                    match_step=5,
                    match_reason=reason,
                    score=best,
                ),
            )
        )
    scored.sort(key=lambda p: p[0], reverse=True)
    return [c for _, c in scored[:5]]


def _write_entity_candidates(
    pg_conn: psycopg.Connection,
    kind: EntityKind,
    candidates: Iterable[Candidate],
    *,
    mention_text: str | None = None,
) -> None:
    """Write ambiguous candidates to the polymorphic ``entity_candidates`` table.

    After migration 0005 (``0005_polymorphic_entity_candidates``) the
    table carries both ``entity_kind`` and ``canonical_entity_id``, so
    non-person kinds (party, office, committee, bill) are now
    persisted alongside persons for the reviewer queue.
    """

    with pg_conn.cursor() as cur:
        for c in candidates:
            cur.execute(
                """
                INSERT INTO entity_candidates
                  (candidate_id, mention_text, entity_kind, canonical_entity_id,
                   confidence, method, evidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    mention_text or "",
                    kind,
                    str(c.entity_id),
                    c.score / 100.0,
                    c.match_reason,
                    json.dumps({"match_step": c.match_step}),
                ),
            )
