# Source manifests

Every ingestion adapter in `services/ingestion/` declares its upstream
contract in a YAML **manifest** file. Manifests are the single
authoritative declaration of "where does this data come from, what
tier is it, and how do we parse it?" No adapter may hard-code its own
URL, tier, or parser kind.

ADR-0004 records the decision to use YAML + Pydantic + JSON Schema;
this document is the operational runbook.

## File layout

```text
services/ingestion/<family>/manifests/<adapter>.yaml
```

Examples (Phase 2 + 2.5):

```text
services/ingestion/knesset/manifests/people.yaml
services/ingestion/knesset/manifests/committees.yaml
services/ingestion/knesset/manifests/votes.yaml
services/ingestion/knesset/manifests/sponsorships.yaml
services/ingestion/knesset/manifests/attendance.yaml
services/ingestion/knesset/manifests/positions.yaml
services/ingestion/knesset/manifests/bill_initiators.yaml
services/ingestion/knesset/manifests/committee_memberships.yaml
```

`<family>` is a whitelisted `SourceFamily` — currently `knesset`,
`gov_il`, `elections`. Adding a family is a two-step change (update
`SourceFamily` in `civic_ingest.manifest` **and** the
`SOURCE_FAMILIES` whitelist in `civic_clients.archive`).

`<adapter>` is an `AdapterKind` — currently `people`, `committees`,
`votes`, `sponsorships`, `attendance`, `positions`, `bill_initiators`,
`committee_memberships`. New kinds require a PR to the Pydantic
`Literal[…]` and the JSON Schema `enum`.

## Required fields

```yaml
family: knesset               # SourceFamily enum
adapter: people               # AdapterKind enum
source_url: https://knesset.gov.il/OdataV4/ParliamentInfo.svc/KNS_Person
source_tier: 1                # 1 = canonical, 2 = contextual, 3 = discovery
parser: odata_json            # ParserKind enum
cadence_cron: "0 4 * * *"     # 04:00 UTC daily
entity_hints:
  hebrew_name_field: FirstName
  external_id_field: PersonID
  locale: he
```

### Field semantics

| Field | Type | Notes |
|---|---|---|
| `family` | enum | Anchors the archive path (`s3://<bucket>/<family>/YYYY/MM/DD/<hash>.<ext>`). Must appear in `SOURCE_FAMILIES`. |
| `adapter` | enum | Selects which workspace package owns the adapter logic. |
| `source_url` | URL | Full upstream URL. No path params or query strings that vary per-run. |
| `source_tier` | 1 \| 2 \| 3 | Drives the verification layer's Tier-1 / Tier-2 / Tier-3 rules. Tier-1 = canonical, Tier-2 = contextual, Tier-3 = discovery-only. |
| `parser` | enum | Picks the deserializer. Phase-2 adapters all use `odata_json`. |
| `cadence_cron` | string | Crontab string. Syntax is not validated at manifest load time; validate expressions manually before committing. Used by `scripts/freshness_check.py` for staleness calculations. |
| `entity_hints.hebrew_name_field` | string? | JSON key where the Hebrew name lives (for the ontology mapper). |
| `entity_hints.external_id_field` | string? | Upstream canonical ID field (e.g. `PersonID`). |
| `entity_hints.locale` | `he` \| `en` | Default locale for text normalization. |

### Disallowed fields

The Pydantic model is configured with `extra="forbid"`. Unknown keys
raise `ValidationError` at adapter boot.

## Authoring workflow

1. Pick the `<family>/<adapter>` tuple. If either is new, PR the enum
   first.
2. Copy the closest existing manifest and update URL / cadence /
   entity hints.
3. Run the static alignment audit:

    ```bash
    uv run pytest tests/smoke/test_alignment.py -k manifest
    ```

    The audit asserts: file exists, name matches `<adapter>.yaml`,
    JSON Schema fields are present, Pydantic model validates.

4. Add unit-test cassettes under
   `tests/fixtures/phase2/cassettes/<adapter>/` and wire them into
   the adapter's tests.
5. For the first real recording pass, run
   `python -m civic_archival fetch <source_url>` (see
   [cassette-recording.md](cassette-recording.md)).

## How manifests are read at runtime

-   **Adapter CLI.** Every adapter's `python -m civic_ingest_<name>
    run --manifest <path>` reads the manifest via
    `civic_ingest.manifest.load_manifest`. The default path is the
    adapter's own manifest under
    `services/ingestion/knesset/manifests/<name>.yaml`.
-   **Worker.** The worker imports adapter modules at boot; each
    module registers its own handlers via `civic_ingest.handlers.register`.
    The adapter reads its manifest on demand when a job arrives.
-   **Alignment audit.** `tests/smoke/test_alignment.py` walks
    `services/ingestion/<family>/manifests/*.yaml` and asserts the
    file set matches the Pydantic-advertised `AdapterKind` enum.

## Contract location

-   **Pydantic model** —
    `services/ingestion/_common/src/civic_ingest/manifest.py` —
    `SourceManifest`.
-   **JSON Schema** —
    `data_contracts/jsonschemas/source_manifest.schema.json` —
    Draft 2020-12.
-   **ADR** — `docs/adr/0004-source-manifest-format.md`.

If the schema and model disagree, the static audit fails. Do not
silence the audit; fix the drift.

## Gotchas

-   **URL must be a full URL.** Pydantic's `HttpUrl` coerces but
    still requires scheme + host. No relative paths.
-   **Cron strings are not validated.** Typos land in your manifest
    silently. Test expressions manually (e.g. `python -c "import croniter; croniter.croniter('0 4 * * *')"`).
-   **`entity_hints` is optional but strict.** Omitting it is fine
    (the adapter defaults to `locale="he"`). Adding an unknown key
    raises.
-   **Locale values are enum'd.** Only `he` and `en` are valid.
    Mixed-language payloads should flag the dominant locale and let
    the parser handle the rest.
