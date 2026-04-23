# ADR-0002: HTTP capture via VCR record-once / replay-in-tests

*   **Status:** Accepted
*   **Date:** 2026-04-23
*   **Deciders:** civic-proof-il core team (Phase 2 Wave-A bootstrap)

## Context and Problem Statement

Phase 2 lands the first five ingestion adapters against Knesset OData
V4 (`https://knesset.gov.il/OdataV4/ParliamentInfo.svc/`). Adapters
must be testable (unit + integration) without pummelling the upstream
endpoint, without leaking credentials, and without silently skipping
tests when the machine is offline. The plan (`docs/political_verifier_v_1_plan.md`,
lines 140-180 on archival + provenance) also requires that every
fetched byte be archived before normalization runs — meaning the
test suite should exercise the same archival path as production, not
a mocked shortcut.

We need a capture strategy that:

1. Lets unit tests run offline, deterministically, in CI.
2. Lets integration tests exercise the full archival + normalization
   chain without hitting live HTTP on every commit.
3. Keeps one authoritative copy of each recorded payload, checked into
   the repo, auditable.
4. Makes "re-record" a one-command operation when upstream schemas
   drift.
5. Survives a review that asks "how does this test know what the real
   payload looks like?"

## Considered Options

1. **VCR-style record-once, replay-in-tests** (chosen). One tool
   (`python -m civic_archival fetch`) issues a real HTTP request, writes
   the response to `tests/fixtures/phase2/cassettes/<adapter>/<slug>.json`,
   and commits it. All subsequent unit/integration runs replay that file.
2. **Full live HTTP in tests**, gated by a `-m live_http` marker.
   Cheap to implement but flaky, slow, and polite-rate-limited in CI.
3. **Pure mock objects** (`unittest.mock.Mock`), hand-written.
   Fastest tests, but loses fidelity — mocks drift from the real
   payload shape, and a test green with mocks can still break on
   production.
4. **Snapshot testing with `pytest-recording` / `vcrpy`.** Library
   support is good, but tightly couples test collection to the
   `vcrpy` cassette format and makes re-recording a per-test
   invocation, not an ad-hoc CLI. Also duplicates what
   `services/archival` already does (hash + store bytes).
5. **Fixture JSON hand-written by developers.** Zero upstream
   dependency, but completely unanchored from reality — identical to
   Option 3 in the "drift" failure mode.

## Decision Outcome

Chosen option: **Option 1 — VCR-style record-once, replay-in-tests.**

Concretely:

1. **`python -m civic_archival fetch <url>` is the record command.**
   It uses the same `Fetcher` every adapter uses in production, writes
   the raw bytes to `tests/fixtures/phase2/cassettes/<family>/<slug>.<ext>`,
   and prints the content-hash for sanity. A future
   `make record-cassettes` target will batch the full adapter set.
2. **Cassette files are checked into the repo** under
   `tests/fixtures/phase2/cassettes/`. One file per logical upstream
   payload. Filename encodes the adapter + a stable slug; extension
   matches the upstream `Content-Type`.
3. **Adapters accept a pluggable `fetch` callable** through
   `civic_ingest.adapter.run_adapter(fetch=…)`. In production it's
   `services/archival.Fetcher.fetch`; in tests it's a 3-line stub
   that reads a cassette file and returns a `FetchResult`. Both paths
   hit the same `archive_payload()` → MinIO → `raw_fetch_objects`
   write flow.
4. **Integration test re-uses the unit cassettes.** `tests/integration/test_phase2_ingestion.py`
   walks the five adapters with a stub fetcher so the whole pipeline
   is reproducible offline; re-recording the cassettes is a
   deliberate, version-controlled event.
5. **Live HTTP is opt-in, behind `@pytest.mark.live_http`.** The
   marker is registered in the root `pyproject.toml`; no test
   currently uses it (cassettes are always replayed), but the
   infrastructure is ready for the first scheduled ingest run.

Rationale: Options 2, 3, and 5 all fail the "how does this test know
what the real payload looks like?" check. Option 4 works but
duplicates our own archival layer and forces every test to cross a
VCR decorator. Option 1 keeps tests offline and deterministic while
the production fetch path is the ONLY way a cassette can be
(re-)recorded — which means recorded fixtures always go through the
same Content-Type / hashing / archiving logic as production writes.

## Consequences

**Positive**

-   Unit and integration tests run offline, deterministically, at
    sub-second latency per adapter.
-   Re-recording is a single CLI invocation; cassette drift from real
    upstream is caught on the next re-record.
-   The same code path handles production fetches and test-time
    cassette capture — no fidelity gap between "what the test sees"
    and "what production sees".
-   Cassettes are auditable artifacts: reviewers can inspect the raw
    JSON in PRs, diff against prior recordings, and flag schema
    drift.

**Negative**

-   Cassettes can silently go stale. Mitigation: `make record-cassettes`
    + a scheduled re-record during the Phase-2 live validation; the
    integration test surfaces drift when the re-recorded payload no
    longer matches the normalizer's shape expectations.
-   Large HTML/PDF payloads will bloat the repo. Mitigation: for
    Phase-2 we only record small OData JSON pages; HTML/PDF archives
    live in MinIO, never in cassettes.
-   The cassette-recording workflow is developer-initiated, not
    automated. We accept this for Phase 2; Phase 3 may introduce a
    scheduled CI job.

## Scope boundaries (what we are NOT deciding here)

-   **Production fetch scheduling.** The adapter cadences are encoded
    in manifests (`cadence_cron`) but the scheduler is not in Phase 2.
-   **Cassette format.** We use raw upstream payloads, not a
    structured "request+response" cassette (à la `vcrpy`). If we ever
    need to test request-level behaviour (headers, retry loops), we
    can revisit.
-   **Live-HTTP integration tests.** Deferred until a real recording
    pass is completed end-to-end. The `live_http` marker exists for
    future use.

## 2026-04-23 policy strengthening

The first Phase-2 cut (commit `c0b1280`) merged with **synthetic**
cassettes under `tests/fixtures/phase2/cassettes/` and Phase-1
contract fixtures (`tests/fixtures/phase1/*.json`) hand-written by
the agent — fabricated names like `"Benjamin Netanyahu"`, fabricated
external IDs like `PersonID: 30800`, placeholder UUIDs of the form
`00000000-0000-4000-8000-000000000001`. This was tolerated *during*
the Phase-2 spike but is now **forbidden repo-wide**.

The replacement policy is codified as an `alwaysApply` Cursor rule
at `.cursor/rules/real-data-tests.mdc`:

-   Every fixture file under `tests/fixtures/**` that represents
    domain data must be the raw bytes of a real upstream recording,
    captured via `python -m civic_archival fetch --out <path>` (now
    extended with `--out`, `--max-bytes`, `--max-lines`).
-   Every cassette directory carries a sibling `SOURCE.md` citing
    the upstream URL, capture date, and SHA-256.
-   Domain UUIDs are deterministic `uuid5(PHASE2_UUID_NAMESPACE, …)`
    over the real upstream external ID — never invented.
-   Re-recording is a single `make record-cassettes` invocation,
    backed by `scripts/record-cassettes.sh`.
-   Enforced by `tests/smoke/test_alignment.py::test_no_synthetic_placeholders_in_fixtures`,
    which scans every fixture for telltale placeholder strings and
    fails the build if any reappear.

This closes the loophole where a synthetic fixture could pass the
adapter's unit test (because the test was pinned to the synthetic
shape) yet break against real upstream payloads — exactly the
"silent drift" failure mode Options 3 and 5 in the original Considered
Options were rejected for. As of `2026-04-23`, the five Phase-2
cassettes (people, committees, votes, sponsorships, attendance) are
real recordings from `knesset.gov.il/Odata/ParliamentInfo.svc/` (and
`oknesset.org/pipelines/data/votes/` for the per-MK vote CSV that
the official OData feed for member-level votes is bot-protected
behind), and all 12 Phase-1 contract fixtures are programmatically
re-derived from those cassettes via `scripts/generate-phase1-fixtures.py`.

## Related plan and contract references

-   `docs/political_verifier_v_1_plan.md` — archival requirement.
-   `docs/conventions/cassette-recording.md` — operational runbook.
-   `services/archival/src/civic_archival/cli.py` — the record
    command.
-   `services/ingestion/_common/src/civic_ingest/adapter.py` — the
    `fetch` callable seam.
