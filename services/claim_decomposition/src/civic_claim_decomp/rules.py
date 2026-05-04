"""Per-claim_type regex templates (Hebrew + English).

Each template binds a named-group regex over either language to one of
the six ``claim_type`` families. Groups:

* ``subject`` — the canonical person the claim is about (speaker slot).
* ``bill`` — bill title / number fragment.
* ``committee`` — committee name fragment.
* ``office`` — office name fragment.
* ``vote_value`` — raw Hebrew/English word; normalized by the caller.
* ``time`` — raw time phrase; normalized by the temporal normalizer.

Templates are intentionally narrow. If the rule matches we extract the
named groups verbatim; the decomposer wires them into slot dicts and
sends them through slot-template validation before emitting a claim.
Unmatched statements fall through to the LLM fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Literal, Mapping, Pattern

from civic_ontology.models.atomic_claim import ClaimType

Language = Literal["he", "en"]

__all__ = ["RULE_TEMPLATES", "RuleMatch", "RuleTemplate", "iter_matches"]


@dataclass(frozen=True, slots=True)
class RuleTemplate:
    """One regex per (claim_type, language)."""

    claim_type: ClaimType
    language: Language
    pattern: Pattern[str]
    description: str
    election_threshold_below: bool = False


@dataclass(frozen=True, slots=True)
class RuleMatch:
    """A structured match from :func:`iter_matches`."""

    template: RuleTemplate
    groups: Mapping[str, str]
    span: tuple[int, int]


# ---------- Hebrew ----------------------------------------------------------
# Notes on style: Hebrew punctuation / MK quote idioms are varied. We accept
# common prepositions (``ב``, ``על``, ``נגד``, ``בעד``) and ignore diacritics
# (caller passes through ``normalize_hebrew`` when needed).

_HE_VOTE = re.compile(
    r"""
    (?P<subject>[\u0590-\u05FFA-Za-z'\"\-\s]{2,40}?)
    \s+
    (?:הצביע(?:ה)?|תמך(?:ה)?|התנגד(?:ה)?|נמנע(?:ה)?)
    \s+
    (?P<vote_value>בעד|נגד|נמנע(?:ה)?)?
    \s*
    (?:(?:ב(?:עד)?|על|נגד|לגבי)\s+)?
    (?:חוק|הצעת\s+חוק)
    \s+
    (?P<bill>[\u0590-\u05FF0-9A-Za-z'\"\-\s,]{2,120}?)
    (?:\s+(?:ב(?:-)?(?P<time>\d{4}|הקדנציה(?:\s+הקודמת)?|כנסת(?:\s+ה[-]?\d+)?)))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)

_HE_SPONSOR = re.compile(
    r"""
    (?P<subject>[\u0590-\u05FFA-Za-z'\"\-\s]{2,40}?)
    \s+
    (?:יזם(?:ה)?|הגיש(?:ה)?|חתם(?:ה)?\s+על|הציע(?:ה)?)
    \s+
    (?:את\s+)?
    (?:הצעת\s+חוק|חוק)
    \s+
    (?P<bill>[\u0590-\u05FF0-9A-Za-z'\"\-\s,]{2,120}?)
    (?:\s+(?:ב(?:-)?(?P<time>\d{4}|הקדנציה(?:\s+הקודמת)?|כנסת(?:\s+ה[-]?\d+)?)))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)

_HE_OFFICE = re.compile(
    r"""
    (?P<subject>[\u0590-\u05FFA-Za-z'\"\-\s]{2,40}?)
    \s+
    (?:כיהן(?:ה)?|שימש(?:ה)?|מונה|היה|הייתה)
    \s+
    (?:כ)?
    (?P<office>שר(?:ת)?(?:\s+[\u0590-\u05FF\-\s]+)?|סגן(?:ית)?\s+שר(?:ת)?(?:\s+[\u0590-\u05FF\-\s]+)?|ראש\s+הממשלה|חבר(?:ת)?\s+כנסת|יו"ר\s+[\u0590-\u05FF\-\s]+)
    (?:\s+(?:ב(?:-)?(?P<time>\d{4}|הקדנציה(?:\s+הקודמת)?|כנסת(?:\s+ה[-]?\d+)?)))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)

_HE_COMMITTEE_MEM = re.compile(
    r"""
    (?P<subject>[\u0590-\u05FFA-Za-z'\"\-\s]{2,40}?)
    \s+
    (?:היה|הייתה|כיהן(?:ה)?|חבר(?:ה)?(?:\s+ב)?)
    \s+
    (?:חבר(?:ה)?\s+)?
    (?:ב)?ועד(?:ת|ה)
    \s+
    (?P<committee>[\u0590-\u05FF0-9A-Za-z'\"\-\s,]{2,80}?)
    (?:\s+(?:ב(?:-)?(?P<time>\d{4}|הקדנציה(?:\s+הקודמת)?|כנסת(?:\s+ה[-]?\d+)?)))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)

_HE_COMMITTEE_ATT = re.compile(
    r"""
    (?P<subject>[\u0590-\u05FFA-Za-z'\"\-\s]{2,40}?)
    \s+
    (?:נכח(?:ה)?|השתתף(?:ה)?|פקד(?:ה)?)
    \s+
    (?:בישיבת|ב)
    (?:ועדת|ועדה)
    \s+
    (?P<committee>[\u0590-\u05FF0-9A-Za-z'\"\-\s,]{2,80}?)
    (?:\s+(?:ב(?:-)?(?P<time>\d{4}|הקדנציה(?:\s+הקודמת)?|כנסת(?:\s+ה[-]?\d+)?)))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)


# ---------- English ---------------------------------------------------------
_EN_VOTE = re.compile(
    r"""
    (?P<subject>[A-Z][A-Za-z'\-\s]{2,50}?)
    \s+
    (?:voted|cast\s+(?:a|their)\s+vote)
    \s+
    (?P<vote_value>for|against|in\s+favou?r\s+of|opposed|abstained|to\s+abstain)
    \s+
    (?:on\s+|the\s+)?
    (?:the\s+)?
    (?P<bill>[A-Za-z0-9'\"\-\s,]{3,120}?)
    \s+
    bill
    (?:\s+in\s+(?P<time>\d{4}|the\s+\d+(?:st|nd|rd|th)\s+Knesset|last\s+term))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE | re.IGNORECASE,
)

_EN_SPONSOR = re.compile(
    r"""
    (?P<subject>[A-Z][A-Za-z'\-\s]{2,50}?)
    \s+
    (?:sponsored|initiated|introduced|co-?sponsored)
    \s+
    (?:the\s+)?
    (?P<bill>[A-Za-z0-9'\"\-\s,]{3,120}?)
    \s+
    bill
    (?:\s+in\s+(?P<time>\d{4}|the\s+\d+(?:st|nd|rd|th)\s+Knesset|last\s+term))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE | re.IGNORECASE,
)

_EN_OFFICE = re.compile(
    r"""
    (?P<subject>[A-Z][A-Za-z'\-\s]{2,50}?)
    \s+
    (?:served\s+as|held\s+the\s+office\s+of|was\s+appointed)
    \s+
    (?:the\s+)?
    (?P<office>Prime\s+Minister|Minister\s+of\s+[A-Za-z\s]+|Deputy\s+Minister(?:\s+of\s+[A-Za-z\s]+)?|Member\s+of\s+Knesset|Chair(?:person)?\s+of\s+[A-Za-z\s]+)
    (?:\s+in\s+(?P<time>\d{4}|the\s+\d+(?:st|nd|rd|th)\s+Knesset|last\s+term))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE | re.IGNORECASE,
)

_EN_COMMITTEE_MEM = re.compile(
    r"""
    (?P<subject>[A-Z][A-Za-z'\-\s]{2,50}?)
    \s+
    (?:was\s+a\s+member\s+of|served\s+on|sat\s+on)
    \s+
    (?:the\s+)?
    (?P<committee>[A-Za-z0-9\-\s,]{2,80}?)
    \s+
    [Cc]ommittee
    (?:\s+in\s+(?P<time>\d{4}|the\s+\d+(?:st|nd|rd|th)\s+Knesset|last\s+term))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)

_EN_COMMITTEE_ATT = re.compile(
    r"""
    (?P<subject>[A-Z][A-Za-z'\-\s]{2,50}?)
    \s+
    (?:attended|was\s+present\s+at)
    \s+
    (?:a\s+|the\s+)?
    (?:session\s+of\s+)?
    (?:the\s+)?
    (?P<committee>[A-Za-z0-9\-\s,]{2,80}?)
    \s+
    [Cc]ommittee
    (?:\s+in\s+(?P<time>\d{4}|the\s+\d+(?:st|nd|rd|th)\s+Knesset|last\s+term))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)

# ---------- Electoral (election_result) ------------------------------------

_HE_ELECTION_SEATS = re.compile(
    r"""
    (?P<party>[\u0590-\u05FFA-Za-z'\"\-\s]{2,50}?)
    \s+
    (?:זכה(?:ה)?|קיבל(?:ה)?|זכתה|קיבלה)
    \s+
    (?:ב-?)?(?P<seats>\d{1,3})
    \s+
    (?:מנדטים|מושבים)
    (?:\s+(?:ב(?:-)?(?P<time>\d{4}|הקדנציה(?:\s+הקודמת)?|כנסת(?:\s+ה[-]?\d+)?)))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)

_HE_ELECTION_THRESHOLD_BELOW = re.compile(
    r"""
    (?P<party>[\u0590-\u05FFA-Za-z'\"\-\s]{2,45}?)
    \s+
    לא\s+עבר(?:ה)?
    \s+
    (?:את\s+)?
    אחוז\s+החסימה
    (?:\s+(?:ב(?:-)?(?P<time>\d{4}|כנסת(?:\s+ה[-]?\d+)?)))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE,
)

_EN_ELECTION_SEATS = re.compile(
    r"""
    (?P<party>[A-Z][A-Za-z'\-\s]{2,50}?)
    \s+
    (?:won|received|got)
    \s+
    (?P<seats>\d{1,3})
    \s+
    seats
    (?:\s+in\s+(?P<time>\d{4}|the\s+\d+(?:st|nd|rd|th)\s+Knesset|last\s+term))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE | re.IGNORECASE,
)

_EN_ELECTION_THRESHOLD_BELOW = re.compile(
    r"""
    (?P<party>[A-Z][A-Za-z'\-\s]{2,50}?)
    \s+
    did\s+not\s+pass
    \s+(?:the\s+)?
    electoral\s+threshold
    (?:\s+in\s+(?P<time>\d{4}|the\s+\d+(?:st|nd|rd|th)\s+Knesset|last\s+term))?
    [\.\?\!]?\s*\Z
    """,
    re.VERBOSE | re.IGNORECASE,
)

# ---------- Government decision (government_decision) -----------------------

_HE_GOV_DECISION_NUMBER = re.compile(
    r"""
    (?:
        (?:הממשלה\s+החליטה)|
        (?:בהחלטת?\s+ממשלה)|
        (?:החלטת?\s+ממשלה)
    )
    \s*
    (?:מספר|מס'?|מס\.?)?
    \s*
    (?P<decision_number>\d[\d/\-]*)
    (?:
        \s+(?:של\s+)?
        (?:הממשלה\s+)?
        (?:ה-?\s*)?
        (?P<government_number>\d{1,2})
    )?
    [\.\?\!,]?\s*
    """,
    re.VERBOSE,
)

_HE_GOV_DECISION_REF = re.compile(
    r"""
    (?:בהחלטה|להחלטה|החלטה)
    \s+
    (?:מספר|מס'?|מס\.?)
    \s*
    (?P<decision_number>\d[\d/\-]*)
    [\.\?\!,]?\s*
    """,
    re.VERBOSE,
)

_EN_GOV_DECISION_NUMBER = re.compile(
    r"""
    (?:
        (?:government\s+(?:decision|resolution)(?:\s+number)?)|
        (?:cabinet\s+(?:decision|resolution)(?:\s+number)?)|
        (?:the\s+cabinet\s+decided)
    )
    \s*
    (?:number\s+)?
    (?:no\.?\s+)?
    (?P<decision_number>\d[\d/\-]*)
    [\.\?\!,]?\s*
    """,
    re.VERBOSE | re.IGNORECASE,
)


RULE_TEMPLATES: tuple[RuleTemplate, ...] = (
    RuleTemplate("vote_cast", "he", _HE_VOTE, "Hebrew vote_cast template"),
    RuleTemplate("bill_sponsorship", "he", _HE_SPONSOR, "Hebrew sponsorship"),
    RuleTemplate("office_held", "he", _HE_OFFICE, "Hebrew office_held"),
    RuleTemplate("committee_membership", "he", _HE_COMMITTEE_MEM, "Hebrew committee membership"),
    RuleTemplate("committee_attendance", "he", _HE_COMMITTEE_ATT, "Hebrew committee attendance"),
    RuleTemplate("vote_cast", "en", _EN_VOTE, "English vote_cast template"),
    RuleTemplate("bill_sponsorship", "en", _EN_SPONSOR, "English sponsorship"),
    RuleTemplate("office_held", "en", _EN_OFFICE, "English office_held"),
    RuleTemplate("committee_membership", "en", _EN_COMMITTEE_MEM, "English committee membership"),
    RuleTemplate("committee_attendance", "en", _EN_COMMITTEE_ATT, "English committee attendance"),
    RuleTemplate("election_result", "he", _HE_ELECTION_SEATS, "Hebrew election seats"),
    RuleTemplate(
        "election_result",
        "he",
        _HE_ELECTION_THRESHOLD_BELOW,
        "Hebrew election below threshold",
        election_threshold_below=True,
    ),
    RuleTemplate("election_result", "en", _EN_ELECTION_SEATS, "English election seats"),
    RuleTemplate(
        "election_result",
        "en",
        _EN_ELECTION_THRESHOLD_BELOW,
        "English election below threshold",
        election_threshold_below=True,
    ),
    RuleTemplate(
        "government_decision",
        "he",
        _HE_GOV_DECISION_NUMBER,
        "Hebrew government decision by number (ממשלה החליטה / החלטת ממשלה מספר)",
    ),
    RuleTemplate(
        "government_decision",
        "he",
        _HE_GOV_DECISION_REF,
        "Hebrew government decision reference (בהחלטה מספר / להחלטה מספר)",
    ),
    RuleTemplate(
        "government_decision",
        "en",
        _EN_GOV_DECISION_NUMBER,
        "English government decision by number",
    ),
)


def iter_matches(statement: str, language: Language) -> Iterator[RuleMatch]:
    """Yield every ``RuleMatch`` for ``language`` over ``statement``.

    Matches may overlap; the caller (``decomposer.decompose``) decides
    how to resolve overlaps (prefer longer spans, then earlier-ordered
    templates).
    """

    for tmpl in RULE_TEMPLATES:
        if tmpl.language != language:
            continue
        for m in tmpl.pattern.finditer(statement):
            yield RuleMatch(
                template=tmpl,
                groups={k: v for k, v in m.groupdict().items() if v is not None},
                span=(m.start(), m.end()),
            )
