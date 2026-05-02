"""Declaration-level checkability classifier.

Aggregates the per-claim checkability values returned by
:func:`civic_claim_decomp.checkability.classify` across all claims derived from
a single utterance, and collapses them into one of the five
:data:`~civic_ontology.models.declaration.DeclarationCheckability` values.

This is **distinct** from the per-claim :func:`~civic_claim_decomp.checkability.classify`:
that function evaluates one ``AtomicClaim`` in isolation; this one answers the
question "how checkable is the *declaration as a whole*?"

Aggregation rules (highest-priority first):

1. **``checkable_formal_action``** — at least one claim whose per-claim
   checkability is ``"checkable"``.
2. **``partially_checkable``** — mixed bag: at least one ``"checkable"`` claim
   *and* at least one non-checkable claim. Because rule 1 fires on the same
   condition, this rule only triggers when the *remaining* claims (after removing
   checkable ones) are non-homogeneous — i.e., the mix includes both
   time/entity failures and outright non-checkable. In practice, rule 1 catches
   "some are checkable", so ``partially_checkable`` is reached when there are
   zero checkable claims but a heterogeneous failure set.
3. **``insufficient_time_scope``** — all claims are ``"insufficient_time_scope"``.
4. **``insufficient_entity_resolution``** — all claims are ``"insufficient_entity_resolution"``.
5. **``not_checkable``** — zero claims derived, all claims are ``"non_checkable"``,
   or a mix of non-checkable sub-types with no clear dominant failure.

Re-stated as a decision table over ``claim_checkabilities``:

| Any "checkable"? | Rest homogeneous? | Result |
|---|---|---|
| Yes | — | ``checkable_formal_action`` |
| No | all ``insufficient_time_scope`` | ``insufficient_time_scope`` |
| No | all ``insufficient_entity_resolution`` | ``insufficient_entity_resolution`` |
| No | heterogeneous non-checkable | ``partially_checkable`` |
| No | all ``non_checkable`` or empty | ``not_checkable`` |
"""

from __future__ import annotations

from collections import Counter

from civic_ontology.models.declaration import DeclarationCheckability

__all__ = ["classify_declaration_checkability"]

# Per-claim checkability values from civic_claim_decomp.checkability
_CHECKABLE = "checkable"
_NON_CHECKABLE = "non_checkable"
_INSUF_TIME = "insufficient_time_scope"
_INSUF_ENTITY = "insufficient_entity_resolution"


def classify_declaration_checkability(
    claim_checkabilities: list[str],
) -> DeclarationCheckability:
    """Collapse a list of per-claim checkability strings into a declaration-level value.

    Parameters
    ----------
    claim_checkabilities:
        Ordered list of per-claim ``Checkability`` strings. May be empty
        (when the decomposer produced zero claims).
    """
    if not claim_checkabilities:
        return "not_checkable"

    counts = Counter(claim_checkabilities)

    if counts[_CHECKABLE] > 0:
        return "checkable_formal_action"

    non_checkable = counts[_NON_CHECKABLE]
    insuf_time = counts[_INSUF_TIME]
    insuf_entity = counts[_INSUF_ENTITY]
    total = len(claim_checkabilities)

    if insuf_time == total:
        return "insufficient_time_scope"

    if insuf_entity == total:
        return "insufficient_entity_resolution"

    if non_checkable == total:
        return "not_checkable"

    # Heterogeneous failure set — declare partially_checkable rather than
    # picking an arbitrary dominant failure mode.
    if insuf_time > 0 or insuf_entity > 0:
        return "partially_checkable"

    return "not_checkable"
