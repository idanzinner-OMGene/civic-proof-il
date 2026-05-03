"""Parser for CEC (ועדת הבחירות המרכזית) national election results pages.

Parses the official final results HTML for a given Knesset election from
``votesXX.bechirot.gov.il``. The page contains:

  - A summary table with totals (eligible voters, votes cast, valid votes, etc.)
  - A per-list results table with: list name, ballot letters, seats won,
    vote share %, and valid votes for the list.

The HTML is structurally stable across elections (same CSS classes and table
layout observed for K24 and K25). The parser is pinned to the K25 cassette
at ``tests/fixtures/phase2/cassettes/elections/sample.html``.

Known quirk: the Shas row (and potentially others) has a literal ASCII double-
quote character inside the ``title`` attribute (e.g. ``זצ"ל``), making the
attribute value ambiguous to a strict HTML parser. The parser handles this by
parsing the ``<tbody>`` content row-by-row and extracting cell text directly
rather than relying on the title attribute for the canonical list name.
"""

from __future__ import annotations

import re
from typing import Iterable

from .types import ParsedElectionPage, ParsedElectionRow

__all__ = ["parse_election_page"]


# --- Summary table patterns --------------------------------------------------

_SUMMARY_TABLE = re.compile(
    r'class="ResultsSummaryTable".*?<tr>\s*<th.*?</tr>\s*<tr>(.*?)</tr>',
    re.DOTALL,
)
_CELL_NUMBERS = re.compile(r'<td[^>]*>\s*([\d,\.%]+)\s*</td>')

# --- Per-list results table patterns -----------------------------------------

_TBODY = re.compile(r'<tbody>(.*?)</tbody>', re.DOTALL)
_TR_SPLIT = re.compile(r'<tr>')
_ALL_TD = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL)
_FLOAT_DIR = re.compile(r'class="FloatDir">\s*([\d,]+)\s*<')
_TAG_STRIP = re.compile(r'<[^>]+>')


def _strip_tags(html: str) -> str:
    return _TAG_STRIP.sub('', html).strip()


def parse_election_page(
    html_bytes: bytes,
    knesset_number: int,
    election_date: str,
) -> ParsedElectionPage:
    """Parse a CEC national results HTML page.

    Parameters
    ----------
    html_bytes:
        Raw bytes of the page (e.g. from ``Fetcher.fetch``).
    knesset_number:
        The Knesset number this page belongs to (e.g. 25).
    election_date:
        ISO-8601 date string for the election (e.g. ``"2022-11-01T00:00:00"``).
        Provided by the manifest / caller since the page itself does not always
        publish a machine-readable election date.

    Returns
    -------
    ParsedElectionPage
        Page-level totals plus one :class:`ParsedElectionRow` per list.
    """
    content = html_bytes.decode('utf-8', errors='replace')

    # -- Summary totals -------------------------------------------------------
    eligible_voters = 0
    votes_cast = 0
    valid_votes = 0
    invalid_votes = 0

    summary_m = _SUMMARY_TABLE.search(content)
    if summary_m:
        cells = _CELL_NUMBERS.findall(summary_m.group(1))
        # Column order: eligible, cast, turnout%, valid, invalid
        nums = [c.replace(',', '').replace('%', '') for c in cells]
        try:
            eligible_voters = int(nums[0]) if len(nums) > 0 else 0
            votes_cast = int(nums[1]) if len(nums) > 1 else 0
            valid_votes = int(nums[3]) if len(nums) > 3 else 0
            invalid_votes = int(nums[4]) if len(nums) > 4 else 0
        except (ValueError, IndexError):
            pass

    # -- Per-list rows --------------------------------------------------------
    tbody_m = _TBODY.search(content)
    rows: list[ParsedElectionRow] = []
    if tbody_m:
        rows = list(_parse_tbody(tbody_m.group(1)))

    return ParsedElectionPage(
        knesset_number=knesset_number,
        election_date=election_date,
        total_valid_votes=valid_votes,
        total_votes_cast=votes_cast,
        total_invalid_votes=invalid_votes,
        eligible_voters=eligible_voters,
        rows=rows,
    )


def _parse_tbody(tbody_html: str) -> Iterable[ParsedElectionRow]:
    """Yield one ParsedElectionRow per <tr> in the results tbody."""
    for chunk in _TR_SPLIT.split(tbody_html):
        if 'scope="row"' not in chunk:
            continue

        cells = _ALL_TD.findall(chunk)
        if len(cells) < 4:
            continue

        # Cell 0: list name (text content, possibly truncated)
        list_name = _strip_tags(cells[0])
        if not list_name:
            continue

        # Cell 1: ballot letters
        ballot_letters = _strip_tags(cells[1])

        # Cell 2: seats won (integer)
        seats_raw = _strip_tags(cells[2])
        try:
            seats_won = int(seats_raw)
        except ValueError:
            continue

        # Cell 3: vote share percentage string (e.g. "23.41%")
        vote_share_pct = _strip_tags(cells[3])

        # Last cell: votes count in a FloatDir div
        last_cell = cells[-1]
        votes_m = _FLOAT_DIR.search(last_cell)
        if votes_m:
            votes = int(votes_m.group(1).replace(',', ''))
        else:
            votes = 0

        yield ParsedElectionRow(
            list_name=list_name,
            ballot_letters=ballot_letters,
            seats_won=seats_won,
            vote_share_pct=vote_share_pct,
            votes=votes,
        )
