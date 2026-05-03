"""Unit tests for the elections adapter.

Assertions are pinned to the first row and key aggregates of the real
recorded cassette at
``tests/fixtures/phase2/cassettes/elections/sample.html``.

Re-recording the cassette (fetching the CEC page again) may change data
only if the committee publishes revised official results, which is extremely
rare after final results are certified. Treat any assertion failure as a
legitimate signal.
"""

from __future__ import annotations

import math
import uuid
from pathlib import Path

import pytest

from civic_ingest_elections.normalize import normalize_election_result, normalize_page
from civic_ingest_elections.parse import parse_election_page
from civic_ingest_elections.party_list_mapping import (
    THRESHOLD_RULE,
    get_election_date,
    resolve_party_id,
)
from civic_ingest_elections.types import PHASE2_UUID_NAMESPACE

REPO_ROOT = Path(__file__).resolve().parents[4]
CASSETTE = REPO_ROOT / "tests/fixtures/phase2/cassettes/elections/sample.html"
CASSETTE_K24 = REPO_ROOT / "tests/fixtures/phase2/cassettes/elections/sample_k24.html"

KNESSET_NUMBER = 25
ELECTION_DATE = "2022-11-01T00:00:00"

KNESSET_24 = 24
ELECTION_DATE_K24 = "2021-03-23T00:00:00"


def _load_page():
    return parse_election_page(
        CASSETTE.read_bytes(),
        knesset_number=KNESSET_NUMBER,
        election_date=ELECTION_DATE,
    )


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_cassette_parses_correct_page_totals():
    page = _load_page()
    assert page.knesset_number == 25
    assert page.election_date == ELECTION_DATE
    assert page.eligible_voters == 6_788_804
    assert page.total_votes_cast == 4_794_593
    assert page.total_valid_votes == 4_764_742
    assert page.total_invalid_votes == 29_851


def test_cassette_has_40_lists():
    page = _load_page()
    assert len(page.rows) == 40


def test_cassette_first_row_is_likud():
    page = _load_page()
    first = page.rows[0]
    assert first.ballot_letters == "מחל"
    assert first.seats_won == 32
    assert first.votes == 1_115_336
    assert first.vote_share_pct == "23.41%"


def test_cassette_10_lists_won_seats():
    page = _load_page()
    seat_winners = [r for r in page.rows if r.seats_won > 0]
    assert len(seat_winners) == 10
    assert sum(r.seats_won for r in seat_winners) == 120


def test_cassette_shas_row_parses_correctly():
    """Shas row has a literal quote inside the title attribute (broken HTML).
    The parser must handle this gracefully via text content extraction."""
    page = _load_page()
    shas = next((r for r in page.rows if r.ballot_letters == "שס"), None)
    assert shas is not None, "Shas row (שס) missing from parsed results"
    assert shas.seats_won == 11
    assert shas.votes == 392_964


def test_cassette_total_valid_votes_equals_sum_of_list_votes():
    """Sum of per-list valid votes must equal the page-level valid vote total."""
    page = _load_page()
    assert sum(r.votes for r in page.rows) == page.total_valid_votes


# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------


def test_normalizer_produces_deterministic_uuid_for_likud():
    page = _load_page()
    likud_row = page.rows[0]
    results = list(normalize_election_result(likud_row, page))
    assert len(results) == 1
    expected_id = uuid.uuid5(PHASE2_UUID_NAMESPACE, "cec_election:25:מחל")
    assert results[0].election_result_id == expected_id


def test_normalizer_likud_passes_threshold():
    page = _load_page()
    likud_row = page.rows[0]
    result = next(iter(normalize_election_result(likud_row, page)))
    assert result.passed_threshold is True
    assert result.seats_won == 32
    assert result.vote_share == pytest.approx(0.2341, abs=1e-3)


def test_normalizer_threshold_boundary():
    """Meretz (מרצ) crossed 3.16% — below 3.25% threshold — so it should be False."""
    page = _load_page()
    meretz_row = next((r for r in page.rows if r.ballot_letters == "מרצ"), None)
    assert meretz_row is not None
    result = next(iter(normalize_election_result(meretz_row, page)))
    threshold_votes = math.ceil(page.total_valid_votes * THRESHOLD_RULE)
    assert meretz_row.votes < threshold_votes
    assert result.passed_threshold is False


def test_normalizer_all_40_rows():
    page = _load_page()
    results = list(normalize_page(page))
    assert len(results) == 40


def test_normalizer_threshold_count():
    page = _load_page()
    threshold_votes = math.ceil(page.total_valid_votes * THRESHOLD_RULE)
    passed = [r for r in normalize_page(page) if r.passed_threshold]
    assert len(passed) == 10
    for r in passed:
        assert r.votes >= threshold_votes


# ---------------------------------------------------------------------------
# Party mapping tests
# ---------------------------------------------------------------------------


def test_party_mapping_election_date():
    assert get_election_date(25) == "2022-11-01T00:00:00"


def test_party_mapping_likud_resolves_to_knesset_faction():
    party_id = resolve_party_id(25, "מחל")
    expected = uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_party:1096")
    assert party_id == expected


def test_party_mapping_shas_resolves_to_knesset_faction():
    party_id = resolve_party_id(25, "שס")
    expected = uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_party:1095")
    assert party_id == expected


def test_party_mapping_hadash_taal_resolves_to_knesset_faction():
    party_id = resolve_party_id(25, "ום")
    expected = uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_party:1103")
    assert party_id == expected


def test_party_mapping_below_threshold_list_gets_cec_uuid():
    """Meretz didn't enter K25; must get a cec_list UUID, not a knesset_party UUID."""
    party_id = resolve_party_id(25, "מרצ")
    expected = uuid.uuid5(PHASE2_UUID_NAMESPACE, "cec_list:25:מרצ")
    assert party_id == expected


def test_party_mapping_unknown_list_gets_cec_uuid():
    """Any ballot letters not in the mapping must fall back to cec_list UUID."""
    party_id = resolve_party_id(25, "xx")
    expected = uuid.uuid5(PHASE2_UUID_NAMESPACE, "cec_list:25:xx")
    assert party_id == expected


def test_party_mapping_normalizer_sets_correct_party_id_for_yesh_atid():
    page = _load_page()
    ya_row = next((r for r in page.rows if r.ballot_letters == "פה"), None)
    assert ya_row is not None
    result = next(iter(normalize_election_result(ya_row, page)))
    expected = uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_party:1102")
    assert result.list_party_id == expected


# ---------------------------------------------------------------------------
# Knesset 24 cassette (PR-4 gap fill)
# ---------------------------------------------------------------------------


def _load_k24_page():
    return parse_election_page(
        CASSETTE_K24.read_bytes(),
        knesset_number=KNESSET_24,
        election_date=ELECTION_DATE_K24,
    )


def test_k24_cassette_page_totals():
    page = _load_k24_page()
    assert page.knesset_number == 24
    assert page.election_date == ELECTION_DATE_K24
    assert page.total_valid_votes == 4_410_052
    assert len(page.rows) == 39


def test_k24_cassette_first_row_is_likud():
    page = _load_k24_page()
    first = page.rows[0]
    assert first.ballot_letters == "מחל"
    assert first.seats_won == 30
    assert first.votes == 1_066_892


def test_k24_party_mapping_likud_faction():
    party_id = resolve_party_id(24, "מחל")
    expected = uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_party:962")
    assert party_id == expected


def test_k24_party_mapping_joint_list_letters():
    """Joint list uses ballot letters 'ודעם' on the CEC page."""
    party_id = resolve_party_id(24, "ודעם")
    expected = uuid.uuid5(PHASE2_UUID_NAMESPACE, "knesset_party:964")
    assert party_id == expected


def test_k24_get_election_date():
    assert get_election_date(24) == ELECTION_DATE_K24


def test_k24_normalizer_threshold_lists():
    page = _load_k24_page()
    passed = [r for r in normalize_page(page) if r.passed_threshold]
    assert len(passed) == 13
    assert sum(r.seats_won for r in page.rows if r.seats_won > 0) == 120
