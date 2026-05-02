# Cassette recording (VCR-style HTTP capture)

Phase 2 adapters talk to Knesset OData V4 (and, later, gov.il and
election sources). We do not hit upstream endpoints from unit or
integration tests — tests replay a recorded payload captured once,
committed to the repo, and refreshed on demand.

ADR-0002 records the decision; this document is the runbook.

## File layout

```text
tests/fixtures/phase2/cassettes/<adapter>/<slug>.<ext>
```

Each cassette is the raw upstream payload — the same bytes
`services/archival.archive_payload()` would have stored in MinIO.
One file per logical payload. `<ext>` matches the upstream
`Content-Type`:

| Content-Type            | Extension |
|-------------------------|-----------|
| `application/json`      | `json`    |
| `application/xml`       | `xml`     |
| `application/pdf`       | `pdf`     |
| `text/html`             | `html`    |
| `text/csv`              | `csv`     |
| anything else           | `bin`     |

Phase-2 Knesset OData payloads are always JSON.

## Recording a new cassette

All cassettes must be captured via the same `Fetcher` the production
path uses. That's the whole point of ADR-0002 — the bytes in the
cassette pass through the same user-agent, retry, and hashing logic
as the bytes in MinIO will.

Single-URL recording:

```bash
uv run python -m civic_archival fetch \
  --url 'https://knesset.gov.il/OdataV4/ParliamentInfo.svc/KNS_Person?$filter=KnessetNum eq 25&$top=50' \
  --out tests/fixtures/phase2/cassettes/people/sample.json
```

The CLI prints:
-   the SHA-256 digest of the captured bytes,
-   the detected `Content-Type`,
-   the final output path.

Review the new file, check it into git with a message of the form
`phase2: record cassette for knesset/<adapter>/<slug>`.

Batch recording lives at:

```bash
make record-cassettes
```

which delegates to `scripts/record-cassettes.sh`. The script walks
every Phase-2 adapter, calls `python -m civic_archival fetch --out
…` for each, and rewrites the corresponding `SOURCE.md` provenance
file (URL, capture date, SHA-256). For large CSV sources (the
oknesset member-vote dump in particular) the script passes
`--max-bytes` / `--max-lines` so the recorded cassette stays under
~200 KB while remaining a byte-for-byte head of a real upstream
response.

`make record-cassettes` is the only sanctioned way to refresh
cassettes — it pins URLs, truncation limits, and provenance writes
to a single source of truth, and it requires `full_network`
permission because `knesset.gov.il` and `production.oknesset.org`
are not in the default sandbox allowlist.

### `SOURCE.md` provenance (required)

Every cassette directory under `tests/fixtures/phase2/cassettes/`
and every fixture root under `tests/fixtures/phase1/` MUST contain a
`SOURCE.md` documenting:

-   The exact upstream URL captured.
-   The capture date (UTC, ISO-8601).
-   The SHA-256 of the captured bytes.
-   Any truncation applied (`--max-bytes` / `--max-lines`).
-   For derived Phase-1 fixtures: the upstream cassette they were
    derived from and the deterministic UUID5 namespace used.

`tests/smoke/test_alignment.py` enforces this — a missing
`SOURCE.md` fails the alignment audit.

## Using cassettes in tests

### Unit tests

Each adapter's unit test imports the parser + normalizer directly and
runs them against the cassette's parsed content. The cassette is
opened with `Path(__file__).parent / "../../tests/fixtures/phase2/cassettes/<adapter>/<slug>.json"`
or equivalent.

### Integration test (`tests/integration/test_phase2_ingestion.py`)

Walks all eight adapters via `civic_ingest.adapter.run_adapter()`,
swapping in a stub fetcher that returns the cassette bytes:

```python
def stub_fetcher(url: str) -> FetchResult:
    payload = _read_cassette(adapter_name, slug)
    return FetchResult(url=url, status_code=200, content=payload,
                       content_type="application/json",
                       fetched_at=datetime.now(timezone.utc))
```

The rest of the pipeline — archive_payload, parse, normalize, Neo4j
upsert — runs for real.

## Re-recording a cassette (upstream schema drift)

1. Run the single-URL recorder against the same URL that originally
   produced the cassette. Overwrite the file in place.
2. Inspect the diff. Meaningful changes in payload shape (new
   top-level keys, new enum values, renamed fields) require an
   adapter-side change:
    -   Parser update in `services/ingestion/<family>/<adapter>/src/.../parse.py`
    -   Normalizer update if the canonical model shifts
    -   New unit-test expectation
3. Run the adapter's test suite:

    ```bash
    uv run pytest services/ingestion/knesset/<adapter>/tests/
    ```

4. Run the alignment audit:

    ```bash
    uv run pytest tests/smoke/test_alignment.py
    ```

5. Commit the new cassette + any code changes together.

## Conventions

-   **Redact nothing.** OData payloads from Knesset are public. If a
    future source requires redaction, add a redaction pass to
    `civic_archival` (and document it here).
-   **Do not hand-edit cassettes.** They must be byte-for-byte what
    the upstream returned, so the archival hash matches what
    production would compute.
-   **Keep cassettes small.** Use `$top=50` (or similar pagination
    parameters) to cap page size for test cassettes. A full-page
    production fetch can be terabytes over the life of an adapter;
    we don't ship that in the repo.
-   **One cassette per upstream URL.** Don't pile multiple variants
    into one file. If an adapter tests pagination, record two
    cassettes (`page_1.json`, `page_2.json`).
-   **Slugs are hand-chosen and stable.** Renaming a cassette breaks
    any test that refers to it; treat slugs as a public API within
    the adapter's tests.

## Gotchas

-   **`$filter` parameters with Hebrew text.** URL-encode the query
    string carefully; zsh will happily mangle unencoded Hebrew. Use
    single quotes around the full URL.
-   **`Retry-After` headers.** The `Fetcher` honors one retry per
    call. If the upstream rate-limits the recorder, wait and retry
    manually; do not loop on `--retry`.
-   **Content-Type inference.** If the upstream returns
    `application/json; charset=utf-8`, the CLI splits on `;` and
    extracts `application/json`. Unusual Content-Types may need a
    manual `--extension` override (tracking as a Phase-3 CLI nicety).
-   **Cassette drift is a bug, not a lint.** If the integration test
    fails after a re-record, the adapter code — not the cassette — is
    the thing to fix.
-   **The alignment audit checks cassette presence, not content.**
    Static checks ensure a file exists per adapter; content
    regressions surface only at test time.
