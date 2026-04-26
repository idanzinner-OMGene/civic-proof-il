#!/usr/bin/env python3
"""Report ingest freshness by adapter (Phase 6).

Reads Knesset adapter manifests and joins ``ingest_runs.stats->>'adapter'``
(Phase-6 drift fix) against ``MAX(started_at)`` per adapter.

Falls back to manifest-only output when Postgres is unreachable.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "services" / "ingestion" / "knesset" / "manifests"


def _cadence_min_interval_seconds(cadence: str | None) -> int | None:
    """Best-effort lower bound on seconds between runs (no croniter dep).

    Supports:
    - ``*/N * * * *`` — every N minutes
    - ``M H * * *`` with day/month/dow ``*`` — once per calendar day (~24h)
    - ``M * * * *`` — hourly at minute M
    """
    if not cadence or not str(cadence).strip():
        return None
    parts = str(cadence).strip().split()
    if len(parts) != 5:
        return None
    minute, hour, dom, month, dow = parts
    if minute.startswith("*/"):
        try:
            n = int(minute[2:])
        except ValueError:
            return None
        return max(60, n * 60)
    if dom == "*" and month == "*" and dow == "*":
        if hour == "*" and minute.isdigit():
            return 3600
        if hour.isdigit() and minute.isdigit():
            return 24 * 3600
    return 24 * 3600


def _fetch_last_runs() -> dict[str, datetime] | None:
    try:
        from civic_common.settings import get_settings
        from civic_clients.postgres import make_connection
    except Exception:  # noqa: BLE001
        return None
    try:
        get_settings()
    except Exception:  # noqa: BLE001
        return None
    try:
        with make_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT stats->>'adapter' AS adapter, MAX(started_at) AS last_at
                  FROM ingest_runs
                 WHERE stats ? 'adapter'
                   AND stats->>'adapter' IS NOT NULL
                 GROUP BY 1
                """
            )
            rows = cur.fetchall()
    except Exception:  # noqa: BLE001
        return None
    out: dict[str, datetime] = {}
    for adapter, last_at in rows:
        if adapter and last_at is not None:
            out[str(adapter)] = last_at if last_at.tzinfo else last_at.replace(tzinfo=UTC)
    return out


def main() -> int:
    if not MANIFEST_DIR.is_dir():
        print(f"no manifests at {MANIFEST_DIR}", file=sys.stderr)
        return 2

    last_by_adapter = _fetch_last_runs()
    postgres_ok = last_by_adapter is not None
    if not postgres_ok:
        last_by_adapter = {}

    now = datetime.now(tz=UTC)
    out: list[dict] = []
    for p in sorted(MANIFEST_DIR.glob("*.yaml")):
        try:
            m = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception as e:  # noqa: BLE001
            out.append({"name": p.name, "error": str(e)})
            continue

        adapter = m.get("adapter")
        cadence = m.get("cadence_cron")
        interval = _cadence_min_interval_seconds(cadence)
        last_at = last_by_adapter.get(str(adapter)) if adapter else None

        entry: dict = {
            "name": p.name,
            "adapter": adapter,
            "cadence_cron": cadence,
            "cadence_min_interval_seconds": interval,
            "postgres_join": postgres_ok,
        }
        if last_at is not None:
            entry["last_run_at"] = last_at.isoformat()
            if interval is not None:
                age = now - last_at
                threshold = timedelta(seconds=2 * interval)
                entry["stale"] = age > threshold
                entry["age_seconds"] = int(age.total_seconds())
            else:
                entry["stale"] = None
        else:
            entry["last_run_at"] = None
            entry["stale"] = None if postgres_ok else None
            if postgres_ok:
                entry["note"] = "no ingest_runs row with stats.adapter yet"

        out.append(entry)

    report = {
        "checked_at": now.isoformat(),
        "postgres_ingest_runs": postgres_ok,
        "manifests": out,
    }
    if not postgres_ok:
        report["postgres_warning"] = (
            "Postgres unreachable or query failed; manifest-only cadence metadata returned"
        )

    j = json.dumps(report, indent=2, default=str)
    (ROOT / "reports").mkdir(exist_ok=True)
    pout = ROOT / "reports" / "freshness_check.json"
    pout.write_text(j + "\n", encoding="utf-8")
    print(j)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
