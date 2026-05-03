"""Dependency-injection seams for the /claims/verify pipeline.

The router is deliberately decoupled from the concrete Postgres /
Neo4j / OpenSearch connection objects; it talks to a
:class:`VerifyPipeline` interface and FastAPI's dependency system
supplies either the real or a stub implementation. Tests override
``get_pipeline`` to supply deterministic fakes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol

import psycopg
from civic_claim_decomp import decompose
from civic_claim_decomp.checkability import CheckabilityInputs, classify
from civic_claim_decomp.decomposer import DecomposedClaim
from civic_retrieval import (
    GraphEvidence,
    LexicalEvidence,
    RerankScore,
    rerank,
)
from civic_temporal import normalize_time_scope
from civic_verification import VerdictInputs, bundle_provenance, decide_verdict

Language = Literal["he", "en"]

# Maps FK slot names to the entity kind used by civic_entity_resolution.
_SLOT_TO_KIND: dict[str, str] = {
    "speaker_person_id": "person",
    "target_person_id": "person",
    "bill_id": "bill",
    "committee_id": "committee",
    "office_id": "office",
    "party_id": "party",
}


def _parse_int_slot(value: object | None) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _parse_expect_passed_threshold(value: object | None) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no"}:
        return False
    return None


@dataclass(frozen=True)
class ResolutionResult:
    """Combined outcome of entity resolution for a single claim.

    ``slot_statuses`` drives the checkability classifier; ``resolved_slots``
    replaces text names with canonical UUID strings for graph retrieval.
    """

    slot_statuses: dict[str, str] = field(default_factory=dict)
    resolved_slots: dict[str, Any] = field(default_factory=dict)


class GraphRetriever(Protocol):
    def retrieve(self, claim_type: str, *, params: dict[str, Any]) -> list[GraphEvidence]: ...


class LexicalRetriever(Protocol):
    def search(
        self,
        query_text: str,
        *,
        top_k: int = 20,
        filters: Mapping[str, Any] | None = None,
    ) -> list[LexicalEvidence]: ...


class EntityResolver(Protocol):
    def resolve(self, claim: DecomposedClaim) -> ResolutionResult:
        """Return statuses and resolved UUID slots for the claim."""


class LiveEntityResolver:
    """Concrete resolver that runs the six-step civic_entity_resolution ladder.

    Persons and committees carry ``hebrew_name`` in Neo4j and resolve via
    exact Hebrew match (step 2) or fuzzy (step 5).  Bills and offices are
    matched by ``title`` / ``canonical_name`` respectively via a direct
    Cypher query when the standard ladder comes up empty.

    The resolver is instantiated once per lifespan with a driver factory;
    it opens a short-lived session per claim to avoid holding a session
    across async boundaries.
    """

    def __init__(
        self,
        neo4j_driver: Any,
        pg_conn: psycopg.Connection | None = None,
    ) -> None:
        self._driver = neo4j_driver
        self._pg_conn = pg_conn

    @staticmethod
    def _is_hebrew(text: str) -> bool:
        """Return True if ``text`` contains any Hebrew character."""
        return any("\u0590" <= ch <= "\u05FF" for ch in text)

    def resolve(self, claim: DecomposedClaim) -> ResolutionResult:
        from civic_entity_resolution import resolve as _resolve

        statuses: dict[str, str] = {}
        resolved: dict[str, Any] = dict(claim.slots)

        with self._driver.session() as session:
            for slot, kind in _SLOT_TO_KIND.items():
                value = claim.slots.get(slot)
                if value is None:
                    continue

                if self._is_hebrew(value):
                    resolve_kwargs: dict[str, Any] = {"hebrew_name": value}
                else:
                    resolve_kwargs = {"english_name": value}

                result = _resolve(
                    kind,  # type: ignore[arg-type]
                    **resolve_kwargs,
                    neo4j_session=session,
                    pg_conn=self._pg_conn,
                )
                if result.is_resolved() and result.entity_id is not None:
                    statuses[slot] = "resolved"
                    resolved[slot] = str(result.entity_id)
                else:
                    fallback_id = self._fallback_resolve(session, kind, value)
                    if fallback_id is not None:
                        statuses[slot] = "resolved"
                        resolved[slot] = fallback_id
                    else:
                        statuses[slot] = result.status

        return ResolutionResult(slot_statuses=statuses, resolved_slots=resolved)

    @staticmethod
    def _fallback_resolve(session: Any, kind: str, text: str) -> str | None:
        """CONTAINS-based fallback for all entity kinds.

        Handles partial names (e.g. "הכלכלה" → "ועדת הכלכלה") and
        title-based matching for bills/offices. Returns None when zero
        or more-than-one candidates match (ambiguous).
        """
        label_id_map: dict[str, tuple[str, str, list[str]]] = {
            "bill": ("Bill", "bill_id", ["title", "hebrew_name"]),
            "office": ("Office", "office_id", ["canonical_name", "hebrew_name"]),
            "committee": ("Committee", "committee_id", ["hebrew_name", "canonical_name"]),
            "person": ("Person", "person_id", ["hebrew_name", "canonical_name", "english_name"]),
            "party": ("Party", "party_id", ["hebrew_name", "canonical_name", "english_name"]),
        }

        if kind not in label_id_map:
            return None

        label, id_field, name_fields = label_id_map[kind]
        conditions = " OR ".join(
            f"toLower(n.{f}) CONTAINS toLower($t)" for f in name_fields
        )
        cypher = (
            f"MATCH (n:{label}) WHERE {conditions} "
            f"RETURN n.{id_field} AS id LIMIT 2"
        )
        rows = list(session.run(cypher, t=text))
        if len(rows) == 1:
            return str(rows[0]["id"])
        return None


@dataclass
class VerifyPipeline:
    """Composes decomposition → resolution → retrieval → verdict.

    Every collaborator is optional so the route can respond even when
    backing stores are offline (the verdict engine abstains with
    ``insufficient_evidence`` when no evidence is retrieved).
    """

    graph: GraphRetriever | None = None
    lexical: LexicalRetriever | None = None
    resolver: EntityResolver | None = None
    default_language: Language = "he"
    review_connection: psycopg.Connection | None = None

    def verify(self, statement: str, language: Language | None = None) -> list[dict[str, Any]]:
        lang: Language = language or self.default_language
        result = decompose(statement, lang)
        bundles: list[dict[str, Any]] = []
        for claim in result.claims:
            resolution = self._resolve(claim)
            scope = normalize_time_scope(claim.time_phrase, language=lang)
            checkability = classify(
                CheckabilityInputs(
                    claim_type=claim.claim_type,
                    slots=claim.slots,
                    slot_resolver_status=resolution.slot_statuses,
                    time_granularity=scope.granularity,
                )
            )
            ranked = self._retrieve(claim, resolution.resolved_slots, scope.model_dump())
            outcome = decide_verdict(
                VerdictInputs(
                    claim_id=str(claim.claim_id),
                    claim_type=claim.claim_type,
                    checkability=checkability,
                    ranked_evidence=ranked,
                    expected_vote_value=claim.slots.get("vote_value"),
                    expected_seats=_parse_int_slot(claim.slots.get("expected_seats")),
                    expect_passed_threshold=_parse_expect_passed_threshold(
                        claim.slots.get("expect_passed_threshold")
                    ),
                    claim_time_scope=scope.model_dump(),
                )
            )
            if self.review_connection is not None:
                from civic_review.conflict import maybe_open_conflict_task

                maybe_open_conflict_task(
                    self.review_connection,
                    claim_id=str(claim.claim_id),
                    outcome=outcome,
                    ranked=ranked,
                )
            bundle = bundle_provenance(
                outcome,
                ranked,
                claim_id=str(claim.claim_id),
                claim_type=claim.claim_type,
            )
            payload = bundle.as_dict()
            payload["claim"] = {
                "claim_id": str(claim.claim_id),
                "claim_type": claim.claim_type,
                "normalized_text": claim.normalized_text,
                "slots": claim.slots,
                "time_phrase": claim.time_phrase,
                "time_scope": scope.model_dump(),
                "checkability": checkability,
                "method": claim.method,
            }
            bundles.append(payload)
        return bundles

    def _resolve(self, claim: DecomposedClaim) -> ResolutionResult:
        """Resolve entity slots — returns both statuses (for checkability) and UUIDs."""
        if self.resolver is None:
            # No live resolver: treat all present slots as "resolved" (offline mode).
            statuses = {slot: "resolved" for slot, v in claim.slots.items() if v is not None}
            return ResolutionResult(slot_statuses=statuses, resolved_slots=dict(claim.slots))
        try:
            return self.resolver.resolve(claim)
        except Exception:  # noqa: BLE001
            return ResolutionResult(resolved_slots=dict(claim.slots))

    def _retrieve(
        self,
        claim: DecomposedClaim,
        resolved_slots: dict[str, Any],
        time_scope: dict[str, Any] | None = None,
    ) -> list[RerankScore]:
        graph_hits: list[GraphEvidence] = []
        lex_hits: list[LexicalEvidence] = []
        if self.graph is not None:
            try:
                graph_params = dict(resolved_slots)
                if time_scope is not None:
                    ts = time_scope.get("start")
                    te = time_scope.get("end")
                    if ts:
                        graph_params.setdefault("time_start", ts)
                    if te:
                        graph_params.setdefault("time_end", te)
                graph_hits = self.graph.retrieve(claim.claim_type, params=graph_params)
            except Exception:  # noqa: BLE001
                graph_hits = []
        if self.lexical is not None:
            try:
                lex_hits = self.lexical.search(claim.normalized_text)
            except Exception:  # noqa: BLE001
                lex_hits = []
        combined: list[Any] = [*graph_hits, *lex_hits]
        return rerank(
            combined,
            claim_type=claim.claim_type,
            claim_time_scope=time_scope,
            resolved_ids={
                k: str(v)
                for k, v in resolved_slots.items()
                if v not in (None, "")
            },
        )


_default_pipeline: VerifyPipeline = VerifyPipeline()


def get_pipeline() -> VerifyPipeline:
    return _default_pipeline


def set_pipeline(pipeline: VerifyPipeline) -> None:
    """Swap the process-wide pipeline (used by wiring + tests)."""

    global _default_pipeline
    _default_pipeline = pipeline


def reset_pipeline() -> None:
    """Restore the default offline pipeline (used after lifespan shutdown)."""

    global _default_pipeline
    _default_pipeline = VerifyPipeline()
