#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the phase-4-plan mechanical Q-Gate's CLOSURE checks."""


from __future__ import annotations

from fnmatch import fnmatch

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


def test_unexpandable_glob_is_reported_not_silently_zero():
    """An absolute pattern is an UNMEASURED scope, never an empty one."""
    deliverable = _deliverable(1, survey=['/etc/*.conf'])

    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert [g['kind'] for g in gaps] == ['unexpandable_glob']
    assert population['globs_unexpandable'] == 1
    assert population['globs_expanded'] == 0
    assert population['population_complete'] is False


def test_a_home_relative_glob_is_unmeasured_not_empty():
    """``~/…`` raises NOTHING and matches nothing — the silent half of the guard.

    An absolute pattern raises inside ``Path.glob`` and is caught either way, so
    guarding it is a statement of intent. ``~`` is different: pathlib treats it
    as an ordinary directory name, so the expansion succeeds, returns zero
    matches, and would be reported as a measured-empty scope. Only the explicit
    guard separates that from a pattern that genuinely matches nothing.
    """
    assert list(PROJECT_ROOT.glob('~/x/*.py')) == [], 'precondition: pathlib does not raise here'

    expansion = expand_declared_glob('~/x/*.py', PROJECT_ROOT)

    assert expansion.expandable is False
    _gaps, population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=['~/x/*.py'])], PROJECT_ROOT
    )
    assert population['globs_unexpandable'] == 1
    assert population['population_complete'] is False
