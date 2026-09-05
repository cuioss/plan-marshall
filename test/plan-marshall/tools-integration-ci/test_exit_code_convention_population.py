#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
"""Population guard: every executor-invoking skill document carries the widened convention.

The guard re-runs the D1 derivation over the live tree rather than reading a
committed list, so a document added tomorrow that invokes a non-``manage-*``
script fails here on arrival without anyone remembering to list it.

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

``phase-6-finalize/test_review_merge_invocation_contract.py`` already pins this
convention, and the two do not overlap in what they establish:

* That guard sweeps **two skills** — ``phase-6-finalize`` and
  ``automatic-review`` — and pins, per obligated document, the exact literal text
  of the exit-0-non-success disposition clause, with an enumerated exemption list.
* This guard sweeps **every bundle's skill documents** and asserts only that a
  convention of the widened *kind* is present. It is wider in population and
  weaker per document, by design.

Neither contradicts the other: both demand the widened form and reject the
``manage-*``-scoped one. The surface that remains covered ONLY by the finalize
guard, and is deliberately not duplicated here, is the **exact wording** of the
disposition clause — this module classifies by the marker phrases that make a
convention widened, not by a byte-for-byte match of the clause text. A document
outside the finalize pool therefore has its convention's *presence and scope*
guarded here, but not its precise phrasing.
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

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. A row naming this module lives in that file's
#: ``_ROUTING_GUARD_MODULES``; the roster guard fails if the two drift apart.
GUARD_POPULATION_LABEL = 'executor-invoking skill docs'
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
        'narrow form outright rather than adding the widened one alongside it.'
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
