"""Wipe a local Neo4j and load the Phase-1 fixture set.

Use case: you have a Neo4j Desktop / Homebrew instance on
``bolt://localhost:7687`` with unrelated data (or empty) and you want a
clean, browsable Phase-1 reference dataset to explore in Neo4j Browser.

This script:
1. Reads credentials from ``.cursor/.env`` (``G_DB_CONNECTION_STRING``,
   ``G_DB_USER``, ``G_DB_PASSWORD``, optional ``G_DB_NAME``). It does NOT
   touch ``civic_common.Settings`` or the repo-root ``.env`` so it is
   safe to run standalone, without the rest of the stack configured.
2. Drops every node + relationship (``DETACH DELETE`` in batched
   transactions).
3. Drops every constraint and every non-LOOKUP index.
4. Re-applies ``infra/neo4j/constraints.cypher`` (12 unique constraints).
5. Loads the 12 Phase-1 fixture nodes via the upsert templates under
   ``infra/neo4j/upserts/`` (Person, Party, Office, Committee, Bill,
   VoteEvent, AttendanceEvent, MembershipTerm, SourceDocument,
   EvidenceSpan, AtomicClaim, Verdict).
6. Loads the 11 Phase-1 relationships via the upsert templates under
   ``infra/neo4j/upserts/relationships/``: about_bill, about_person,
   cast_vote, contradicted_by, evaluates, has_span, held_office,
   member_of, member_of_committee, sponsored, supported_by.
7. Verifies and prints the label / relationship-type counts. No
   teardown — the dataset is left in place for manual inspection in
   Neo4j Browser (http://localhost:7474).

Counterpart to ``tests/integration/test_phase1_persistence.py`` (which
writes the same fixtures against compose Neo4j, verifies round-trip,
and scrubs on teardown). This script is deliberately persistent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from neo4j import GraphDatabase
except ImportError:
    print(
        "ERROR: the `neo4j` python driver is not installed.\n"
        "       Run: uv sync  (or: pip install neo4j)",
        file=sys.stderr,
    )
    raise


ROOT = Path(__file__).resolve().parents[1]
CURSOR_ENV = ROOT / ".cursor" / ".env"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "phase1"
CONSTRAINTS_FILE = ROOT / "infra" / "neo4j" / "constraints.cypher"
UPSERT_DIR = ROOT / "infra" / "neo4j" / "upserts"
REL_DIR = UPSERT_DIR / "relationships"


def load_dotenv(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file without depending on python-dotenv.

    Tolerates comments, blank lines, trailing whitespace, and values that
    contain shell-special characters like ``!``. Does NOT do shell
    interpolation (e.g. ``$VAR``).
    """

    values: dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"expected env file not found: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip matching surrounding quotes but keep inner content verbatim.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _person_params(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "person_id": p["person_id"],
        "canonical_name": p.get("canonical_name"),
        "hebrew_name": p.get("hebrew_name"),
        "english_name": p.get("english_name"),
        "external_ids": (
            json.dumps(p["external_ids"]) if p.get("external_ids") else None
        ),
        "source_tier": p.get("source_tier"),
    }


def _party_params(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "party_id": p["party_id"],
        "canonical_name": p.get("canonical_name"),
        "hebrew_name": p.get("hebrew_name"),
        "english_name": p.get("english_name"),
        "abbreviation": p.get("abbreviation"),
    }


def _office_params(o: dict[str, Any]) -> dict[str, Any]:
    return {
        "office_id": o["office_id"],
        "canonical_name": o.get("canonical_name"),
        "office_type": o.get("office_type"),
        "scope": o.get("scope"),
    }


def _committee_params(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "committee_id": c["committee_id"],
        "canonical_name": c.get("canonical_name"),
        "hebrew_name": c.get("hebrew_name"),
    }


def _bill_params(b: dict[str, Any]) -> dict[str, Any]:
    return {
        "bill_id": b["bill_id"],
        "title": b.get("title"),
        "knesset_number": b.get("knesset_number"),
        "status": b.get("status"),
    }


def _vote_event_params(v: dict[str, Any]) -> dict[str, Any]:
    return {
        "vote_event_id": v["vote_event_id"],
        "bill_id": v.get("bill_id"),
        "occurred_at": v.get("occurred_at"),
        "vote_type": v.get("vote_type"),
    }


def _attendance_event_params(a: dict[str, Any]) -> dict[str, Any]:
    return {
        "attendance_event_id": a["attendance_event_id"],
        "committee_id": a.get("committee_id"),
        "occurred_at": a.get("occurred_at"),
    }


def _membership_term_params(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "membership_term_id": m["membership_term_id"],
        "person_id": m.get("person_id"),
        "org_id": m.get("org_id"),
        "org_type": m.get("org_type"),
        "valid_from": m.get("valid_from"),
        "valid_to": m.get("valid_to"),
    }


def _source_document_params(s: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": s["document_id"],
        "source_family": s.get("source_family"),
        "source_tier": s.get("source_tier"),
        "source_type": s.get("source_type"),
        "url": s.get("url"),
        "archive_uri": s.get("archive_uri"),
        "content_sha256": s.get("content_sha256"),
        "captured_at": s.get("captured_at"),
        "language": s.get("language"),
        "title": s.get("title"),
    }


def _evidence_span_params(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "span_id": e["span_id"],
        "document_id": e.get("document_id"),
        "source_tier": e.get("source_tier"),
        "source_type": e.get("source_type"),
        "url": e.get("url"),
        "archive_uri": e.get("archive_uri"),
        "text": e.get("text"),
        "char_start": e.get("char_start"),
        "char_end": e.get("char_end"),
        "captured_at": e.get("captured_at"),
    }


def _atomic_claim_params(c: dict[str, Any]) -> dict[str, Any]:
    ts = c.get("time_scope") or {}
    return {
        "claim_id": c["claim_id"],
        "raw_text": c.get("raw_text"),
        "normalized_text": c.get("normalized_text"),
        "claim_type": c.get("claim_type"),
        "speaker_person_id": c.get("speaker_person_id"),
        "target_person_id": c.get("target_person_id"),
        "bill_id": c.get("bill_id"),
        "committee_id": c.get("committee_id"),
        "office_id": c.get("office_id"),
        "vote_value": c.get("vote_value"),
        "time_scope_start": ts.get("start"),
        "time_scope_end": ts.get("end"),
        "time_scope_granularity": ts.get("granularity"),
        "checkability": c.get("checkability"),
        "created_at": c.get("created_at"),
    }


def _verdict_params(v: dict[str, Any]) -> dict[str, Any]:
    conf = v.get("confidence") or {}
    return {
        "verdict_id": v["verdict_id"],
        "claim_id": v.get("claim_id"),
        "status": v.get("status"),
        "confidence_overall": conf.get("overall"),
        "confidence_source_authority": conf.get("source_authority"),
        "confidence_directness": conf.get("directness"),
        "confidence_temporal_alignment": conf.get("temporal_alignment"),
        "confidence_entity_resolution": conf.get("entity_resolution"),
        "confidence_cross_source_consistency": conf.get("cross_source_consistency"),
        "summary": v.get("summary"),
        "needs_human_review": v.get("needs_human_review"),
        "model_version": v.get("model_version"),
        "ruleset_version": v.get("ruleset_version"),
        "created_at": v.get("created_at"),
    }


NODE_LOADERS: list[tuple[str, str, Any]] = [
    ("person", "person_upsert.cypher", _person_params),
    ("party", "party_upsert.cypher", _party_params),
    ("office", "office_upsert.cypher", _office_params),
    ("committee", "committee_upsert.cypher", _committee_params),
    ("bill", "bill_upsert.cypher", _bill_params),
    ("vote_event", "vote_event_upsert.cypher", _vote_event_params),
    ("attendance_event", "attendance_event_upsert.cypher", _attendance_event_params),
    ("membership_term", "membership_term_upsert.cypher", _membership_term_params),
    ("source_document", "source_document_upsert.cypher", _source_document_params),
    ("evidence_span", "evidence_span_upsert.cypher", _evidence_span_params),
    ("atomic_claim", "atomic_claim_upsert.cypher", _atomic_claim_params),
    ("verdict", "verdict_upsert.cypher", _verdict_params),
]


def run_file(session, path: Path, params: dict[str, Any]) -> None:
    cypher = path.read_text(encoding="utf-8")
    session.run(cypher, **params).consume()


def split_statements(text: str) -> list[str]:
    """Split Cypher text on bare ``;`` terminators, ignoring comments.

    Good enough for ``constraints.cypher`` (every statement ends with
    ``;`` on its own and there are no string literals with embedded
    semicolons).
    """

    stmts: list[str] = []
    buf: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("//") or not stripped:
            buf.append(raw)
            continue
        buf.append(raw)
        if stripped.endswith(";"):
            joined = "\n".join(buf).strip()
            joined = joined.rstrip(";").strip()
            if joined:
                stmts.append(joined)
            buf = []
    tail = "\n".join(buf).strip().rstrip(";").strip()
    if tail:
        stmts.append(tail)
    return stmts


def wipe(session) -> None:
    print("[wipe] counting existing graph...")
    before_nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    before_rels = session.run(
        "MATCH ()-[r]->() RETURN count(r) AS c"
    ).single()["c"]
    print(f"[wipe] before: {before_nodes} nodes, {before_rels} relationships")

    print("[wipe] deleting all nodes + relationships (batched)...")
    session.run(
        """
        CALL {
          MATCH (n)
          DETACH DELETE n
        } IN TRANSACTIONS OF 10000 ROWS
        """
    ).consume()

    after_nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    after_rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
    if after_nodes != 0 or after_rels != 0:
        raise RuntimeError(
            f"wipe failed: {after_nodes} nodes and {after_rels} rels remain"
        )
    print(f"[wipe] after:  {after_nodes} nodes, {after_rels} relationships")

    print("[wipe] dropping existing constraints...")
    names = [row["name"] for row in session.run("SHOW CONSTRAINTS YIELD name")]
    for name in names:
        session.run(f"DROP CONSTRAINT `{name}` IF EXISTS").consume()
    print(f"[wipe] dropped {len(names)} constraints")

    print("[wipe] dropping non-LOOKUP indexes...")
    index_rows = list(
        session.run("SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP'")
    )
    for row in index_rows:
        session.run(f"DROP INDEX `{row['name']}` IF EXISTS").consume()
    print(f"[wipe] dropped {len(index_rows)} non-LOOKUP indexes")

    remaining_c = session.run("SHOW CONSTRAINTS YIELD name").data()
    remaining_i = session.run(
        "SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP'"
    ).data()
    if remaining_c:
        raise RuntimeError(f"constraints still present after wipe: {remaining_c}")
    if remaining_i:
        raise RuntimeError(f"indexes still present after wipe: {remaining_i}")


def apply_constraints(session) -> int:
    print("[schema] applying infra/neo4j/constraints.cypher...")
    text = CONSTRAINTS_FILE.read_text(encoding="utf-8")
    stmts = split_statements(text)
    for stmt in stmts:
        session.run(stmt).consume()
    applied = session.run("SHOW CONSTRAINTS YIELD name RETURN count(*) AS c").single()["c"]
    print(f"[schema] {applied} constraints active (expected 12)")
    if applied != 12:
        raise RuntimeError(f"expected 12 constraints, got {applied}")
    return applied


def load_nodes(session, fixtures: dict[str, dict[str, Any]]) -> None:
    print("[nodes] loading 12 fixture nodes...")
    for key, template_name, builder in NODE_LOADERS:
        params = builder(fixtures[key])
        run_file(session, UPSERT_DIR / template_name, params)
        print(f"[nodes]   upserted {key}")


def load_relationships(session, f: dict[str, dict[str, Any]]) -> None:
    """Load all 11 Phase-1 relationship templates with deterministic params."""

    print("[rels] loading 11 relationships...")

    rels: list[tuple[str, str, dict[str, Any]]] = [
        (
            "held_office",
            "held_office.cypher",
            {
                "person_id": f["person"]["person_id"],
                "office_id": f["office"]["office_id"],
                "valid_from": f["membership_term"]["valid_from"],
                "valid_to": f["membership_term"]["valid_to"],
            },
        ),
        (
            "member_of",
            "member_of.cypher",
            {
                "person_id": f["person"]["person_id"],
                "party_id": f["party"]["party_id"],
                "valid_from": f["membership_term"]["valid_from"],
                "valid_to": f["membership_term"]["valid_to"],
            },
        ),
        (
            "member_of_committee",
            "member_of_committee.cypher",
            {
                "person_id": f["person"]["person_id"],
                "committee_id": f["committee"]["committee_id"],
                "valid_from": f["membership_term"]["valid_from"],
                "valid_to": f["membership_term"]["valid_to"],
            },
        ),
        (
            "sponsored",
            "sponsored.cypher",
            {
                "person_id": f["person"]["person_id"],
                "bill_id": f["bill"]["bill_id"],
            },
        ),
        (
            "cast_vote",
            "cast_vote.cypher",
            {
                "person_id": f["person"]["person_id"],
                "vote_event_id": f["vote_event"]["vote_event_id"],
                "value": "for",
            },
        ),
        (
            "has_span",
            "has_span.cypher",
            {
                "document_id": f["source_document"]["document_id"],
                "span_id": f["evidence_span"]["span_id"],
            },
        ),
        (
            "about_person",
            "about_person.cypher",
            {
                "claim_id": f["atomic_claim"]["claim_id"],
                "person_id": f["person"]["person_id"],
            },
        ),
        (
            "about_bill",
            "about_bill.cypher",
            {
                "claim_id": f["atomic_claim"]["claim_id"],
                "bill_id": f["bill"]["bill_id"],
            },
        ),
        (
            "supported_by",
            "supported_by.cypher",
            {
                "claim_id": f["atomic_claim"]["claim_id"],
                "span_id": f["evidence_span"]["span_id"],
            },
        ),
        (
            "contradicted_by",
            "contradicted_by.cypher",
            {
                "claim_id": f["atomic_claim"]["claim_id"],
                "span_id": f["evidence_span"]["span_id"],
            },
        ),
        (
            "evaluates",
            "evaluates.cypher",
            {
                "verdict_id": f["verdict"]["verdict_id"],
                "claim_id": f["atomic_claim"]["claim_id"],
            },
        ),
    ]

    for name, template, params in rels:
        run_file(session, REL_DIR / template, params)
        print(f"[rels]    merged {name}")


def verify(session) -> None:
    print("\n=== Verification ===")
    print("Label counts:")
    label_rows = list(
        session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS c ORDER BY label"
        )
    )
    for row in label_rows:
        print(f"  {row['label']:<18} {row['c']}")
    total_nodes = sum(r["c"] for r in label_rows)

    print("\nRelationship counts:")
    rel_rows = list(
        session.run(
            "MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c ORDER BY t"
        )
    )
    for row in rel_rows:
        print(f"  {row['t']:<22} {row['c']}")
    total_rels = sum(r["c"] for r in rel_rows)

    print(
        f"\n  total nodes: {total_nodes} (expected 12)"
        f" / labels: {len(label_rows)} (expected 12)"
    )
    print(
        f"  total rels:  {total_rels} (expected 11)"
        f" / types:  {len(rel_rows)} (expected 11)"
    )

    expected_labels = {
        "Person",
        "Party",
        "Office",
        "Committee",
        "Bill",
        "VoteEvent",
        "AttendanceEvent",
        "MembershipTerm",
        "SourceDocument",
        "EvidenceSpan",
        "AtomicClaim",
        "Verdict",
    }
    expected_rels = {
        "ABOUT_BILL",
        "ABOUT_PERSON",
        "CAST_VOTE",
        "CONTRADICTED_BY",
        "EVALUATES",
        "HAS_SPAN",
        "HELD_OFFICE",
        "MEMBER_OF",
        "MEMBER_OF_COMMITTEE",
        "SPONSORED",
        "SUPPORTED_BY",
    }
    got_labels = {r["label"] for r in label_rows}
    got_rels = {r["t"] for r in rel_rows}
    missing_labels = expected_labels - got_labels
    missing_rels = expected_rels - got_rels
    if missing_labels:
        raise RuntimeError(f"missing node labels: {missing_labels}")
    if missing_rels:
        raise RuntimeError(f"missing relationship types: {missing_rels}")


def main() -> int:
    env = load_dotenv(CURSOR_ENV)
    uri = env.get("G_DB_CONNECTION_STRING")
    user = env.get("G_DB_USER")
    password = env.get("G_DB_PASSWORD")
    db_name = env.get("G_DB_NAME") or "neo4j"
    if not (uri and user and password):
        print(
            "ERROR: .cursor/.env must define G_DB_CONNECTION_STRING, G_DB_USER, "
            "and G_DB_PASSWORD.",
            file=sys.stderr,
        )
        return 2

    print(f"[connect] uri={uri} user={user} database={db_name}")

    fixtures: dict[str, dict[str, Any]] = {key: load_fixture(key) for key, _, _ in NODE_LOADERS}

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        with driver.session(database=db_name) as session:
            wipe(session)
            apply_constraints(session)
            load_nodes(session, fixtures)
            load_relationships(session, fixtures)
            verify(session)
    finally:
        driver.close()

    print(f"\nPhase-1 dataset loaded into {uri} (database={db_name}).")
    print("Inspect via Neo4j Browser at http://localhost:7474 with the same creds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
