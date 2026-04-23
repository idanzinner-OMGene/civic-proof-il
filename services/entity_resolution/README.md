# `civic-entity-resolution`

Deterministic-first entity resolution for civic domain entities
(`person`, `party`, `office`, `committee`, `bill`). Phase 2 ships the
MVP (steps 1-4 of the plan's six-step ladder); steps 5 (fuzzy) and 6
(LLM fallback) land in Phase 3.

Rules-before-LLM is a system-wide invariant (see Phase-0 design
decisions in `docs/PROJECT_STATUS.md`). This service exists to keep
that invariant enforceable.

## Resolution ladder (Phase 2 scope)

1. **External ID match** — Look up the upstream canonical ID
   (`knesset_person_id`, `knesset_committee_id`, …) as a Neo4j node
   property. Deterministic; no ambiguity possible.
2. **Exact normalized Hebrew match** — `normalize_hebrew(name)` →
   query Neo4j node's normalized-name property. Niqqud stripped, NFC
   normalized, whitespace collapsed.
3. **Curated alias match** — Look up `entity_aliases` (Phase-2 table,
   migration `0004`). Unique on
   `(entity_kind, alias_text, alias_locale)`. Curated entries are
   reviewer-written (Phase-5 workflow).
4. **Transliteration normalization** — `transliterate_hebrew(name)`
   (deterministic 22-letter table) → repeat step 2/3 against the
   transliteration column.
5. **Fuzzy matching** — Deferred to Phase 3.
6. **LLM fallback for ties** — Deferred to Phase 3 (strictly scoped
   to resolving ties among > 1 deterministic candidates; never
   creates new facts).

## Public surface

```python
from civic_entity_resolution import (
    normalize_hebrew,
    transliterate_hebrew,
    Candidate,
    ResolveResult,
    resolve,
)

result = resolve(
    kind="person",
    mention_text="אברהם בן דוד",
    external_ids={"knesset_person_id": 12345},
    locale="he",
    neo4j_driver=driver,
    pg_conn=conn,
)
# result.status ∈ {"resolved", "ambiguous", "unresolved"}
# result.canonical_id: UUID | None
# result.candidates: list[Candidate]
# result.method: "external_id" | "exact_he" | "alias" | "transliteration" | None
```

## Ambiguity handling

-   `person`-kind ambiguities write to the Phase-1 `entity_candidates`
    table (`mention_text`, `resolved_person_id`, `confidence`,
    `method`, `evidence`). The Phase-1 schema is person-scoped by
    design; Phase 3 must extend it for the other kinds.
-   Non-`person` ambiguities return `ResolveResult(status="ambiguous")`
    to the caller; the caller may route them to the review workflow
    or defer resolution.

## Gotchas

-   `normalize_hebrew` treats non-breaking space (`\xa0`) as
    whitespace — `str.split()` collapses it. Tests expect the
    collapsed form.
-   The transliteration table is deterministic but intentionally
    lossy (22 consonants, no vowels). It serves as a coarse filter,
    not a round-trip encoding.
-   `entity_aliases` is empty at migration time. Populating it is
    the reviewer's responsibility in Phase 5.
-   `PHASE2_UUID_NAMESPACE` in each adapter must stay stable — every
    resolver match is by business key (UUID5 of the external ID);
    drift creates orphan nodes.
