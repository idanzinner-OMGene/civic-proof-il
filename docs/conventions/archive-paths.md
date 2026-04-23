# Archive URI convention

> Authoritative spec for the MinIO / S3 archive URI scheme used across
> ingestion, verification, and evidence-span retrieval. Code reference:
> [`packages/clients/src/civic_clients/archive.py`](../../packages/clients/src/civic_clients/archive.py).
> Phase-1 context: plan lines 311-320. Cross-linked from
> [`docs/DATA_MODEL.md`](../DATA_MODEL.md) (owned by Agent F).

## URI format

```
s3://<bucket>/<source_family>/<YYYY>/<MM>/<DD>/<sha256>.<ext>
```

Every field is mandatory; there are no optional path segments. A literal
dot separates the content hash from the extension.

### Field definitions

- **`bucket`** — the value of the `MINIO_BUCKET_ARCHIVE` environment
  variable (see `.env.example`). Dev default: `civic-archive`. The
  bucket segment must match the currently-configured env var at
  write time; mismatches raise `ValueError` (see
  `civic_clients.minio_client.put_archive_object`).
- **`source_family`** — one of:
  - `knesset` — Knesset records (plenum votes, committee minutes,
    sponsorship, attendance, MK roles).
  - `gov_il` — gov.il role and decision pages.
  - `elections` — official election results.

  This list mirrors the Phase-0 `services/ingestion/*` subdirectories.
  Adding a new family is a two-step change: update
  `civic_clients.archive.SOURCE_FAMILIES` and document it here.
- **`YYYY/MM/DD`** — the UTC calendar date derived from
  `captured_at`. `captured_at` MUST be a timezone-aware
  `datetime`; naive timestamps are rejected to eliminate an entire
  class of "off-by-one-day" archive-path drift. The date is always
  computed via `captured_at.astimezone(timezone.utc)`.
- **`sha256`** — hex-lowercase SHA-256 of the raw bytes exactly as
  delivered by the upstream source. Computed via
  `civic_clients.archive.content_sha256`. Do **not** canonicalise,
  reformat, or re-encode content before hashing.
- **`ext`** — lowercase file extension with **no leading dot** in the
  URI. The builder normalises input (`.PDF`, `PDF`, `.pdf` all become
  `pdf`). Only `[a-z0-9]+` characters are permitted.

### Worked example

```
captured_at  = 2024-01-15T09:00:00+00:00
source_family = "knesset"
content      = b"hello"
extension    = "html"

sha256(content) = 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
URI = s3://civic-archive/knesset/2024/01/15/2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824.html
```

## Immutability

Once written, an archive object MUST NOT be overwritten. Two rules
follow from this:

1. **Re-fetching identical content is a no-op.** If a worker re-fetches
   a page and the new SHA-256 matches the existing object's SHA-256,
   the URI is identical and the second write is either skipped entirely
   or issued idempotently. Consumers should rely on the URI as a stable
   reference.
2. **A collision is a bug.** If the URI already exists but the incoming
   content hash differs from the stored one, the system MUST raise
   rather than overwrite. This can only happen on algorithm change or
   path malformation; either way it signals a defect, not a normal
   re-ingest.

## Bucket layout invariants

- `<bucket>/<source_family>/…` — top-level prefix per family lets us
  lifecycle / replicate / backup families independently.
- `<…>/YYYY/MM/DD/…` — date prefix keeps per-day listings bounded even
  for high-volume sources.
- `<sha256>.<ext>` — hash-addressed filename guarantees uniqueness
  within a day and supports content-addressed deduplication.

## Cross-store references

- **Postgres.** `raw_fetch_objects.archive_uri TEXT NOT NULL` stores
  the full canonical URI; `raw_fetch_objects.content_sha256 TEXT NOT
  NULL` stores the hash separately so SQL filters do not need to
  parse the URI. The two fields MUST stay consistent — enforced at
  write time by `civic_clients.minio_client.put_archive_object`.
- **OpenSearch.** `source_documents.archive_uri: keyword` and
  `evidence_spans.archive_uri: keyword` store the same string.
- **Neo4j.** `SourceDocument { archive_uri }` stores the same string.
- **JSON Schemas.** `source_document.schema.json` /
  `evidence_span.schema.json` declare `archive_uri` as a `string` with
  the canonical URI pattern (`^s3://…`).

## Code surface

All read / write paths go through `civic_clients`:

- `civic_clients.archive.build_archive_uri(source_family, captured_at, content, ext)`
- `civic_clients.archive.parse_archive_uri(uri) -> ArchiveCoord`
- `civic_clients.archive.content_sha256(content) -> str`
- `civic_clients.minio_client.put_archive_object(uri, content, content_type)`

Hand-crafting URIs anywhere else is forbidden — it breaks the
immutability and bucket-match guarantees above.
