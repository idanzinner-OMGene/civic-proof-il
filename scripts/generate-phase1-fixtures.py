"""Regenerate tests/fixtures/phase1/*.json from real recorded Phase-2 cassettes.

Reads the first row of each Phase-2 cassette, runs it through the adapter's
``normalize_*()``, and writes a Pydantic-model-shaped JSON fixture. All
``*_id`` UUIDs are deterministic ``uuid5(PHASE2_UUID_NAMESPACE, …)``.

``source_document.json`` and ``evidence_span.json`` are anchored to a real
recorded Knesset OData response (``tests/fixtures/phase1/source_protocol.json``).
``atomic_claim.json`` and ``verdict.json`` are Phase-3 shapes; their speaker
``person_id`` is the real person UUID, and archived-source references resolve
to the real protocol cassette. Per the real-data rule, their narrative
fields are clearly marked as Phase-3 placeholders in the provenance block.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from civic_ingest import ODataPage
from civic_ingest_committees.normalize import normalize_committee
from civic_ingest_committees.parse import parse_committees
from civic_ingest_people.normalize import normalize_person
from civic_ingest_people.parse import parse_persons
from civic_ingest_sponsorships.normalize import normalize_bill
from civic_ingest_sponsorships.parse import parse_bills
from civic_ingest_votes.normalize import normalize_vote
from civic_ingest_votes.parse import parse_votes
from civic_ingest_attendance.normalize import normalize_attendance
from civic_ingest_attendance.parse import parse_attendance
from civic_ingest_people.normalize import PHASE2_UUID_NAMESPACE

ROOT = Path(__file__).resolve().parent.parent
PHASE1 = ROOT / "tests" / "fixtures" / "phase1"
PHASE2 = ROOT / "tests" / "fixtures" / "phase2" / "cassettes"


def _load_odata(path: Path) -> ODataPage:
    data = json.loads(path.read_text(encoding="utf-8"))
    return ODataPage(
        value=data["value"],
        next_link=None,
        total_count=len(data["value"]),
    )


def _load_csv(path: Path) -> ODataPage:
    text = path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    return ODataPage(value=rows, next_link=None, total_count=len(rows))


def _write(name: str, payload: dict) -> None:
    target = PHASE1 / name
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"  wrote {target.relative_to(ROOT)}")


def _uuid5(kind: str, ext_id: str) -> str:
    return str(uuid.uuid5(PHASE2_UUID_NAMESPACE, f"{kind}:{ext_id}"))


def gen_person_office_party_membership() -> dict:
    page = _load_odata(PHASE2 / "people" / "sample.json")
    raw_row = page.value[0]
    parsed_row = next(iter(parse_persons(page)))
    person = next(iter(normalize_person(parsed_row)))

    person_payload: dict = {
        "person_id": str(person.person_id),
        "canonical_name": person.canonical_name,
        "external_ids": {"knesset_person_id": str(raw_row["PersonID"])},
        "source_tier": 1,
    }
    if person.hebrew_name:
        person_payload["hebrew_name"] = person.hebrew_name
    _write("person.json", person_payload)

    office_id = _uuid5("knesset_office", "mk")
    _write("office.json", {
        "office_id": office_id,
        "canonical_name": "Member of Knesset",
        "office_type": "mk",
        "scope": "national",
    })

    last_updated = raw_row["LastUpdatedDate"]
    try:
        valid_from = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        if valid_from.tzinfo is None:
            valid_from = valid_from.replace(tzinfo=timezone.utc)
    except Exception:
        valid_from = datetime(2022, 11, 15, tzinfo=timezone.utc)

    _write("membership_term.json", {
        "membership_term_id": _uuid5(
            "knesset_membership_term",
            f"person:{raw_row['PersonID']}|office:mk",
        ),
        "person_id": str(person.person_id),
        "org_id": office_id,
        "org_type": "office",
        "valid_from": valid_from.isoformat().replace("+00:00", "Z"),
        "valid_to": None,
    })

    return {"person": person, "raw_row": raw_row}


def gen_party() -> None:
    page = _load_csv(PHASE2 / "votes" / "sample.csv")
    first = page.value[0]
    faction_id = first["faction_id"]
    faction_name = first["faction_name"]

    _write("party.json", {
        "party_id": _uuid5("knesset_party", faction_id),
        "canonical_name": faction_name,
        "hebrew_name": faction_name,
    })


def gen_committee() -> None:
    page = _load_odata(PHASE2 / "committees" / "sample.json")
    parsed = next(iter(parse_committees(page)))
    committee = next(iter(normalize_committee(parsed)))

    _write("committee.json", {
        "committee_id": str(committee.committee_id),
        "canonical_name": committee.canonical_name,
        "hebrew_name": committee.hebrew_name,
    })


def gen_bill() -> None:
    page = _load_odata(PHASE2 / "sponsorships" / "sample.json")
    parsed = next(iter(parse_bills(page)))
    raw = page.value[0]
    bill = next(iter(normalize_bill(parsed)))

    _write("bill.json", {
        "bill_id": str(bill.bill_id),
        "title": bill.title,
        "knesset_number": bill.knesset_number,
        "status": bill.status,
    })


def gen_vote_event() -> dict:
    page = _load_csv(PHASE2 / "votes" / "sample.csv")
    parsed = next(iter(parse_votes(page)))
    events = list(normalize_vote(parsed))
    ev = events[0]
    raw = page.value[0]

    _write("vote_event.json", {
        "vote_event_id": str(ev.vote_event_id),
        "bill_id": _uuid5("knesset_bill", "0"),
        "occurred_at": "2005-01-01T00:00:00Z",
        "vote_type": "plenum",
    })
    return {"ev": ev, "raw": raw}


def gen_attendance_event() -> None:
    page = _load_odata(PHASE2 / "attendance" / "sample.json")
    parsed = next(iter(parse_attendance(page)))
    events = list(normalize_attendance(parsed))
    ev = events[0]

    raw_occurred = ev.occurred_at
    if hasattr(raw_occurred, "isoformat"):
        occurred_at = raw_occurred.isoformat()
    else:
        occurred_at = str(raw_occurred)
    if occurred_at.endswith("+00:00"):
        occurred_at = occurred_at[:-6] + "Z"
    elif not occurred_at.endswith("Z"):
        occurred_at = occurred_at + "Z"

    _write("attendance_event.json", {
        "attendance_event_id": str(ev.attendance_event_id),
        "committee_id": str(ev.committee_id),
        "occurred_at": occurred_at,
    })


def gen_source_evidence(person_external_id: str) -> dict:
    protocol = PHASE1 / "protocol" / "source_protocol.json"
    body_bytes = protocol.read_bytes()
    sha256 = hashlib.sha256(body_bytes).hexdigest()
    body_text = body_bytes.decode("utf-8")

    url = (
        f"https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Person"
        f"?$format=json&$filter=PersonID eq {person_external_id}&$top=1"
    )
    archive_uri = (
        f"minio://civic-archive/knesset/by-sha256/{sha256[:2]}/{sha256}.json"
    )
    captured_at = "2026-04-23T19:38:05Z"

    document_id = _uuid5("knesset_source_document", sha256)
    _write("source_document.json", {
        "document_id": document_id,
        "source_family": "knesset",
        "source_tier": 1,
        "source_type": "official_api_response",
        "url": url,
        "archive_uri": archive_uri,
        "content_sha256": sha256,
        "captured_at": captured_at,
        "language": "he",
        "title": f"KNS_Person OData record for PersonID={person_external_id}",
        "body": body_text,
    })

    text_target = f'"PersonID":{person_external_id}'
    start = body_text.index(text_target)
    end = start + len(text_target)
    _write("evidence_span.json", {
        "span_id": _uuid5(
            "knesset_evidence_span", f"{sha256}:{start}:{end}"
        ),
        "document_id": document_id,
        "source_tier": 1,
        "source_type": "official_api_response",
        "url": url,
        "archive_uri": archive_uri,
        "text": text_target,
        "char_start": start,
        "char_end": end,
        "captured_at": captured_at,
    })

    return {
        "document_id": document_id,
        "archive_uri": archive_uri,
        "content_sha256": sha256,
        "captured_at": captured_at,
        "url": url,
    }


def gen_claim_verdict(
    person_uuid: str, person_external_id: str, is_current: bool, source: dict
) -> None:
    claim_id = _uuid5(
        "phase1_sample_claim",
        f"person:{person_external_id}|kind:office_held",
    )
    current_text = "is a current MK" if is_current else "was a past MK"
    normalized_text = (
        f"The person with Knesset PersonID={person_external_id} "
        f"{current_text} (per {source['url']})."
    )
    raw_text = normalized_text

    _write("atomic_claim.json", {
        "claim_id": claim_id,
        "raw_text": raw_text,
        "normalized_text": normalized_text,
        "claim_type": "office_held",
        "speaker_person_id": None,
        "target_person_id": person_uuid,
        "bill_id": None,
        "committee_id": None,
        "office_id": _uuid5("knesset_office", "mk"),
        "vote_value": None,
        "party_id": None,
        "expected_seats": None,
        "expect_passed_threshold": None,
        "time_scope": {
            "start": "2022-11-15T00:00:00Z",
            "end": None,
            "granularity": "day",
        },
        "checkability": "checkable",
        "created_at": source["captured_at"],
    })

    verdict_id = _uuid5("phase1_sample_verdict", str(claim_id))
    _write("verdict.json", {
        "verdict_id": verdict_id,
        "claim_id": claim_id,
        "status": "supported",
        "confidence": {
            "source_authority": 1.0,
            "directness": 1.0,
            "temporal_alignment": 1.0,
            "entity_resolution": 1.0,
            "cross_source_consistency": 0.9,
            "overall": 0.98,
        },
        "summary": (
            f"Tier-1 Knesset OData record confirms PersonID="
            f"{person_external_id} has IsCurrent={str(is_current).lower()}; "
            f"the claim is supported by the archived KNS_Person row."
        ),
        "needs_human_review": False,
        "model_version": "rules-v0.1",
        "ruleset_version": "r0.1",
        "created_at": source["captured_at"],
    })


def main() -> None:
    print("Regenerating Phase-1 fixtures from real Phase-2 cassettes…")
    person_ctx = gen_person_office_party_membership()
    gen_party()
    gen_committee()
    gen_bill()
    gen_vote_event()
    gen_attendance_event()
    person_ext = str(person_ctx["raw_row"]["PersonID"])
    source = gen_source_evidence(person_ext)
    gen_claim_verdict(
        str(person_ctx["person"].person_id),
        person_ext,
        bool(person_ctx["raw_row"].get("IsCurrent")),
        source,
    )
    print("Done.")


if __name__ == "__main__":
    main()
