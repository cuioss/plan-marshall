#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
"""Population guard: every executor-invoking skill document reaches the convention.

The guard re-runs the D1 derivation over the live tree rather than reading a
committed list, so a document added tomorrow that invokes a non-``manage-*``
script fails here on arrival without anyone remembering to list it.

Two properties, deliberately separate
-------------------------------------

The convention is stated ONCE and referenced everywhere else, so a green tree has
to satisfy two independent things — and one predicate cannot check both, because
a reintroduced verbatim copy satisfies the first while violating the second:

* **Coverage** — no retained document is left with no rule (``none`` empty) and
  none stops at the ``manage-*`` boundary (``narrow`` empty).
* **Single-sourcing** — the contract's body occurs in exactly one document, and
  every other retained document reaches it by reference.

The second is the one this rework turns on. Every copy of a duplicated
convention is individually correct, so coverage alone stays green on a tree that
has silently gone back to hand-maintaining N copies of a paragraph whose
duplication has already produced two multi-site defects at two consecutive HEADs.

Why the size is published rather than merely asserted
-----------------------------------------------------

Every assertion below is over a DERIVED population, and the failure messages
already carry its size. That leaves the one case a message cannot reach: a
derivation that quietly narrowed — a changed walk root, a regex that stopped
matching — and then satisfied every assertion over the smaller set. A green run
reports nothing, so a population that collapsed to three documents looks exactly
like one that covered all of them.

``GUARD_POPULATION_LABEL`` / ``GUARD_POPULATION_SIZE`` are read by the root
conftest's ``pytest_report_header``, which prints them at session start on EVERY
run, passing included. They are declared at module level rather than reported
from a test body because a test-body ``print`` is not a publication channel on
the canonical ``module-tests`` / ``verify`` path: that path carries no ``-s`` /
``--capture=no`` / ``-rP``, so pytest captures and discards a passing test's
stdout — the only run on which the population line is supposed to appear.

Relationship to the existing exit-code-convention guard
--------------------------------------------------------

``phase-6-finalize/test_review_merge_invocation_contract.py`` also pins this
convention, and the two now stand in a relationship that needs stating plainly:

* That guard sweeps **two skills** — ``phase-6-finalize`` and
  ``automatic-review`` — and pins the exact literal text of the exit-0-non-success
  disposition clause, together with the disposition body beneath it.
* This guard sweeps **every bundle's skill documents** and asserts that each one
  REACHES the contract, plus that the contract has exactly one body.

The two once pulled against each other: a per-document literal-clause assertion
needs the clause text present in every obligated document, while the single-body
assertion here needs it absent from all but the canonical standard, and both
cannot hold over one document set. That is settled, and settled by strengthening
rather than by softening. The finalize guard now pins the literal AND its
disposition body **at the canonical standard, unconditionally**, and each
obligated document discharges its own obligation by referencing that standard —
so the clause is pinned exactly once, which is what this module measures, and
every reference terminates in a document that guard checks rather than in a link
nobody follows. Its matched control gained an arm for the mutation the
arrangement newly permits: a document left untouched and correct while the one
standard it points at is gutted.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HELPER_DIR = Path(__file__).resolve().parent
if str(_HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(_HELPER_DIR))

import _exit_code_convention_derivation as derivation

#: Derived once at import. The same object backs every assertion below and the
#: published size, so the number reported is the number actually swept.
DERIVATION = derivation.derive()

#: The companion measurement: how many documents state the contract in full.
#: Derived from a content sweep over the same walked document set, never from an
#: enumerated list of expected paths.
BODY_SWEEP = derivation.sweep_convention_bodies()

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. A row naming this module lives in that file's
#: ``_ROUTING_GUARD_MODULES``; the roster guard fails if the two drift apart.
#:
#: The label carries the single-body measurement alongside the population because
#: the header publishes ONE number per module, and both numbers have to survive a
#: passing run. The occurrence count is the one this plan turns on: a run that
#: reports ``1 body`` is showing the property was measured, while a reintroduced
#: copy would print ``2 bodies`` in the ordinary output of every run, passing or
#: not. The swept count rides along so a body count taken over a collapsed walk
#: cannot look like a healthy one.
GUARD_POPULATION_LABEL = (
    f'executor-invoking skill docs ({BODY_SWEEP.occurrences} convention '
    f'{"body" if BODY_SWEEP.occurrences == 1 else "bodies"} '
    f'over {BODY_SWEEP.coverage.files_scanned} swept)'
)
GUARD_POPULATION_SIZE = DERIVATION.population_size


def test_the_derived_population_is_non_empty():
    """The derivation retained real documents, so the assertions below are not vacuous.

    This is the check that keeps a green run honest: every assertion after it is
    a claim about an empty class, and an empty class over an empty population is
    satisfied by a derivation that found nothing at all.
    """
    assert DERIVATION.population_size > 0, (
        'the derivation retained no documents at all, so every assertion below would pass '
        f'vacuously. Scanned {DERIVATION.coverage.files_scanned} file(s) — check the walk root.'
    )
    assert DERIVATION.coverage.files_scanned > 0, (
        'the walk scanned no documents, so the population above is the absence of a measurement '
        'rather than a measurement of absence.'
    )


def test_the_walk_reached_every_document():
    """No document was unreadable, so an empty class is a measurement and not a gap.

    Per ADR-019 the clean verdict is reserved for a complete walk: a file the
    derivation could not decode is a file that might carry a missing convention
    and was never classified.
    """
    assert DERIVATION.coverage.unreadable == (), (
        f'{len(DERIVATION.coverage.unreadable)} document(s) could not be read, so the empty '
        f'classes below cover less than the tree: {list(DERIVATION.coverage.unreadable)}'
    )
    assert DERIVATION.coverage.complete, (
        'coverage is incomplete, so no clean verdict may be drawn from the classes below.'
    )


def test_every_derived_document_carries_an_exit_code_convention():
    """The ``none`` class is empty: no retained document is left with no rule at all.

    A document in this class invokes a script through the executor whose skill
    segment is not ``manage-*`` — so a caller reading it gets no exit-code rule,
    while the script it names may print ``status: error`` at exit 0.
    """
    assert DERIVATION.none == (), (
        f'{len(DERIVATION.none)} of {DERIVATION.population_size} executor-invoking document(s) '
        f'carry no exit-code convention at all: {list(DERIVATION.none)}. Each invokes a '
        'non-manage-* script, so its reader has no rule for a status: error return at exit 0.'
    )


def test_no_derived_document_keeps_the_manage_scoped_form():
    """The ``narrow`` class is empty: no retained document stops at the ``manage-*`` boundary.

    A ``manage-*``-scoped convention in a document that invokes ``ci`` is the
    precise defect this plan closes — the rule is present, reads as complete, and
    does not reach the call that needs it.
    """
    assert DERIVATION.narrow == (), (
        f'{len(DERIVATION.narrow)} of {DERIVATION.population_size} executor-invoking document(s) '
        f'carry a convention scoped to manage-* only: {list(DERIVATION.narrow)}. Replace the '
        'narrow form outright with a reference to '
        f'{derivation.CANONICAL_STANDARD} rather than adding one alongside it.'
    )


# ---------------------------------------------------------------------------
# Single body — the convention is stated in exactly one place
# ---------------------------------------------------------------------------


def test_the_convention_is_stated_in_exactly_one_document():
    """The contract has ONE body in the tree, and it is the canonical standard.

    This is the assertion that makes the cross-reference arrangement structural
    rather than merely intended. The convention was previously duplicated across
    the tree, and that duplication produced two multi-site defects at two
    consecutive HEADs — a fix landing in some copies and not others. Without this
    test a future edit could reintroduce a verbatim copy and nothing would fail:
    every copy is individually *correct*, so the population guard above stays
    green on a tree that has silently gone back to hand-maintaining N copies.

    The count is DERIVED from a content sweep over the walked document set, never
    from an enumerated list of expected paths.
    """
    assert BODY_SWEEP.documents == (derivation.CANONICAL_STANDARD,), (
        f'the convention body occurs in {BODY_SWEEP.occurrences} document(s) rather than in the '
        f'canonical standard alone: {list(BODY_SWEEP.documents)}. Expected exactly '
        f'{derivation.CANONICAL_STANDARD}. Swept {BODY_SWEEP.coverage.files_scanned} document(s).'
    )


def test_the_single_body_sweep_reached_the_whole_tree():
    """The sweep's coverage is clean, so a count of one is a measurement.

    An unreadable document is one that might carry a second body, and a sweep
    that scanned nothing would report a single body it never looked for.
    """
    assert BODY_SWEEP.coverage.unreadable == (), (
        f'{len(BODY_SWEEP.coverage.unreadable)} document(s) could not be read, so the '
        f'occurrence count covers less than the tree: {list(BODY_SWEEP.coverage.unreadable)}'
    )
    assert BODY_SWEEP.coverage.complete, (
        f'the body sweep scanned {BODY_SWEEP.coverage.files_scanned} document(s) with '
        'incomplete coverage, so its single-body result is not a clean verdict.'
    )


def test_every_other_retained_document_carries_only_a_reference():
    """No retained document but the canonical one states the contract itself.

    The per-document counterpart of the tree-wide count above: that assertion
    establishes there is one body, this one establishes that the population is
    reaching the contract by reference rather than by carrying it.
    """
    restating = [
        document
        for document in DERIVATION.widened
        if document != derivation.CANONICAL_STANDARD and document in BODY_SWEEP.documents
    ]
    assert restating == [], (
        f'{len(restating)} of {DERIVATION.population_size} retained document(s) state the '
        f'contract inline instead of referencing it: {restating}.'
    )

    unreferenced = [
        document
        for document in DERIVATION.widened
        if document != derivation.CANONICAL_STANDARD
        and not derivation.references_canonical(
            (derivation.PROJECT_ROOT / document).read_text(encoding='utf-8')
        )
    ]
    assert unreferenced == [], (
        f'{len(unreferenced)} of {DERIVATION.population_size} retained document(s) are classified '
        f'covered but name no reference to {derivation.CANONICAL_STANDARD}: {unreferenced}.'
    )


def test_the_published_body_count_is_the_count_actually_swept():
    """The header's body count is read off the same sweep the assertions use.

    A second sweep for the header could report a healthy ``1`` for assertions
    taken over a different one — the exact failure the published number exists to
    make visible.
    """
    assert f'{BODY_SWEEP.occurrences} convention' in GUARD_POPULATION_LABEL, (
        f'the published label {GUARD_POPULATION_LABEL!r} does not carry the swept occurrence '
        f'count ({BODY_SWEEP.occurrences}), so a passing run would not report it.'
    )
    assert f'{BODY_SWEEP.coverage.files_scanned} swept' in GUARD_POPULATION_LABEL, (
        f'the published label {GUARD_POPULATION_LABEL!r} does not carry the swept population '
        f'({BODY_SWEEP.coverage.files_scanned}), so the occurrence count is published without '
        'the tree it was taken over.'
    )


def test_the_three_classes_partition_the_population():
    """The classes are disjoint and total, so an empty class is not an accounting artefact.

    Without this, a classifier that dropped documents on the floor would report
    two empty classes and a shrunken population while every assertion above
    passed.
    """
    total = len(DERIVATION.widened) + len(DERIVATION.narrow) + len(DERIVATION.none)
    assert total == DERIVATION.population_size, (
        f'the three class sizes sum to {total} but the population is '
        f'{DERIVATION.population_size} — a retained document was classified into no class.'
    )
    assert len(set(DERIVATION.widened) | set(DERIVATION.narrow) | set(DERIVATION.none)) == total, (
        'a document appears in more than one class, so the classes are not disjoint and the '
        'empty-class assertions above do not mean what they say.'
    )


def test_the_published_size_is_the_size_actually_swept():
    """The header number is read off the same derivation the assertions use.

    A second derivation for the header could report a healthy number for a sweep
    that used a different, smaller one — which is the exact failure the published
    size exists to make visible.
    """
    assert GUARD_POPULATION_SIZE == DERIVATION.population_size
    assert GUARD_POPULATION_SIZE == len(DERIVATION.widened), (
        f'the published population ({GUARD_POPULATION_SIZE}) is not entirely widened — '
        f'{len(DERIVATION.narrow)} narrow, {len(DERIVATION.none)} none. The header would report '
        'a covered population larger than the one actually carrying the convention.'
    )
