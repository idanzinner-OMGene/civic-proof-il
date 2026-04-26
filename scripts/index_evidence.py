#!/usr/bin/env python3
"""Index ``evidence_spans`` in OpenSearch from Neo4j :SourceDocument rows.

Creates one synthetic span per document using ``title`` as BM25 text (falls
back to a single dot when missing). Requires a live Neo4j + OpenSearch; exits
0 with a warning when either ping fails (CI / laptop without compose).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
SPAN_NS = uuid5(NAMESPACE_URL, "civic-proof-il/evidence_spans/v1")


def _span_id(document_id: str) -> str:
    return str(uuid5(SPAN_NS, document_id))


def _neo4j_documents(limit: int) -> list[dict[str, Any]]:
    from civic_clients import neo4j

    if not neo4j.ping():
        return []
    q = """
    MATCH (d:SourceDocument)
    RETURN d.document_id AS document_id,
           d.title AS title,
           d.archive_uri AS archive_uri,
           d.url AS url,
           d.source_tier AS source_tier,
           d.source_type AS source_type,
           d.captured_at AS captured_at
    LIMIT $lim
    """
    driver = neo4j.make_driver()
    rows: list[dict[str, Any]] = []
    with driver.session() as session:
        for rec in session.run(q, lim=limit):
            rows.append(rec.data())
    return rows


def _serialize_dt(val: Any) -> str | None:
    if val is None:
        return None
    if hasattr(val, "iso_format"):
        return val.iso_format()  # neo4j.time.DateTime
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=UTC)
        return val.isoformat()
    return str(val)


def _build_doc(row: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(row.get("document_id") or "")
    title = (row.get("title") or "").strip() or "."
    tier = int(row.get("source_tier") or 2)
    stype = str(row.get("source_type") or "unknown")
    url = str(row.get("url") or "")
    archive_uri = str(row.get("archive_uri") or "")
    cap = _serialize_dt(row.get("captured_at"))
    span_id = _span_id(doc_id)
    n = len(title)
    body: dict[str, Any] = {
        "span_id": span_id,
        "document_id": doc_id,
        "source_tier": tier,
        "source_type": stype,
        "url": url,
        "archive_uri": archive_uri,
        "text": title,
        "normalized_text": title.lower(),
        "char_start": 0,
        "char_end": max(0, n),
    }
    if cap:
        body["captured_at"] = cap
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Index evidence_spans from Neo4j SourceDocument")
    parser.add_argument("--limit", type=int, default=500, help="Max SourceDocument nodes to index")
    parser.add_argument(
        "--index",
        default="evidence_spans",
        help="OpenSearch index name (must match LexicalRetriever index)",
    )
    args = parser.parse_args()

    from civic_clients import opensearch

    if not opensearch.ping():
        print("opensearch unreachable; skipping index", file=sys.stderr)
        return 0

    rows = _neo4j_documents(args.limit)
    if not rows:
        print("no SourceDocument rows (or neo4j unreachable); nothing indexed", file=sys.stderr)
        return 0

    client = opensearch.make_client()
    indexed = 0
    errors: list[str] = []
    for row in rows:
        doc = _build_doc(row)
        sid = doc["span_id"]
        try:
            client.index(index=args.index, id=sid, body=doc, refresh=False)
            indexed += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"{sid}: {e}")
    client.indices.refresh(index=args.index)

    report = {
        "indexed_at": datetime.now(tz=UTC).isoformat(),
        "index": args.index,
        "indexed": indexed,
        "errors": errors[:20],
    }
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index_evidence.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
