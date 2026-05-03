"""V2 Stage B — build :class:`~civic_ontology.models.attribution.AttributionEdge` rows from v1 verdicts and provenance."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from civic_ontology.models.attribution import AttributionEdge, ToObjectType

from . import relation_rules

_CLAIM_TYPE_TO_OBJECT_TYPE: dict[str, ToObjectType] = {
    "vote_cast": "VoteEvent",
    "bill_sponsorship": "Bill",
    "office_held": "PositionTerm",
    "committee_membership": "AtomicClaim",
    "committee_attendance": "AtomicClaim",
    "election_result": "ElectionResult",
    "statement_about_formal_action": "AtomicClaim",
}


def determine_to_object_type(claim_type: str) -> ToObjectType:
    """Resolve graph target node kind for a decomposed ``claim_type`` string."""

    return _CLAIM_TYPE_TO_OBJECT_TYPE.get(claim_type, "AtomicClaim")


def extract_to_object_id(
    claim_type: str,
    top_evidence: Sequence[Mapping[str, Any]],
    fallback_claim_id: UUID,
) -> UUID:
    """Take the first matching graph evidence ``node_ids`` id for this ``claim_type``, else fallback."""

    for ev in top_evidence:
        if ev.get("kind") != "graph":
            continue
        if ev.get("claim_type") != claim_type:
            continue
        node_ids = ev.get("node_ids")
        if not isinstance(node_ids, Mapping):
            continue
        key_chain: tuple[str, ...]
        if claim_type == "vote_cast":
            key_chain = ("vote_event_id",)
        elif claim_type == "bill_sponsorship":
            key_chain = ("bill_id",)
        elif claim_type == "office_held":
            key_chain = ("position_term_id", "office_id")
        elif claim_type == "election_result":
            key_chain = ("election_result_id",)
        else:
            continue
        for key in key_chain:
            raw = node_ids.get(key)
            if raw is None or raw == "":
                continue
            try:
                return UUID(str(raw))
            except ValueError:
                continue
    return fallback_claim_id


def extract_evidence_span_ids(top_evidence: Sequence[Mapping[str, Any]]) -> list[UUID]:
    """Collect span UUIDs from graph ``node_ids`` and lexical evidence rows, in order, deduped."""

    out: list[UUID] = []
    seen: set[UUID] = set()

    def _push(raw: object) -> None:
        try:
            u = UUID(str(raw))
        except ValueError:
            return
        if u not in seen:
            seen.add(u)
            out.append(u)

    for ev in top_evidence:
        node_ids = ev.get("node_ids")
        if isinstance(node_ids, Mapping):
            sid = node_ids.get("span_id")
            if sid is not None:
                _push(sid)
            sids = node_ids.get("span_ids")
            if isinstance(sids, (list, tuple)):
                for item in sids:
                    _push(item)
            elif sids is not None:
                _push(sids)
        if ev.get("kind") == "lexical":
            lex_sid = ev.get("span_id")
            if lex_sid is not None:
                _push(lex_sid)
    return out


def build_attribution_edge(
    *,
    declaration_id: UUID,
    claim_id: UUID,
    claim_type: str,
    verdict_status: str,
    checkability: str,
    confidence_overall: float,
    top_evidence: Sequence[Mapping[str, Any]],
    reasons: Sequence[Mapping[str, Any]],
    lexical_hits: int,
    needs_human_review: bool,
    now: datetime | None = None,
) -> AttributionEdge:
    """Assemble a validated :class:`AttributionEdge` from v1 pipeline outputs."""

    relation_type = relation_rules.determine_relation(
        verdict_status=verdict_status,
        checkability=checkability,
        reasons=reasons,
        lexical_hits=lexical_hits,
    )
    confidence_band = relation_rules.determine_confidence_band(confidence_overall)
    to_object_type = determine_to_object_type(claim_type)
    to_object_id = extract_to_object_id(claim_type, top_evidence, claim_id)
    evidence_span_ids = extract_evidence_span_ids(top_evidence)
    review_status = "needs_human_review" if needs_human_review else "pending"
    created = now if now is not None else datetime.now(tz=timezone.utc)
    return AttributionEdge(
        attribution_id=uuid.uuid4(),
        from_declaration_id=declaration_id,
        to_object_id=to_object_id,
        to_object_type=to_object_type,
        relation_type=relation_type,
        evidence_span_ids=evidence_span_ids,
        confidence_band=confidence_band,
        review_status=review_status,
        created_at=created,
    )
