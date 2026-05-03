"""CLI entry point: ``python -m civic_ingest_elections run``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

__all__ = ["main"]

REPO_ROOT = Path(__file__).resolve().parents[5]
MANIFEST_PATH = REPO_ROOT / "services/ingestion/elections/manifest.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="civic_ingest_elections")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument(
        "--knesset",
        type=int,
        default=25,
        help="Knesset number to ingest (default: 25).",
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

    from .normalize import normalize_page
    from .parse import parse_election_page
    from .party_list_mapping import get_election_date
    from .upsert import upsert_election_result

    manifest = load_manifest(MANIFEST_PATH)
    fetcher = Fetcher()
    knesset_number = args.knesset
    election_date = get_election_date(knesset_number)

    # CEC URL for this specific Knesset election
    source_url = str(manifest.source_url).rstrip('/') + '/'

    with IngestRun(source_family=manifest.family) as run:
        fetch_result = fetcher.fetch(source_url)

        if not args.dry_run:
            archive_payload(
                fetch_result=fetch_result,
                source_family=manifest.family,
                source_url=source_url,
                ingest_run_id=run.db_id,
                source_tier=manifest.source_tier,
                conn=run.connection,
                extension_hint="html",
            )

        page = parse_election_page(
            html_bytes=fetch_result.content,
            knesset_number=knesset_number,
            election_date=election_date,
        )

        upsert_fn = (lambda _r: None) if args.dry_run else upsert_election_result

        rows_upserted = 0
        for normalized in normalize_page(page):
            upsert_fn(normalized)
            rows_upserted += 1

        run.add_stats({
            "adapter": manifest.adapter,
            "knesset_number": knesset_number,
            "pages": 1,
            "rows_parsed": len(page.rows),
            "rows_upserted": rows_upserted,
        })

    print(
        f"elections: knesset={knesset_number} "
        f"rows_parsed={len(page.rows)} "
        f"rows_upserted={rows_upserted}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
