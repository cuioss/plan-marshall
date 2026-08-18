#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the phase-4-plan mechanical Q-Gate's CLOSURE checks.

Existence and closure are different questions. Every fixture here declares
paths that RESOLVE on disk, so the pre-existing ``files_exist`` check passes on
each of them; what the closure checks add is whether the declared SET is
complete. A fixture whose paths all exist and whose set is still incomplete is
the precise shape these checks were written for, and the shape no other check
in the mechanical pass can see.
"""

from __future__ import annotations

import json
from argparse import Namespace
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from conftest import PROJECT_ROOT, load_script_module

_closure = load_script_module('plan-marshall', 'manage-tasks', '_qgate_closure.py', '_qgate_closure')
_qgate = load_script_module(
    'plan-marshall', 'manage-tasks', '_cmd_qgate_mechanical.py', '_cmd_qgate_mechanical_closure'
)

check_declared_set_closure = _closure.check_declared_set_closure
check_declared_scope_reconciliation = _closure.check_declared_scope_reconciliation
compute_projection_gaps = _closure.compute_projection_gaps
compute_referrer_gaps = _closure.compute_referrer_gaps
expand_declared_glob = _closure.expand_declared_glob
declared_paths = _closure.declared_paths
normalize_declared_path = _closure.normalize_declared_path
cmd_qgate_mechanical = _qgate.cmd_qgate_mechanical

#: Two real repository files. Using real paths keeps ``files_exist`` green in
#: the end-to-end cases, so a closure finding can never be confused with an
#: existence finding.
_REAL_A = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
_REAL_B = 'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_qgate_closure.py'

#: A glob whose expansion is stable and small, used for the claim-vs-index
#: cases. Its enumeration is re-derived from the tree at assert time rather
#: than hard-coded, so the test cannot go stale when a file is added.
_STANDARDS_GLOB = 'marketplace/bundles/plan-marshall/skills/manage-tasks/standards/*.md'


def _deliverable(
    number: int,
    *,
    title: str = 'D',
    affected: list[str] | None = None,
    survey: list[str] | None = None,
    mutate: list[str] | None = None,
) -> dict[str, Any]:
    """Build a deliverable record in the shape ``extract_deliverables`` returns."""
    return {
        'number': number,
        'title': title,
        'affected_files': [{'path': p, 'intent': 'write-replace'} for p in (affected or [])],
        'survey_scope': [{'path': p, 'intent': 'read'} for p in (survey or [])],
        'mutation_scope': [{'path': p, 'intent': None} for p in (mutate or [])],
    }


def _task(
    number: int,
    deliverable: int,
    targets: list[str],
    *,
    profile: str = 'implementation',
    title: str = 'T',
) -> dict[str, Any]:
    return {
        'number': number,
        'title': title,
        'profile': profile,
        'deliverable': deliverable,
        'steps': [
            {'number': i + 1, 'target': t, 'intent': 'write-replace'}
            for i, t in enumerate(targets)
        ],
    }


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
    expected_hits = sorted(
        p.relative_to(PROJECT_ROOT).as_posix() for p in PROJECT_ROOT.glob(_STANDARDS_GLOB)
    )
    assert expected_hits, 'positive-population guard: the glob must match something'
    deliverable = _deliverable(1, survey=[_STANDARDS_GLOB], mutate=[_REAL_A])

    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert population['globs_declared'] == 1
    assert population['globs_expanded'] == 1
    assert population['matches_enumerated'] == len(expected_hits)
    assert [g['kind'] for g in gaps] == ['claim_vs_index']
    for hit in expected_hits:
        assert hit in gaps[0]['detail'], hit


def test_declared_glob_fully_enumerated_is_closed():
    """When every match is also enumerated, the claim and the index agree."""
    expected_hits = sorted(
        p.relative_to(PROJECT_ROOT).as_posix() for p in PROJECT_ROOT.glob(_STANDARDS_GLOB)
    )
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


def test_expand_declared_glob_reports_expandability_separately_from_emptiness():
    """A pattern matching nothing and a pattern that cannot expand differ."""
    empty_matches, empty_truncated, empty_expandable = expand_declared_glob(
        'marketplace/bundles/plan-marshall/skills/manage-tasks/no-such-dir/*.md', PROJECT_ROOT
    )
    abs_matches, _abs_truncated, abs_expandable = expand_declared_glob('/etc/*.conf', PROJECT_ROOT)

    assert empty_matches == [] and empty_expandable is True and empty_truncated is False
    assert abs_matches == [] and abs_expandable is False


# =============================================================================
# Population — the positive-population guard (D3)
# =============================================================================


def test_population_is_incomplete_when_a_task_names_a_missing_deliverable():
    """``detector_population ⊇ fix_set_population`` fails loudly, not silently."""
    deliverables = [_deliverable(1, affected=[_REAL_A])]
    tasks = [_task(1, 1, [_REAL_A]), _task(2, 99, [_REAL_B])]

    _gaps, population = check_declared_set_closure(tasks, deliverables)

    assert population['population_complete'] is False
    assert population['unmapped_tasks'] == [2]


def test_population_reports_what_was_actually_scanned():
    """A non-empty scanned population is asserted positively, not inferred."""
    deliverables = [_deliverable(1, affected=[_REAL_A], survey=[_REAL_B])]
    tasks = [_task(1, 1, [_REAL_A, _REAL_B])]

    _gaps, population = check_declared_set_closure(tasks, deliverables)

    assert population['deliverables_scanned'] == 1
    assert population['declared_paths_scanned'] == 2
    assert population['tasks_scanned'] == 1
    assert population['step_targets_scanned'] == 2
    assert population['population_complete'] is True


def test_verification_tasks_are_excluded_from_the_scanned_population():
    """A verification task's steps are commands, not paths, so it is skipped."""
    deliverables = [_deliverable(1, affected=[_REAL_A])]
    tasks = [_task(1, 1, [_REAL_A]), _task(2, 1, ['./pw verify'], profile='verification')]

    gaps, population = check_declared_set_closure(tasks, deliverables)

    assert gaps == []
    assert population['tasks_scanned'] == 1


# =============================================================================
# End-to-end through the mechanical Q-Gate
# =============================================================================


def _write_task_file(task_dir: Path, task: dict[str, Any]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    record = {
        'number': task['number'],
        'title': task['title'],
        'status': 'pending',
        'profile': task['profile'],
        'domain': 'plan-marshall-plugin-dev',
        'origin': 'plan',
        'deliverable': task['deliverable'],
        'depends_on': [],
        'skills': ['plan-marshall:manage-tasks'],
        'description': '',
        'steps': [{**s, 'status': 'pending'} for s in task['steps']],
        'verification': {'commands': [], 'criteria': '', 'manual': False},
    }
    (task_dir / f'TASK-{task["number"]:03d}.json').write_text(
        json.dumps(record, indent=2), encoding='utf-8'
    )


def _write_outline(plan_dir: Path, body: str) -> None:
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution Outline\n\n## Deliverables\n\n' + body, encoding='utf-8'
    )


def test_qgate_reports_closure_gap_while_files_exist_stays_clean(plan_context):
    """Every declared path resolves, and the set is still incomplete.

    This is the fixture the plan names: existence passes, closure does not. If
    ``files_exist`` reported anything here the test would be measuring the wrong
    check, so its zero is asserted alongside the closure finding.
    """
    plan_dir = plan_context.plan_dir_for('closure-e2e')
    _write_outline(
        plan_dir,
        f'### 1. Widen the sweep\n\n'
        f'**Affected files:**\n- `{_REAL_A}` (write-replace)\n- `{_REAL_B}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-e2e', no_emit=True))

    assert result['checks']['files_exist']['failed'] == 0
    assert result['checks']['declared_set_closure']['failed'] == 1
    assert result['population']['declared_set_closure']['population_complete'] is True


def test_qgate_reads_the_survey_scope_pair_from_the_outline(plan_context):
    """A survey-scope deliverable's declaration reaches the mechanical Q-Gate.

    Authored per ``outline-workflow-detail.md`` — the two disjoint fields and no
    ``Affected files:`` list. The mutation-scope path is unprojected, so the
    closure fires; before the parser read these headings the deliverable's
    declared surface was empty and nothing could fire at all.
    """
    plan_dir = plan_context.plan_dir_for('closure-survey')
    _write_outline(
        plan_dir,
        f'### 1. Survey the standards and classify each\n\n'
        f'**Files to survey:**\n- `{_REAL_A}`\n\n'
        f'**Files expected to mutate:**\n- `{_REAL_B}`\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-survey', no_emit=True))

    population = result['population']['declared_set_closure']
    assert population['declared_paths_scanned'] == 2, 'the survey pair must be scanned'
    assert result['checks']['declared_set_closure']['failed'] == 1


def test_closure_check_runs_under_the_surgical_scope_bypass_shape(plan_context):
    """ADVERSARIAL: a plan shaped exactly like the Step 8b bypass is still checked.

    phase-4-plan's B2 predicate — ``scope_estimate == surgical`` with at most
    two declared affected files — suppresses the DISPATCHED q-gate-validation.
    This fixture satisfies that predicate exactly, and asserts the closure check
    still runs and still fires, because it lives in Step 8, which has no bypass.
    A closure claim is a hint; it may never be a licence to skip the check that
    would test it.
    """
    plan_dir = plan_context.plan_dir_for('closure-bypass')
    (plan_dir / 'references.json').write_text(
        json.dumps({'scope_estimate': 'surgical'}), encoding='utf-8'
    )
    _write_outline(
        plan_dir,
        f'### 1. Surgical fix\n\n'
        f'**Metadata:**\n- change_type: bug_fix\n\n'
        f'**Affected files:**\n- `{_REAL_A}` (write-replace)\n- `{_REAL_B}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-bypass', no_emit=True))

    declared = sum(
        1
        for line in (plan_dir / 'solution_outline.md').read_text(encoding='utf-8').splitlines()
        if line.startswith('- `')
    )
    assert declared <= 2, 'precondition: the fixture must satisfy the bypass predicate'
    assert result['checks']['declared_set_closure']['failed'] == 1
