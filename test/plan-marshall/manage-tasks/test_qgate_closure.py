#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the phase-4-plan mechanical Q-Gate's CLOSURE checks."""


from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

import pytest
from _qgate_closure_fixtures import (
    _REAL_A,
    _REAL_B,
    _STANDARDS_GLOB,
    _deliverable,
    _independent_expansion,
    _task,
    check_declared_scope_reconciliation,
    compute_projection_gaps,
    compute_referrer_gaps,
    declared_paths,
    expand_declared_glob,
    normalize_declared_path,
)

from conftest import PROJECT_ROOT

# =============================================================================
# Path normalization — the comparison's own precondition
# =============================================================================


def test_normalize_strips_leading_dot_slash_and_trailing_separator():
    """``./a/b.py`` and ``a/b.py/`` name the same file as ``a/b.py``."""
    assert normalize_declared_path('./a/b.py') == 'a/b.py'
    assert normalize_declared_path('a/b.py/') == 'a/b.py'
    assert normalize_declared_path('  ./a/b.py  ') == 'a/b.py'


def test_normalize_preserves_a_leading_dot_directory():
    """A dotfile tree keeps its leading dot — only ``./`` prefixes are stripped."""
    assert normalize_declared_path('.claude/skills/x/SKILL.md') == '.claude/skills/x/SKILL.md'


# =============================================================================
# Projection closure — declared write path that no task targets
# =============================================================================


def test_projection_gap_when_a_declared_write_is_never_targeted():
    """A declared write path no step names is reported, even though it exists."""
    deliverable = _deliverable(1, affected=[_REAL_A, _REAL_B])
    tasks = [_task(1, 1, [_REAL_A])]

    gaps = compute_projection_gaps(deliverable, tasks)

    assert gaps == [_REAL_B], 'the unprojected declared write must be named, positively'


def test_projection_closed_when_every_declared_write_is_targeted():
    """A fully projected write-set yields no gap."""
    deliverable = _deliverable(1, affected=[_REAL_A, _REAL_B])
    tasks = [_task(1, 1, [_REAL_A]), _task(2, 1, [_REAL_B])]

    assert compute_projection_gaps(deliverable, tasks) == []


def test_projection_ignores_read_intent_declarations():
    """A ``read`` declaration is not a write, so it is never owed a step."""
    deliverable = {
        'number': 1,
        'title': 'D',
        'affected_files': [
            {'path': _REAL_A, 'intent': 'write-replace'},
            {'path': _REAL_B, 'intent': 'read'},
        ],
        'survey_scope': [],
        'mutation_scope': [],
    }

    assert compute_projection_gaps(deliverable, [_task(1, 1, [_REAL_A])]) == []


def test_projection_covers_the_mutation_scope_of_a_survey_deliverable():
    """``Files expected to mutate:`` is a write-set member and is owed a step.

    This is the survey-scope deliverable authored exactly as the outline
    standard mandates — no ``Affected files:`` list at all. Before the write-set
    unioned the mutation scope, this deliverable's write-set was EMPTY, so the
    projection had nothing to be incomplete about and the gap was unreportable
    by construction.
    """
    deliverable = _deliverable(1, survey=[_REAL_A], mutate=[_REAL_B])

    gaps = compute_projection_gaps(deliverable, [_task(1, 1, [])])

    assert gaps == [_REAL_B]


# =============================================================================
# Referrer closure — step target the deliverable never declared
# =============================================================================

def test_projection_leaves_a_declared_glob_to_the_reconciliation_check():
    """A declared glob in the write-set is not reported as an unprojected write.

    A pattern cannot be a step target, so reporting it as "no task targets this"
    would emit a finding on every survey-scope deliverable that declares a
    pattern — noise the author cannot act on. The claim-versus-index check owns
    patterns; the projection check owns literal paths.
    """
    deliverable = _deliverable(1, mutate=[_STANDARDS_GLOB, _REAL_A])

    gaps = compute_projection_gaps(deliverable, [_task(1, 1, [_REAL_A])])

    assert gaps == []


# =============================================================================
# Referrer closure — step target the deliverable never declared
# =============================================================================


def test_referrer_gap_when_a_step_targets_an_undeclared_path():
    """A step target absent from every declared heading is reported."""
    deliverable = _deliverable(1, affected=[_REAL_A])

    gaps = compute_referrer_gaps(_task(1, 1, [_REAL_B]), declared_paths(deliverable))

    assert gaps == [_REAL_B]


def test_referrer_accepts_a_target_declared_under_files_to_survey():
    """The survey pool is part of the declared surface, so a read step is covered."""
    deliverable = _deliverable(1, survey=[_REAL_B], mutate=[_REAL_A])

    assert compute_referrer_gaps(_task(1, 1, [_REAL_B]), declared_paths(deliverable)) == []


def test_referrer_reports_a_target_covered_only_by_a_glob():
    """A step target a declared PATTERN would match is still reported.

    The step is where a pattern must have become a concrete enumerated path.
    Accepting glob coverage here would let ``{declared scope wide, write-set
    narrow}`` pass as closure — the exact pair the reconciliation check exists
    to surface.

    The fixture pins the precondition it depends on: the pattern really does
    match the target under ``fnmatch``, so a referrer closure that matched
    patterns would fall silent here. Without that assertion the test would pass
    for the uninteresting reason that the glob was irrelevant to the target.
    """
    pattern = 'marketplace/bundles/plan-marshall/skills/*/SKILL.md'
    assert fnmatch(_REAL_A, pattern), 'precondition: the declared glob matches the step target'
    deliverable = _deliverable(1, survey=[pattern])

    gaps = compute_referrer_gaps(_task(1, 1, [_REAL_A]), declared_paths(deliverable))

    assert gaps == [_REAL_A]


# =============================================================================
# Claim-versus-index closure — a declared glob against the enumerated list
# =============================================================================


def test_declared_glob_wider_than_the_enumeration_is_reported():
    """A declared glob matching files the deliverable never enumerates fires.

    The expected hit set is re-derived from the tree at assert time rather than
    written as a literal, so the assertion cannot drift from what the glob
    actually matches.
    """
    expected_hits = _independent_expansion(_STANDARDS_GLOB)
    assert expected_hits, 'positive-population guard: the glob must match something'
    deliverable = _deliverable(1, survey=[_STANDARDS_GLOB], mutate=[_REAL_A])

    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert population['globs_declared'] == 1
    assert population['globs_expanded'] == 1
    assert population['matches_enumerated'] == len(expected_hits)
    assert [g['kind'] for g in gaps] == ['claim_vs_index']
    # Every KNOWN hit is named — the positive half of the population guard, which
    # a cardinality assertion alone cannot express.
    for hit in expected_hits:
        assert hit in gaps[0]['detail'], hit


def test_declared_glob_fully_enumerated_is_closed():
    """When every match is also enumerated, the claim and the index agree."""
    expected_hits = _independent_expansion(_STANDARDS_GLOB)
    assert expected_hits, 'positive-population guard: the glob must match something'
    deliverable = _deliverable(1, survey=[_STANDARDS_GLOB, *expected_hits])

    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert gaps == []
    assert population['globs_expanded'] == 1
    assert population['matches_enumerated'] == len(expected_hits)
    assert population['population_complete'] is True


# =============================================================================
# End-to-end through the mechanical Q-Gate
# =============================================================================

class EscapePreconditionUnmet(Exception):
    """The escaping-glob fixture could not be constructed on this platform.

    Raised instead of failing an ``assert`` so an unmet precondition surfaces as
    a COULD-NOT-LOOK — a `pytest.skip` naming which half was missing — rather
    than as an assertion error indistinguishable from the subject failing. The
    distinction is the whole point of the test it guards: a body that never ran
    must not be reported in the vocabulary of one that ran and disagreed.
    """


def _escape_target() -> tuple[str, Path]:
    """Return an ``(escaping_glob, resolved_target)`` pair, or refuse to guess.

    ⛔ **The number of ``..`` segments is DERIVED from ``PROJECT_ROOT``, never
    hard-coded.** How deep the checkout sits below ``/`` is a property of the
    environment, not of the code under test: a developer checkout at
    ``/home/user/plan-marshall`` is three levels down, a GitHub Actions checkout
    at ``/home/runner/work/plan-marshall/plan-marshall`` is five. An earlier
    version wrote ``../../../etc`` and asserted it resolved to ``/etc``, with a
    docstring claiming ``PROJECT_ROOT`` "is three levels below /". That was true
    only where it was written: CI resolved the same pattern to
    ``/home/runner/etc``, the precondition failed, and the suite was green on one
    machine and red on every other. Deriving the depth makes the precondition
    hold wherever the checkout lives.

    ⛔ **Both sides of the escape comparison are RESOLVED.** ``Path('/etc')`` is
    a symlink to ``/private/etc`` on macOS, so comparing a ``resolve()``d
    left-hand side against the unresolved literal can never hold there. The test
    body — which verifies that an escaping glob is reported UNMEASURED rather
    than empty — therefore never executed on macOS while the test still appeared
    in the suite: a test whose subject is "unmeasured must not render as clean"
    that was itself unmeasured.

    Raises:
        EscapePreconditionUnmet: when the constructed path does not leave the
            repository, or leaves it but finds nothing there — naming which half
            was missing so the skip reason is actionable.
    """
    root = PROJECT_ROOT.resolve()
    # parts[0] is '/', so the remaining count is the depth to climb to reach it.
    up = '/'.join(['..'] * (len(root.parts) - 1))
    escape = f'{up}/etc/*.conf'
    # The climb depth was derived from the RESOLVED root, so it is applied to the
    # resolved root too — an unresolved ``PROJECT_ROOT`` carrying a symlinked
    # ancestor can have a different part count, which would climb the wrong
    # number of levels.
    outside = (root / f'{up}/etc').resolve()

    # Resolve BOTH sides: on macOS /etc is a symlink to /private/etc, and only a
    # resolved-vs-resolved comparison holds on every platform.
    if outside != Path('/etc').resolve():
        raise EscapePreconditionUnmet(
            f'the constructed pattern does not leave the repo: {outside} != '
            f'{Path("/etc").resolve()} (project root {root})'
        )
    if not list(outside.glob('*.conf')):
        raise EscapePreconditionUnmet(
            f'the escape target {outside} exists but is unpopulated, so an empty '
            f'result would prove nothing'
        )
    return escape, outside


def test_the_escape_precondition_is_constructible_on_this_platform():
    """The precondition itself is the subject here, so its failure is visible.

    Without this, an unmet precondition would only ever surface as a skip on the
    test below — and a skipped test is easy to read as "fine". This one FAILS,
    naming the half that was missing, so the platform gap cannot go unnoticed the
    way the macOS symlink mismatch did.
    """
    escape, outside = _escape_target()

    assert escape.endswith('/etc/*.conf')
    assert outside == Path('/etc').resolve()


def test_a_declared_glob_escaping_the_repo_is_unmeasured_not_empty():
    """An escaping pattern is rejected, and the escape target really exists.

    Left unnormalised, ``Path.glob`` walks out of the repository and returns
    nothing, so a scope nothing examined reports a clean zero — the very defect
    this module reports on outlines, committed by the module itself.

    The precondition is constructed by :func:`_escape_target`, which refuses
    rather than guesses; an unmet one becomes a skip naming the missing half, so
    a body that could not run is distinguishable from one that ran and passed.
    """
    try:
        escape, _outside = _escape_target()
    except EscapePreconditionUnmet as unmet:  # pragma: no cover - platform-dependent
        pytest.skip(f'could not look: {unmet}')

    expansion = expand_declared_glob(escape, PROJECT_ROOT)
    assert expansion.expandable is False

    deliverable = _deliverable(1, survey=[escape])
    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert [g['kind'] for g in gaps] == ['unexpandable_glob']
    assert population['globs_unexpandable'] == 1
    assert population['population_complete'] is False


def test_an_in_repo_glob_is_expandable_and_completes_its_population():
    """The matched negative control the escaping case lacked.

    Its assertions are the exact opposites of the test above, over the SAME two
    helpers. Without it, ``expandable is False`` / ``population_complete is
    False`` would be satisfied by an expander that rejects every pattern — which
    is indistinguishable from the guard working, and is precisely the shape a
    never-executed body leaves behind.

    The overlap with ``test_declared_glob_fully_enumerated_is_closed`` is
    deliberate rather than redundant: that test establishes the closure property
    on its own terms, while this one exists to be READ against the escaping case
    directly above it — the control half of a pair is only a control if it sits
    beside what it controls for.
    """
    expansion = expand_declared_glob(_STANDARDS_GLOB, PROJECT_ROOT)
    assert expansion.expandable is True

    matches = _independent_expansion(_STANDARDS_GLOB)
    assert matches, 'positive-population guard: the in-repo glob must match something'
    deliverable = _deliverable(1, survey=[_STANDARDS_GLOB, *matches])

    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert [g['kind'] for g in gaps] == []
    assert population['globs_unexpandable'] == 0
    assert population['population_complete'] is True
