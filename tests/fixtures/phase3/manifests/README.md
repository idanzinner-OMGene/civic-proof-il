# Phase-3 statement recording manifests

JSONL manifests consumed by `scripts/record-statements.py`. Each line is
one statement to record, with these fields:

- `source_url` — the authoritative upstream URL (Knesset stenogram,
  press release, verified social post, etc.).
- `source_family` — matches one of the ingestion families
  (`knesset_plenary`, `knesset_committee`, `press_release`, etc.).
- `language` — `"he"` or `"en"`.
- `excerpt_selector` — optional substring anchor to trim the fetched
  body to a single line. For curated local files, prefer a URL that
  already points at the trimmed excerpt.
- `speaker_hint` — optional. The speaker's name as it appears in the
  source. Used by the curator to sanity-check entity resolution.
- `notes` — curator notes (why this statement, expected outcome).

## Batches

- `batch_01.jsonl` — placeholder; populate during the Phase-3 live
  acceptance run. Curators should distribute statements across the six
  claim_type families and across both languages.

Per plan lines 412-418 the target is ~25 statements total. The
alignment audit (`tests/smoke/test_alignment.py`, Phase-3 section)
asserts minimum counts per family once the batches are populated.
