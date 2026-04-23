"""Unit tests for civic_ingest.handlers registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from civic_ingest import handlers


@dataclass
class _FakeJob:
    kind: str
    payload: dict[str, Any]


def setup_function(_fn):
    handlers.clear_registry()


def test_register_and_dispatch_default_handler():
    calls = []

    @handlers.register("fetch")
    def _h(job):
        calls.append(("default", job.kind))

    handlers.dispatch(_FakeJob(kind="fetch", payload={}))
    assert calls == [("default", "fetch")]


def test_adapter_specific_beats_default():
    calls = []

    @handlers.register("fetch")
    def _default(job):
        calls.append("default")

    @handlers.register("fetch", adapter="people")
    def _people(job):
        calls.append("people")

    handlers.dispatch(_FakeJob(kind="fetch", payload={"adapter": "people"}))
    handlers.dispatch(_FakeJob(kind="fetch", payload={"adapter": "votes"}))

    assert calls == ["people", "default"]


def test_dispatch_raises_when_no_handler():
    with pytest.raises(LookupError):
        handlers.dispatch(_FakeJob(kind="parse", payload={}))
