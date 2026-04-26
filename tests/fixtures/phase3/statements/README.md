# Phase-3 statement gold set

Real-data political statements that drive Phase-3 acceptance and the
~40-row alignment audit. Populated ONLY by
`scripts/record-statements.py` against a hand-curated JSONL manifest.

## Policy

Per `.cursor/rules/real-data-tests.mdc`, every file in this directory
must trace to a real upstream recording. NEVER hand-edit
`statement.txt` files. If a curator needs to fix a typo, rerun the
recorder against a corrected source and commit the replacement.

## Layout

Each gold-set row is a directory:

    <sha256-first-12-hex>/
      statement.txt    # raw excerpt bytes
      SOURCE.md        # provenance + curator notes
      labels.yaml      # expected claim_type / slots / verdict

The directory name is the first 12 hex chars of the sha256 of the
fetched source bytes — deterministic from the upstream URL's content.

## Target

The Phase-3 plan requires ~25 recordings spanning all six claim_type
families in both Hebrew and English. The ~40-row alignment audit in
`tests/smoke/test_alignment.py` asserts that enough rows exist per
family to keep coverage honest.

## Seeding

Manifests live under `tests/fixtures/phase3/manifests/` (JSONL). Run:

    python scripts/record-statements.py tests/fixtures/phase3/manifests/<batch>.jsonl

The manifest files are safe to commit; the recorded statements are
produced by the script and must not be hand-edited.
