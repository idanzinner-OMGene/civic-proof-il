"""Small CLI for ad-hoc captures used by the VCR record workflow.

Usage::

    # print metadata only
    python -m civic_archival fetch <url>

    # record a real upstream cassette for tests
    python -m civic_archival fetch <url> \
        --out tests/fixtures/phase2/cassettes/people/sample.json

    # large CSV sources: cap the capture at N bytes or N lines (still
    # records the real upstream prefix byte-for-byte)
    python -m civic_archival fetch <url> \
        --out tests/fixtures/phase2/cassettes/votes/sample.csv \
        --max-lines 50
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .fetcher import Fetcher

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="civic_archival")
    sub = p.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch a URL and print metadata.")
    fetch.add_argument("url", nargs="?", help="URL to fetch (positional).")
    fetch.add_argument(
        "--url",
        dest="url_flag",
        help="URL to fetch (flag form — runbook style).",
    )
    fetch.add_argument(
        "--family",
        choices=["knesset", "gov_il", "elections"],
        default="knesset",
    )
    fetch.add_argument("--tier", type=int, choices=[1, 2, 3], default=1)
    fetch.add_argument(
        "--body",
        action="store_true",
        help="Also print the response body (truncated to 500 bytes).",
    )
    fetch.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Write the raw response bytes to this path. Parent directories "
            "are created if missing. Required for recording VCR cassettes."
        ),
    )
    fetch.add_argument(
        "--allow-error",
        action="store_true",
        help="Accept non-2xx responses (default: raise on 4xx/5xx).",
    )
    fetch.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help=(
            "Truncate the captured payload to this many bytes before writing "
            "to --out. The SHA-256 in the printed metadata is of the truncated "
            "bytes (= what the cassette file contains). Intended for very "
            "large upstream CSV dumps."
        ),
    )
    fetch.add_argument(
        "--max-lines",
        type=int,
        default=None,
        help=(
            "Truncate the captured payload to this many newline-terminated "
            "lines before writing to --out. Intended for CSV cassettes "
            "(preserves header + first N-1 rows)."
        ),
    )
    return p


def _truncate(content: bytes, *, max_bytes: int | None, max_lines: int | None) -> bytes:
    """Return ``content`` trimmed to at most ``max_bytes`` / ``max_lines``.

    ``max_lines`` takes precedence when both are given (CSV truncation is
    always line-aligned).
    """

    if max_lines is not None:
        lines = content.splitlines(keepends=True)
        content = b"".join(lines[:max_lines])
    if max_bytes is not None and len(content) > max_bytes:
        content = content[:max_bytes]
    return content


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch":
        url = args.url_flag or args.url
        if not url:
            parser.error("fetch requires either a positional URL or --url")
        with Fetcher() as f:
            result = f.fetch(url, allow_error=args.allow_error)

        raw_size = len(result.content)
        truncated = _truncate(
            result.content,
            max_bytes=args.max_bytes,
            max_lines=args.max_lines,
        )
        sha = hashlib.sha256(truncated).hexdigest()
        out: dict[str, object] = {
            "url": result.url,
            "status_code": result.status_code,
            "content_type": result.content_type,
            "upstream_byte_size": raw_size,
            "captured_byte_size": len(truncated),
            "content_sha256": sha,
            "fetched_at": result.fetched_at.isoformat(),
            "family": args.family,
            "tier": args.tier,
        }
        if args.max_lines is not None:
            out["max_lines"] = args.max_lines
        if args.max_bytes is not None:
            out["max_bytes"] = args.max_bytes
        if args.body:
            out["body_preview"] = truncated[:500].decode("utf-8", errors="replace")
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_bytes(truncated)
            out["out"] = str(args.out)
            out["bytes_written"] = len(truncated)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
