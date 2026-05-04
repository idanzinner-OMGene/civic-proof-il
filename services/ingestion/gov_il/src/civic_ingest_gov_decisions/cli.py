"""CLI entry point: ``python -m civic_ingest_gov_decisions run``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

__all__ = ["main"]

REPO_ROOT = Path(__file__).resolve().parents[5]
MANIFEST_PATH = REPO_ROOT / "services/ingestion/gov_il/manifest.yaml"

_BASE_URL = "https://next.obudget.org/search/gov_decisions"
_QUERY = "החלטה+מספר"
_PAGE_SIZE = 50


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="civic_ingest_gov_decisions")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Stop after this many pages (default: all).",
    )
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + parse + normalize only; skip Neo4j writes and archival.",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        return _run(args)
    return 2


def _run(args) -> int:
    from civic_archival import Fetcher, archive_payload
    from civic_ingest import IngestRun, load_manifest

    from .normalize import normalize_rows
    from .parse import parse_response, total_overall
    from .upsert import upsert_government_decision

    manifest = load_manifest(MANIFEST_PATH)
    fetcher = Fetcher()

    upsert_fn = (lambda _d: None) if args.dry_run else upsert_government_decision

    pages_fetched = 0
    rows_parsed = 0
    rows_upserted = 0

    with IngestRun(source_family=manifest.family) as run:
        offset = 0
        while True:
            if args.max_pages is not None and pages_fetched >= args.max_pages:
                break

            url = f"{_BASE_URL}?q={_QUERY}&size={_PAGE_SIZE}&from={offset}"
            fetch_result = fetcher.fetch(url)

            if not args.dry_run:
                archive_payload(
                    fetch_result=fetch_result,
                    source_family=manifest.family,
                    source_url=url,
                    ingest_run_id=run.db_id,
                    source_tier=manifest.source_tier,
                    conn=run.connection,
                    extension_hint="json",
                )

            page_rows = parse_response(fetch_result.content)
            pages_fetched += 1
            rows_parsed += len(page_rows)

            for normalized in normalize_rows(page_rows):
                upsert_fn(normalized)
                rows_upserted += 1

            # Paginate: stop when fewer results than page size were returned
            if len(page_rows) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE

        run.add_stats({
            "adapter": manifest.adapter,
            "pages": pages_fetched,
            "rows_parsed": rows_parsed,
            "rows_upserted": rows_upserted,
        })

    print(
        f"gov_decisions: pages={pages_fetched} "
        f"rows_parsed={rows_parsed} "
        f"rows_upserted={rows_upserted}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
