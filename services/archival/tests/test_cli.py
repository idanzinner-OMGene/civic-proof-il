"""Unit tests for the civic_archival CLI.

The CLI is used to capture real upstream bytes into test cassettes
(see `docs/conventions/cassette-recording.md` + the `real-data-tests`
rule). These tests stub `Fetcher` so they don't touch the network;
the bytes themselves come from a `FetchResult` the test constructs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from civic_archival import cli as cli_mod
from civic_archival.fetcher import FetchResult


class _StubFetcher:
    """Stand-in Fetcher returning a fixed FetchResult."""

    def __init__(self, result: FetchResult):
        self._result = result

    def fetch(self, url: str, *, allow_error: bool = False) -> FetchResult:
        assert url == self._result.url
        return self._result

    def __enter__(self) -> "_StubFetcher":
        return self

    def __exit__(self, *_exc) -> None:
        return None


@pytest.fixture
def odata_result() -> FetchResult:
    body = b'{"@odata.context":"x","value":[{"PersonID":1}]}'
    return FetchResult(
        url="https://knesset.gov.il/OdataV4/ParliamentInfo.svc/KNS_Person?$top=1",
        status_code=200,
        content=body,
        content_type="application/json",
        fetched_at=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
    )


def _install_stub(monkeypatch: pytest.MonkeyPatch, result: FetchResult) -> None:
    monkeypatch.setattr(cli_mod, "Fetcher", lambda: _StubFetcher(result))


def test_fetch_prints_metadata_with_content_hash(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    odata_result: FetchResult,
) -> None:
    _install_stub(monkeypatch, odata_result)

    rc = cli_mod.main(["fetch", odata_result.url])
    assert rc == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["url"] == odata_result.url
    assert payload["status_code"] == 200
    assert payload["upstream_byte_size"] == len(odata_result.content)
    assert payload["captured_byte_size"] == len(odata_result.content)
    assert payload["content_sha256"] == hashlib.sha256(
        odata_result.content
    ).hexdigest()
    assert "out" not in payload


def test_fetch_writes_cassette_with_out(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    odata_result: FetchResult,
) -> None:
    _install_stub(monkeypatch, odata_result)

    target = tmp_path / "nested" / "cassettes" / "sample.json"
    rc = cli_mod.main(["fetch", odata_result.url, "--out", str(target)])
    assert rc == 0

    assert target.exists()
    assert target.read_bytes() == odata_result.content

    payload = json.loads(capsys.readouterr().out)
    assert payload["out"] == str(target)
    assert payload["bytes_written"] == len(odata_result.content)
    assert payload["content_sha256"] == hashlib.sha256(
        odata_result.content
    ).hexdigest()


def test_fetch_accepts_runbook_url_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    odata_result: FetchResult,
) -> None:
    _install_stub(monkeypatch, odata_result)

    target = tmp_path / "sample.json"
    rc = cli_mod.main(
        [
            "fetch",
            "--url",
            odata_result.url,
            "--out",
            str(target),
        ]
    )
    assert rc == 0
    assert target.read_bytes() == odata_result.content


def test_fetch_truncates_csv_by_max_lines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    csv_body = b"a,b,c\n1,2,3\n4,5,6\n7,8,9\n"
    result = FetchResult(
        url="https://example.test/large.csv",
        status_code=200,
        content=csv_body,
        content_type="text/csv",
        fetched_at=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
    )
    _install_stub(monkeypatch, result)

    target = tmp_path / "sample.csv"
    rc = cli_mod.main(
        [
            "fetch",
            result.url,
            "--out",
            str(target),
            "--max-lines",
            "2",
        ]
    )
    assert rc == 0
    assert target.read_bytes() == b"a,b,c\n1,2,3\n"

    payload = json.loads(capsys.readouterr().out)
    assert payload["upstream_byte_size"] == len(csv_body)
    assert payload["captured_byte_size"] == len(b"a,b,c\n1,2,3\n")
    assert payload["max_lines"] == 2


def test_fetch_truncates_by_max_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    body = b"x" * 1000
    result = FetchResult(
        url="https://example.test/blob",
        status_code=200,
        content=body,
        content_type="application/octet-stream",
        fetched_at=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
    )
    _install_stub(monkeypatch, result)

    target = tmp_path / "blob.bin"
    rc = cli_mod.main(
        ["fetch", result.url, "--out", str(target), "--max-bytes", "100"]
    )
    assert rc == 0
    assert target.read_bytes() == b"x" * 100
