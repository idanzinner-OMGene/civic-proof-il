"""CLI: ``python -m civic_ingest_votes run``."""

from __future__ import annotations

import argparse
import functools
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
MANIFEST_PATH = REPO_ROOT / "services/ingestion/knesset/manifests/votes.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="civic_ingest_votes")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--max-pages", type=int, default=None)
    run.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.command != "run":
        return 2

    from civic_archival import Fetcher, archive_payload
    from civic_ingest import IngestRun, load_manifest, parse_csv_page, run_adapter

    from .normalize import normalize_vote
    from .parse import parse_votes
    from .upsert import upsert_vote

    manifest = load_manifest(MANIFEST_PATH)
    fetcher = Fetcher()

    with IngestRun(source_family=manifest.family) as run:
        archive = None
        if not args.dry_run:
            archive = functools.partial(
                archive_payload,
                source_family=manifest.family,
                source_url=str(manifest.source_url),
                ingest_run_id=run.db_id,
                source_tier=manifest.source_tier,
                conn=run.connection,
                extension_hint="csv",
            )

        def _archive(fr):
            return None if archive is None else archive(fetch_result=fr)

        upsert_fn = (lambda _n: None) if args.dry_run else upsert_vote
        result = run_adapter(
            ingest_run=run,
            source_url=str(manifest.source_url),
            fetch=fetcher.fetch,
            archive=_archive,
            parse=parse_votes,
            normalize=normalize_vote,
            upsert=upsert_fn,
            max_pages=args.max_pages,
            page_parser=parse_csv_page,
        )

    print(
        f"votes: pages={result.pages} rows={result.rows_parsed} "
        f"upserted={result.rows_upserted}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
