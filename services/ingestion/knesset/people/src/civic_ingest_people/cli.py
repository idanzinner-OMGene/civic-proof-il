"""CLI entry point: ``python -m civic_ingest_people run``."""

from __future__ import annotations

import argparse
import functools
import sys
from pathlib import Path

__all__ = ["main"]

REPO_ROOT = Path(__file__).resolve().parents[6]
MANIFEST_PATH = REPO_ROOT / "services/ingestion/knesset/manifests/people.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="civic_ingest_people")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--max-pages", type=int, default=None)
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + normalize only; skip Neo4j writes and archival.",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        return _run(args)
    return 2


def _run(args) -> int:
    from civic_archival import Fetcher, archive_payload
    from civic_ingest import IngestRun, load_manifest, run_adapter

    from .normalize import normalize_person
    from .parse import parse_persons
    from .upsert import upsert_person

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
                extension_hint="json",
            )

        def _archive_one(fetch_result):
            if archive is None:
                return None
            return archive(fetch_result=fetch_result)

        upsert_fn = (lambda _n: None) if args.dry_run else upsert_person

        result = run_adapter(
            ingest_run=run,
            adapter=manifest.adapter,
            source_url=str(manifest.source_url),
            fetch=fetcher.fetch,
            archive=_archive_one,
            parse=parse_persons,
            normalize=normalize_person,
            upsert=upsert_fn,
            max_pages=args.max_pages,
        )

    print(
        f"people: pages={result.pages} rows_parsed={result.rows_parsed} "
        f"rows_upserted={result.rows_upserted}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
