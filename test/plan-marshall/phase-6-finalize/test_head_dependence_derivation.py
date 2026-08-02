#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Derivation guard for the finalize-step ``head_dependent`` membership set.

HEAD-dependence used to be governed by ``HEAD_DEPENDENT_STEPS``, a six-member
set hand-maintained as prose in ``phase-6-finalize/SKILL.md`` and enumerated at
three separate sites. Because membership was hand-listed rather than derived, a
step that IS head-dependent by the governing discriminator — *"would this verdict
change if HEAD changed?"* — but was never added to the list kept a stale ``done``
record across a loop-back commit, standing as green for a diff it never examined.
``default:pre-submission-self-review`` is the clearest instance: it reviews the
plan's diff, yet it was absent from every copy of the set.

Membership is now a **derived frontmatter fact**: each step doc declares
``head_dependent: true`` in its own frontmatter, and the set is obtained by
reading that fact off every doc ``find_implementors()`` discovers. These tests
pin that derivation:

(a) The derived set is **non-empty**. A derivation that silently returned nothing
    would make every other assertion here vacuous, so this is checked first and
    on its own.
(b) It contains the two long-known members ``default:pre-push-quality-gate`` and
    ``default:ci-verify``.
(c) It contains the members the hand-maintained literal omitted —
    ``default:pre-submission-self-review``,
    ``project:finalize-step-plugin-doctor`` and
    ``project:finalize-step-era-stamp-fill``.
(d) It contains the project-tier members declared for the first time by the
    project-local sweep — ``project:finalize-step-lessons-housekeeping`` and
    ``project:finalize-step-review-retrospective``. These are a DISTINCT lower
    bound from (c): they were never members of the retired hand-maintained
    literal, so they are not instances of the omission defect (c) records —
    they are steps the sweep newly brought into the derived population.
(e) Every member declares the ``--head-at-completion`` persistence obligation in
    its own doc body. Declaring the fact without persisting the SHA would leave
    the dispatcher's re-entry check nothing to compare against, so the
    declaration and the obligation are checked together.

Plus the per-member mutation guard: the required-member lower bound spanning
(b), (c) and (d) is verified to fail for **each** required member independently,
so a guard that passes on one omission while missing another cannot read as
green. Without it, a single assertion over the whole set could be satisfied by an
accident of ordering and still hide a second omission — the exact shape of the
original defect.

**The population is derived from discovery, never hardcoded**, so a step added
later is covered automatically. And this module deliberately asserts **no
cardinality literal** (there is no ``len(derived) == 9``): a hardcoded count is
precisely the drift shape this plan removes, and it would have to be hand-edited
the first time a step is added or removed. The named-member assertions above are
lower bounds on a derived set, not a pinned enumeration of it.

The derivation reuses the registry's OWN path — ``find_implementors()`` for the
population and ``extension_discovery._read_frontmatter_fields`` for the fact — so
no second parser exists to drift from the one the registry uses.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import extension_discovery
from extension_discovery import find_implementors

#: The canonical ext-point value whose implementors carry the fact.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The frontmatter key that IS the membership declaration.
_FACT_KEY = 'head_dependent'

#: Members that the retired hand-maintained literal already carried.
_KNOWN_MEMBERS = (
    'default:pre-push-quality-gate',
    'default:ci-verify',
)

#: Members the hand-maintained literal OMITTED — each a live instance of the
#: defect this derivation fixes. Each is asserted independently below.
_PREVIOUSLY_OMITTED_MEMBERS = (
    'default:pre-submission-self-review',
    'project:finalize-step-plugin-doctor',
    'project:finalize-step-era-stamp-fill',
)

#: Project-tier steps the project-local sweep declares for the FIRST time. They
#: were never members of the retired hand-maintained literal, so they are not
#: instances of the omission defect ``_PREVIOUSLY_OMITTED_MEMBERS`` records —
#: keeping them in their own constant is what keeps each tuple's stated
#: provenance true of every member it holds.
_NEWLY_DECLARED_MEMBERS = (
    'project:finalize-step-lessons-housekeeping',
    'project:finalize-step-review-retrospective',
)

#: The lower bound the derived set must cover. NOT an enumeration of the set —
#: the set is derived and may legitimately be larger.
_REQUIRED_MEMBERS = (
    _KNOWN_MEMBERS + _PREVIOUSLY_OMITTED_MEMBERS + _NEWLY_DECLARED_MEMBERS
)

#: The persistence obligation every head-dependent step's doc body must carry.
_HEAD_AT_COMPLETION_FLAG = '--head-at-completion'


def _declares_head_dependent(doc_path: Path) -> bool:
    """Read the ``head_dependent`` fact off one discovered step doc.

    Reuses ``_read_frontmatter_fields`` — the same extraction primitive
    ``_build_implementor_record`` uses for every other implementor field — rather
    than re-implementing a frontmatter parser. The coerced value is narrowed with
    ``bool()`` exactly the way the registry narrows ``default_on``, so the two
    conditional booleans are read identically.
    """
    fields = extension_discovery._read_frontmatter_fields(doc_path, (_FACT_KEY,))
    return bool(fields.get(_FACT_KEY, False))


def _head_dependent_records() -> list[dict]:
    """Derive the head-dependent implementor records from discovery."""
    return [rec for rec in find_implementors(_EXT_POINT) if _declares_head_dependent(Path(rec['path']))]


def _head_dependent_names() -> set[str]:
    """Derive the head-dependent step-id set from discovery."""
    return {rec['name'] for rec in _head_dependent_records()}


def _missing_required(derived: set[str]) -> list[str]:
    """The membership predicate under test: which required members are absent.

    Factored out so the mutation guard can drive the SAME predicate the
    assertions use. A guard that re-implemented the check would prove nothing
    about the check that actually runs.
    """
    return [member for member in _REQUIRED_MEMBERS if member not in derived]


def test_derived_set_is_non_empty():
    """(a) The derivation resolves something — every later assertion depends on it."""
    derived = _head_dependent_names()

    assert derived, (
        'The head-dependent derivation returned an EMPTY set. Every membership '
        'assertion in this module would pass vacuously against an empty '
        'derivation, so this is checked first and separately. Either no step doc '
        f'declares {_FACT_KEY}: true, or find_implementors({_EXT_POINT!r}) '
        'discovered no step docs at all.'
    )


@pytest.mark.parametrize('member', _KNOWN_MEMBERS)
def test_derived_set_contains_known_member(member):
    """(b) The two members the retired literal already carried stay derived."""
    derived = _head_dependent_names()

    assert member in derived, (
        f'{member} is head-dependent but the derivation did not surface it. '
        f'Its authoritative step doc must declare {_FACT_KEY}: true in frontmatter. '
        f'Derived set: {sorted(derived)}'
    )


@pytest.mark.parametrize('member', _PREVIOUSLY_OMITTED_MEMBERS)
def test_derived_set_contains_previously_omitted_member(member):
    """(c) Each member the hand-maintained literal omitted is now derived.

    Parametrized per member rather than asserted as one set-containment, so a
    regression that drops exactly one of the three fails as one identifiable
    test instead of hiding inside a combined assertion.
    """
    derived = _head_dependent_names()

    assert member in derived, (
        f'{member} is one of the members the hand-maintained HEAD_DEPENDENT_STEPS '
        f'literal omitted — the defect this derivation exists to fix. Its step doc '
        f'must declare {_FACT_KEY}: true in frontmatter. Derived set: {sorted(derived)}'
    )


@pytest.mark.parametrize('member', _NEWLY_DECLARED_MEMBERS)
def test_derived_set_contains_newly_declared_member(member):
    """(d) Each project-tier step declared by the sweep is derived.

    Parametrized per member for the same reason (c) is: a regression that drops
    exactly one declaration fails as one identifiable test. Kept separate from
    (c) because these members carry a different provenance — they were newly
    declared, not omitted from a hand-maintained list.
    """
    derived = _head_dependent_names()

    assert member in derived, (
        f'{member} was brought into the head-dependent population by the '
        f'project-local sweep, so its step doc must declare {_FACT_KEY}: true in '
        f'frontmatter. Derived set: {sorted(derived)}'
    )


@pytest.mark.parametrize('omitted', _REQUIRED_MEMBERS)
def test_each_required_member_is_independently_load_bearing(omitted):
    """Mutation guard: dropping any ONE required member is detected on its own.

    Removing a single member from the derived set must make the membership
    predicate report exactly that member — no more, no fewer. This proves the
    check is sensitive to each member independently, so a derivation that
    silently omitted one while satisfying the others could never read as green.
    A single set-containment assertion cannot make that claim about itself.
    """
    derived = _head_dependent_names()
    assert omitted in derived, (
        f'Mutation guard precondition failed: {omitted} is not in the derived set, '
        'so removing it proves nothing. Fix the derivation first.'
    )

    mutated = derived - {omitted}

    assert _missing_required(mutated) == [omitted], (
        f'The membership predicate did not isolate {omitted} when it alone was '
        'removed from the derived set. A predicate that cannot detect each '
        'member independently can pass while silently missing one — which is '
        f'exactly how {omitted} (or a sibling) went unnoticed before. '
        f'Reported missing: {_missing_required(mutated)}'
    )


def test_every_member_declares_the_head_at_completion_obligation():
    """(e) Every derived member's doc body carries the SHA-persistence obligation.

    The frontmatter fact arms the dispatcher's re-entry check, but the check has
    nothing to compare against unless the step actually persists the SHA it
    computed its verdict at. Declaring the fact without documenting
    ``--head-at-completion`` would leave a member that re-fires on every entry
    (SHA absent reads as unverified), so the two are asserted together.

    The population is the DERIVED set, so a member added later is covered with
    no edit here.
    """
    offenders = []
    for record in _head_dependent_records():
        doc_path = Path(record['path'])
        body = doc_path.read_text(encoding='utf-8')
        if _HEAD_AT_COMPLETION_FLAG not in body:
            offenders.append(f"{record['name']} ({doc_path})")

    assert not offenders, (
        f'These head_dependent steps do not document the {_HEAD_AT_COMPLETION_FLAG} '
        'persistence obligation in their own doc body. Without it the dispatcher '
        'has no recorded SHA to compare the live HEAD against, so the declaration '
        f'buys nothing: {offenders}'
    )
