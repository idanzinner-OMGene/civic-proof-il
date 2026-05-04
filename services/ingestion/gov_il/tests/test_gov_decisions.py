"""Unit tests for the gov_decisions adapter.

Assertions are pinned to the first row and key aggregates of the real
recorded cassette at
``tests/fixtures/phase2/cassettes/gov_decisions/sample.json``.

Re-recording the cassette will update these assertions only if BudgetKey
has materially changed the data, which should be treated as a real signal.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from civic_ingest_gov_decisions.normalize import normalize_decision, normalize_rows, _parse_government_number
from civic_ingest_gov_decisions.parse import parse_response, total_overall
from civic_ingest_gov_decisions.types import PHASE2_UUID_NAMESPACE

REPO_ROOT = Path(__file__).resolve().parents[4]
CASSETTE = REPO_ROOT / "tests/fixtures/phase2/cassettes/gov_decisions/sample.json"


def _load_rows():
    return parse_response(CASSETTE.read_bytes())


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_cassette_parses_nonzero_rows():
    rows = _load_rows()
    assert len(rows) > 0, "cassette must contain at least one formal decision"


def test_cassette_total_overall_is_populated():
    total = total_overall(CASSETTE.read_bytes())
    assert total > 100, "BudgetKey must report more than 100 numbered decisions"


def test_cassette_first_row_has_required_fields():
    rows = _load_rows()
    first = rows[0]
    assert first.budgetkey_id == "dc13f245-5109-41cd-aa18-f097f1d69bd8"
    assert first.procedure_number_str == "2084"
    assert first.title == "החלטה מספר 2084 - הרכבי ועדות לאיתור מועמדים"
    assert first.office == "נציבות שירות המדינה"
    assert first.publish_date == "2018-02-04T13:30:00"


def test_cassette_all_rows_have_title_and_budgetkey_id():
    rows = _load_rows()
    for row in rows:
        assert row.budgetkey_id, "every row must have a budgetkey_id"
        assert row.title, "every row must have a title"


def test_cassette_all_rows_are_formal_decisions():
    """Only rows with 'החלטות' in policy_type should be returned."""
    rows = _load_rows()
    for row in rows:
        if row.policy_type is not None:
            assert "החלטות" in row.policy_type, (
                f"Row {row.budgetkey_id} has unexpected policy_type: {row.policy_type!r}"
            )


# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------


def test_normalizer_produces_deterministic_uuid_for_first_row():
    rows = _load_rows()
    first = rows[0]
    result = normalize_decision(first)
    expected_id = uuid.uuid5(
        PHASE2_UUID_NAMESPACE,
        "budgetkey_gov_decision:dc13f245-5109-41cd-aa18-f097f1d69bd8",
    )
    assert result.government_decision_id == expected_id


def test_normalizer_first_row_fields():
    rows = _load_rows()
    result = normalize_decision(rows[0])
    assert result.decision_number == "2084"
    assert result.title == "החלטה מספר 2084 - הרכבי ועדות לאיתור מועמדים"
    assert result.issuing_body == "נציבות שירות המדינה"
    assert result.decision_date == "2018-02-04T13:30:00"
    assert result.government_number is None  # first record has null government field


def test_normalizer_all_rows_produce_unique_ids():
    rows = _load_rows()
    ids = [normalize_decision(r).government_decision_id for r in rows]
    assert len(ids) == len(set(ids)), "all normalized IDs must be unique"


def test_normalizer_summary_truncated_to_2000_chars():
    rows = _load_rows()
    long_text_rows = [r for r in rows if r.text and len(r.text) > 2000]
    for row in long_text_rows:
        result = normalize_decision(row)
        assert result.summary is not None
        assert len(result.summary) <= 2000


def test_normalizer_source_url_built_from_url_id():
    rows = _load_rows()
    rows_with_url_id = [r for r in rows if r.url_id]
    assert rows_with_url_id, "cassette must contain at least one row with url_id"
    result = normalize_decision(rows_with_url_id[0])
    assert result.source_url is not None
    assert result.source_url.startswith("https://www.gov.il/he/departments/policies/")
    assert rows_with_url_id[0].url_id in result.source_url


def test_normalize_rows_yields_same_count():
    rows = _load_rows()
    results = list(normalize_rows(rows))
    assert len(results) == len(rows)


# ---------------------------------------------------------------------------
# Government number parser tests (pure logic — no cassette required)
# ---------------------------------------------------------------------------


def test_parse_government_number_standard():
    assert _parse_government_number("הממשלה ה- 37") == 37


def test_parse_government_number_without_space():
    assert _parse_government_number("הממשלה ה-36") == 36


def test_parse_government_number_none():
    assert _parse_government_number(None) is None


def test_parse_government_number_empty():
    assert _parse_government_number("") is None


def test_parse_government_number_no_match():
    assert _parse_government_number("ממשלת ישראל") is None


def test_parse_government_number_34():
    assert _parse_government_number("הממשלה ה-34") == 34
