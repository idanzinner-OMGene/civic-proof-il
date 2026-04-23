# `civic-archival`

Fetches source material, hashes content, writes it to the immutable
MinIO archive, and records per-fetch metadata in Postgres.

Non-negotiable rule: **no verification-grade verdict may exist
without an archived source object.** This service is the single write
path to that archive.

## Responsibilities

-   Polite HTTP fetching (`Fetcher`) with a project `User-Agent`,
    timeouts, and a single `Retry-After` honor on 429.
-   Content hashing (SHA-256 over the raw bytes).
-   Idempotent upload to `MINIO_BUCKET_ARCHIVE` using the URI
    convention documented in `docs/conventions/archive-paths.md`.
-   Insert of one `raw_fetch_objects` row per new content hash.
    Existing hashes short-circuit with `created=False`.
-   CLI for the VCR cassette-recording workflow documented in
    `docs/conventions/cassette-recording.md`.

## Public surface

```python
from civic_archival import Fetcher, FetchResult, archive_payload, ArchiveRecord, fetch
```

-   `Fetcher(user_agent=…, timeout=…)` — wrap an `httpx.Client`.
-   `Fetcher.fetch(url, headers=…, allow_error=False) -> FetchResult`.
-   `archive_payload(*, source_family, source_url, fetch_result,
    ingest_run_id, source_tier, extension_hint=None, conn=None) ->
    ArchiveRecord` — the only supported write path to MinIO + Postgres.
-   `fetch(url, …)` — module-level convenience wrapper around
    `Fetcher.fetch`.

## CLI

```bash
# Record one cassette
uv run python -m civic_archival fetch \
  --url 'https://knesset.gov.il/OdataV4/ParliamentInfo.svc/KNS_Person?$top=50' \
  --out tests/fixtures/phase2/cassettes/people/sample.json
```

Prints the content-hash, Content-Type, and output path.

## Gotchas

-   `FetchResult.fetched_at` is always timezone-aware (UTC). Naive
    datetimes anywhere in this service are a bug.
-   `archive_payload()` requires an open `psycopg.Connection` when you
    want the write + insert to share a transaction. When called
    without one, it opens a short-lived connection.
-   `extension_from_content_type("application/json; charset=utf-8")`
    returns `json`; unknown content types fall back to `bin`.
-   `put_archive_object` refuses cross-bucket writes — the URI's
    bucket segment must equal `MINIO_BUCKET_ARCHIVE`.
