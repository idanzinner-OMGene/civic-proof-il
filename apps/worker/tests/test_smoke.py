import os

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_USER", "civic")
    monkeypatch.setenv("POSTGRES_PASSWORD", "civic_dev_pw")
    monkeypatch.setenv("POSTGRES_DB", "civic")
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "civic_dev_pw")


def test_worker_imports():
    from worker import main  # noqa: F401


def test_run_once_returns_ok():
    from worker.main import run_once
    from worker.settings import get_settings

    get_settings.cache_clear()
    result = run_once()
    # ``run_once`` always returns at least ``{env, ok}``. When Postgres
    # is reachable (``ENV=ci`` / live compose stack) it also adds
    # ``job: None | <uuid>``; assert subset to stay rerun-safe.
    assert result["env"] == "dev"
    assert result["ok"] is True


def test_run_forever_exits_on_flag(monkeypatch):
    from worker import main as worker_main
    from worker.settings import get_settings

    get_settings.cache_clear()

    ticks = []

    def fake_sleep(s):
        ticks.append(s)
        worker_main._should_exit = True

    worker_main._should_exit = False
    worker_main.run_forever(sleep_fn=fake_sleep)
    assert ticks == [30] or len(ticks) == 1
    worker_main._should_exit = False
