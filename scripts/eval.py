#!/usr/bin/env python3
"""Offline eval harness (Phase 6) — run VerifyPipeline on the benchmark set."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))


@dataclass
class RowMetrics:
    claim_typing_precision: float | None = None
    claim_typing_recall: float | None = None
    verdict_match: bool | None = None
    n_claims: int = 0
    errors: list[str] = field(default_factory=list)


def _load_statement(spec: dict[str, Any]) -> tuple[str, str]:
    lang = str(spec.get("language", "he"))
    if spec.get("statement_path"):
        p = ROOT / str(spec["statement_path"])
        stmt = p.read_text(encoding="utf-8").strip()
        return stmt, lang if lang in ("he", "en") else "he"
    stmt = str(spec.get("statement", ""))
    return stmt, lang if lang in ("he", "en") else "he"


def _score_row(
    spec: dict[str, Any],
    bundles: list[dict[str, Any]],
    *,
    live: bool = False,
) -> RowMetrics:
    m = RowMetrics(n_claims=len(bundles))
    exp = spec.get("expected") or {}
    want_types = exp.get("expected_claim_types")
    want_verdict = exp.get("expected_verdict_live") if live else None
    if want_verdict is None:
        want_verdict = exp.get("expected_verdict")

    got_types = {b.get("claim", {}).get("claim_type") for b in bundles if isinstance(b, dict)}
    got_types.discard(None)

    if isinstance(want_types, list) and want_types:
        want_set = set(want_types)
        inter = got_types & want_set
        m.claim_typing_precision = len(inter) / len(got_types) if got_types else 0.0
        m.claim_typing_recall = len(inter) / len(want_set) if want_set else None

    if want_verdict is not None and bundles:
        statuses = [b.get("verdict", {}).get("status") for b in bundles]
        m.verdict_match = bool(statuses) and all(s == want_verdict for s in statuses)

    return m


def _aggregate(rows_out: list[dict[str, Any]]) -> dict[str, Any]:
    precisions = [r["metrics"]["claim_typing_precision"] for r in rows_out if r["metrics"]["claim_typing_precision"] is not None]
    recalls = [r["metrics"]["claim_typing_recall"] for r in rows_out if r["metrics"]["claim_typing_recall"] is not None]
    vmatches = [r["metrics"]["verdict_match"] for r in rows_out if r["metrics"]["verdict_match"] is not None]

    def _avg(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    f1_parts: list[float] = []
    for r in rows_out:
        p, rec = r["metrics"]["claim_typing_precision"], r["metrics"]["claim_typing_recall"]
        if p is not None and rec is not None and (p + rec) > 0:
            f1_parts.append(2 * p * rec / (p + rec))
    f1_claim = _avg(f1_parts) if f1_parts else 0.0
    f1_verdict = sum(1 for v in vmatches if v) / len(vmatches) if vmatches else 0.0

    return {
        "rows": len(rows_out),
        "mean_claim_typing_precision": _avg(precisions) if precisions else 0.0,
        "mean_claim_typing_recall": _avg(recalls) if recalls else 0.0,
        "f1_claim_typing": f1_claim,
        "f1_verdict": f1_verdict,
    }


def _build_live_pipeline():  # type: ignore[return]
    """Build a VerifyPipeline wired to live backing services, or return None."""
    try:
        sys.path.insert(0, str(ROOT / "packages" / "civic_clients" / "src"))
        from api.routers.pipeline import LiveEntityResolver, VerifyPipeline
        from civic_clients import neo4j as neo4j_client
        from civic_clients import opensearch as opensearch_client
        from civic_clients import postgres as postgres_client
        from civic_retrieval import GraphRetriever, LexicalRetriever

        if not (neo4j_client.ping() and opensearch_client.ping() and postgres_client.ping()):
            return None
        driver = neo4j_client.make_driver()
        conn = postgres_client.make_connection()
        conn.autocommit = True
        return VerifyPipeline(
            graph=GraphRetriever(driver),
            lexical=LexicalRetriever(opensearch_client.make_client()),
            resolver=LiveEntityResolver(neo4j_driver=driver, pg_conn=conn),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"failed to build live pipeline: {exc}", file=sys.stderr)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase-6 benchmark against VerifyPipeline")
    parser.add_argument(
        "--gold",
        type=Path,
        default=ROOT / "tests" / "benchmark" / "gold_set.yaml",
        help="Benchmark manifest (YAML)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "tests" / "benchmark" / "config.yaml",
        help="Threshold gates (YAML)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports" / "eval" / "last_run.json",
        help="Write JSON report here",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Wire live Neo4j / OpenSearch retrievers + entity resolver (requires running stack)",
    )
    args = parser.parse_args()
    if not args.gold.is_file():
        print(f"gold set not found: {args.gold}", file=sys.stderr)
        return 2

    data = yaml.safe_load(args.gold.read_text(encoding="utf-8")) or {}
    rows = data.get("rows", [])
    from api.routers.pipeline import LiveEntityResolver, VerifyPipeline  # noqa: F401

    if args.live:
        pl = _build_live_pipeline()
        if pl is None:
            print("--live requested but one or more backing stores unreachable; aborting", file=sys.stderr)
            return 2
    else:
        pl = VerifyPipeline()
    out_rows: list[dict] = []
    for spec in rows:
        try:
            stmt, lang = _load_statement(spec)
            bundles = pl.verify(stmt, language=lang)
            m = _score_row(spec, bundles, live=args.live)
        except Exception as e:  # noqa: BLE001
            m = RowMetrics(errors=[str(e)])
            bundles = []
        out_rows.append(
            {
                "id": spec.get("id"),
                "metrics": asdict(m),
                "verdicts": [b.get("verdict", {}) for b in bundles],
            }
        )

    summary = _aggregate(out_rows)
    summary["ok"] = True
    summary["live"] = args.live

    gates: dict[str, Any] = {}
    if not args.live and args.config.is_file():
        cfg = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
        min_rows = int(cfg.get("min_rows", 0))
        if len(out_rows) < min_rows:
            summary["ok"] = False
            gates["min_rows"] = {"want": min_rows, "got": len(out_rows)}
        fv = float(cfg.get("f1_verdict", 0.0))
        if summary["f1_verdict"] + 1e-9 < fv:
            summary["ok"] = False
            gates["f1_verdict"] = {"want": fv, "got": summary["f1_verdict"]}
        fc = float(cfg.get("f1_claim_typing", 0.0))
        if summary["f1_claim_typing"] + 1e-9 < fc:
            summary["ok"] = False
            gates["f1_claim_typing"] = {"want": fc, "got": summary["f1_claim_typing"]}

    report = {"rows": out_rows, "summary": summary, "gates_failed": gates}
    out_file = args.out if not args.live else args.out.with_stem("last_run_live")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
