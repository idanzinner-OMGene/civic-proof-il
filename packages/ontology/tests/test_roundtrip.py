"""Round-trip every Pydantic model: construct, dump JSON, re-parse, compare."""

from __future__ import annotations

from typing import Any

import pytest

from civic_ontology import (
    AtomicClaim,
    AttendanceEvent,
    Bill,
    Committee,
    Confidence,
    EvidenceSpan,
    MembershipTerm,
    Office,
    Party,
    Person,
    SourceDocument,
    TimeScope,
    Verdict,
    VoteEvent,
)

UUID_A = "00000000-0000-4000-8000-000000000001"
UUID_B = "00000000-0000-4000-8000-000000000002"
UUID_C = "00000000-0000-4000-8000-000000000003"
UUID_D = "00000000-0000-4000-8000-000000000004"
UUID_E = "00000000-0000-4000-8000-000000000005"
UUID_F = "00000000-0000-4000-8000-000000000006"
UUID_G = "00000000-0000-4000-8000-000000000007"
UUID_H = "00000000-0000-4000-8000-000000000008"
UUID_I = "00000000-0000-4000-8000-000000000009"
UUID_J = "00000000-0000-4000-8000-00000000000a"
UUID_K = "00000000-0000-4000-8000-00000000000b"
UUID_L = "00000000-0000-4000-8000-00000000000c"

TS_2024 = "2024-01-15T10:00:00Z"


def _sample_person() -> Person:
    return Person(
        person_id=UUID_A,
        canonical_name="Benjamin Netanyahu",
        hebrew_name="בנימין נתניהו",
        english_name="Benjamin Netanyahu",
        source_tier=1,
    )


def _sample_office() -> Office:
    return Office(
        office_id=UUID_B,
        canonical_name="Prime Minister of Israel",
        office_type="minister",
        scope="national",
    )


def _sample_party() -> Party:
    return Party(
        party_id=UUID_I,
        canonical_name="Likud",
        hebrew_name="הליכוד",
        english_name="Likud",
        abbreviation="LKD",
    )


def _sample_committee() -> Committee:
    return Committee(
        committee_id=UUID_J,
        canonical_name="Foreign Affairs and Defense Committee",
        hebrew_name="ועדת החוץ והביטחון",
    )


def _sample_bill() -> Bill:
    return Bill(
        bill_id=UUID_G,
        title="Bill X — Sample Legislation",
        knesset_number=25,
        status="first_reading",
    )


def _sample_vote_event() -> VoteEvent:
    return VoteEvent(
        vote_event_id=UUID_K,
        bill_id=UUID_G,
        occurred_at="2024-06-15T14:30:00Z",
        vote_type="plenum_first_reading",
    )


def _sample_attendance_event() -> AttendanceEvent:
    return AttendanceEvent(
        attendance_event_id=UUID_L,
        committee_id=UUID_J,
        occurred_at="2024-07-08T09:00:00Z",
    )


def _sample_membership_term() -> MembershipTerm:
    return MembershipTerm(
        membership_term_id=UUID_C,
        person_id=UUID_A,
        org_id=UUID_B,
        org_type="office",
        valid_from="2022-12-29T00:00:00Z",
        valid_to=None,
    )


def _sample_source_document() -> SourceDocument:
    return SourceDocument(
        document_id=UUID_D,
        source_family="knesset",
        source_tier=1,
        source_type="official_vote_record",
        url="https://main.knesset.gov.il/Activity/plenum/Pages/Vote.aspx?voteId=1",
        archive_uri="s3://civic-archive/knesset/2024/01/15/abc123.html",
        content_sha256="abc123abc123abc123abc123abc123abc123abc123abc123abc123abc123abcd",
        captured_at=TS_2024,
        language="he",
        title="Vote record",
        body="Sample body.",
    )


def _sample_evidence_span() -> EvidenceSpan:
    return EvidenceSpan(
        span_id=UUID_E,
        document_id=UUID_D,
        source_tier=1,
        source_type="official_vote_record",
        url="https://main.knesset.gov.il/Activity/plenum/Pages/Vote.aspx?voteId=1",
        archive_uri="s3://civic-archive/knesset/2024/01/15/abc123.html",
        text="sample evidence text",
        char_start=0,
        char_end=20,
        captured_at=TS_2024,
    )


def _sample_atomic_claim() -> AtomicClaim:
    return AtomicClaim(
        claim_id=UUID_F,
        raw_text="Netanyahu voted against bill X",
        normalized_text="Benjamin Netanyahu voted against bill X in 2024",
        claim_type="vote_cast",
        speaker_person_id=None,
        target_person_id=UUID_A,
        bill_id=UUID_G,
        committee_id=None,
        office_id=None,
        vote_value="against",
        party_id=None,
        expected_seats=None,
        expect_passed_threshold=None,
        time_scope=TimeScope(
            start="2024-01-01T00:00:00Z",
            end="2024-12-31T23:59:59Z",
            granularity="year",
        ),
        checkability="checkable",
        created_at=TS_2024,
    )


def _sample_verdict() -> Verdict:
    return Verdict(
        verdict_id=UUID_H,
        claim_id=UUID_F,
        status="supported",
        confidence=Confidence(
            source_authority=1.0,
            directness=0.9,
            temporal_alignment=1.0,
            entity_resolution=1.0,
            cross_source_consistency=0.8,
            overall=0.94,
        ),
        summary="Tier 1 vote record confirms.",
        needs_human_review=False,
        model_version="v0.1",
        ruleset_version="r0.1",
        created_at=TS_2024,
    )


SAMPLES: list[tuple[str, Any]] = [
    ("person", _sample_person()),
    ("office", _sample_office()),
    ("party", _sample_party()),
    ("committee", _sample_committee()),
    ("bill", _sample_bill()),
    ("vote_event", _sample_vote_event()),
    ("attendance_event", _sample_attendance_event()),
    ("membership_term", _sample_membership_term()),
    ("source_document", _sample_source_document()),
    ("evidence_span", _sample_evidence_span()),
    ("atomic_claim", _sample_atomic_claim()),
    ("verdict", _sample_verdict()),
]


@pytest.mark.parametrize("name,instance", SAMPLES, ids=[n for n, _ in SAMPLES])
def test_model_roundtrip(name: str, instance: Any) -> None:
    """Dump, re-parse, and compare — every model round-trips identically."""
    cls = type(instance)
    payload = instance.model_dump_json()
    reparsed = cls.model_validate_json(payload)
    assert reparsed == instance, f"round-trip drift in {name}"


def test_extra_fields_are_rejected() -> None:
    """extra='forbid' is enforced — unknown keys must raise."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        Person.model_validate(
            {
                "person_id": UUID_A,
                "canonical_name": "X",
                "not_a_real_field": "boom",
            }
        )


def test_vote_value_allows_null() -> None:
    claim = _sample_atomic_claim().model_copy(update={"vote_value": None})
    assert claim.vote_value is None
    payload = claim.model_dump_json()
    assert '"vote_value":null' in payload
