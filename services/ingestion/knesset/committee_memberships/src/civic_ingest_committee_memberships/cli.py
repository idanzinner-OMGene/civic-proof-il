"""CLI: ``python -m civic_ingest_committee_memberships run``.

In production both the committee-membership CSV *and* the
``mk_individual.csv`` lookup need to be fetched live; the lookup URL
is fixed (it's a shared dimension table), so we fetch it once up-front
via the archival :class:`Fetcher` and build the in-memory
:class:`civic_ingest.MkIndividualLookup` before running the main
pipeline.
"""

from __future__ import annotations

import argparse
import functools
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
MANIFEST_PATH = (
    REPO_ROOT
    / "services/ingestion/knesset/manifests/committee_memberships.yaml"
)

MK_INDIVIDUAL_URL = (
    "https://production.oknesset.org/pipelines/data/members/"
    "mk_individual/mk_individual.csv"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="civic_ingest_committee_memberships"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--max-pages", type=int, default=None)
    run.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.command != "run":
        return 2

    from civic_archival import Fetcher, archive_payload
    from civic_ingest import (
        IngestRun,
        load_manifest,
        load_mk_individual_lookup,
        parse_csv_page,
        run_adapter,
    )

    from .normalize import normalize_committee_membership
    from .parse import parse_committee_memberships
    from .upsert import upsert_committee_membership

    manifest = load_manifest(MANIFEST_PATH)
    fetcher = Fetcher()

    lookup_payload = fetcher.fetch(MK_INDIVIDUAL_URL).content
    lookup = load_mk_individual_lookup(lookup_payload)

    def _normalize(row):
        return normalize_committee_membership(row, lookup=lookup)

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

        upsert_fn = (
            (lambda _n: None) if args.dry_run else upsert_committee_membership
        )
        result = run_adapter(
            ingest_run=run,
            adapter=manifest.adapter,
            source_url=str(manifest.source_url),
            fetch=fetcher.fetch,
            archive=_archive,
            parse=parse_committee_memberships,
            normalize=_normalize,
            upsert=upsert_fn,
            max_pages=args.max_pages,
            page_parser=parse_csv_page,
        )

    print(
        f"committee_memberships: pages={result.pages} "
        f"rows={result.rows_parsed} upserted={result.rows_upserted}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
