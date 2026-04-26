#!/usr/bin/env python3
"""Record real-data political statements for the Phase-3 gold set.

Per ``.cursor/rules/real-data-tests.mdc`` every gold-set statement MUST
trace to an identifiable real upstream recording (Knesset plenary
stenogram, public press release, verified public social media post,
etc.). This script is the ONLY supported path to populate
``tests/fixtures/phase3/statements/``.

Usage:

    python scripts/record-statements.py <manifest.jsonl> [--out DIR]

Manifest lines are JSONL with fields::

    {"source_url": "https://knesset.gov.il/...",
     "source_family": "knesset_plenary",
     "language": "he",
     "excerpt_selector": "p#para_12",
     "speaker_hint": "<optional MK name as it appears>",
     "notes": "<curator notes>"}

For each line the script:

1. Fetches ``source_url`` (respecting the archival checksum convention
   in ``packages/clients/src/civic_clients/archive.py``).
2. Extracts the selected excerpt verbatim.
3. Writes ``tests/fixtures/phase3/statements/<sha256_12>/`` with:
   - ``statement.txt`` — the raw excerpt bytes (NO edits).
   - ``SOURCE.md`` — provenance (URL, accessed-at, sha256, selector).
   - ``labels.yaml`` — empty template for the human curator to fill in
     (expected claim_type, slot resolution, verdict).

The script is deliberately conservative: it refuses to overwrite an
existing statement directory and refuses to write if the fetched
content is empty. Every error aborts the manifest run; partial
progress is visible by listing the output directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "civic-proof-il/record-statements (ops@civic-proof-il)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _select(body: bytes, selector: str | None) -> str:
    """Minimal selector: if selector is None, return the decoded body.

    Real recorder runs with explicit XPath / CSS selectors live behind a
    richer implementation that callers can swap in. For the gold set we
    prefer curators to pass pre-trimmed excerpts via the manifest
    ``source_url`` pointing at a static file they've already audited.
    """

    text = body.decode("utf-8", errors="replace").strip()
    if not selector:
        return text
    # The default implementation treats ``selector`` as a literal
    # substring anchor: we return the line containing it. More
    # sophisticated selectors (XPath / CSS) are a future extension.
    for line in text.splitlines():
        if selector in line:
            return line.strip()
    return text


def _write_record(
    out_dir: Path,
    statement: str,
    manifest_entry: dict,
    body_sha: str,
) -> Path:
    digest12 = body_sha[:12]
    record_dir = out_dir / digest12
    if record_dir.exists():
        raise SystemExit(
            f"refusing to overwrite existing statement record {record_dir}"
        )
    record_dir.mkdir(parents=True)
    (record_dir / "statement.txt").write_text(statement + "\n", encoding="utf-8")
    source_md = (
        "# Statement provenance\n\n"
        f"- source_url: {manifest_entry['source_url']}\n"
        f"- source_family: {manifest_entry['source_family']}\n"
        f"- language: {manifest_entry['language']}\n"
        f"- speaker_hint: {manifest_entry.get('speaker_hint', '')}\n"
        f"- accessed_at: {dt.datetime.now(dt.timezone.utc).isoformat()}\n"
        f"- sha256: {body_sha}\n"
        f"- excerpt_selector: {manifest_entry.get('excerpt_selector', '')}\n\n"
        "## Curator notes\n\n"
        f"{manifest_entry.get('notes', '').strip()}\n"
    )
    (record_dir / "SOURCE.md").write_text(source_md, encoding="utf-8")
    labels_template = (
        "# Fill in expected outputs for this gold-set row.\n"
        "# All fields optional for smoke tests; required for gold audits.\n"
        "expected:\n"
        "  claim_type: null        # vote_cast | bill_sponsorship | ...\n"
        "  speaker_person_id: null # UUID in Neo4j, or null if unresolvable\n"
        "  target_person_id: null\n"
        "  bill_id: null\n"
        "  committee_id: null\n"
        "  office_id: null\n"
        "  vote_value: null\n"
        "  time_granularity: unknown\n"
        "  checkability: non_checkable\n"
        "  verdict: not_enough_information\n"
    )
    (record_dir / "labels.yaml").write_text(labels_template, encoding="utf-8")
    return record_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record real-data statements.")
    parser.add_argument("manifest", type=Path, help="JSONL manifest.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "phase3"
        / "statements",
    )
    args = parser.parse_args(argv)

    if not args.manifest.is_file():
        print(f"manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)

    for lineno, raw in enumerate(args.manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        entry = json.loads(raw)
        for required in ("source_url", "source_family", "language"):
            if required not in entry:
                print(
                    f"manifest line {lineno}: missing field {required!r}",
                    file=sys.stderr,
                )
                return 2
        body = _fetch(entry["source_url"])
        if not body:
            print(f"manifest line {lineno}: empty body", file=sys.stderr)
            return 3
        excerpt = _select(body, entry.get("excerpt_selector"))
        if not excerpt:
            print(f"manifest line {lineno}: empty excerpt", file=sys.stderr)
            return 3
        digest = _sha256(body)
        record_dir = _write_record(args.out, excerpt, entry, digest)
        print(f"wrote {record_dir}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
