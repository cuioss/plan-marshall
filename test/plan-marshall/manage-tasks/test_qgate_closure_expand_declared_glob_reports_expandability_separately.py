#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the phase-4-plan mechanical Q-Gate's CLOSURE checks.

Existence and closure are different questions, and the end-to-end fixtures are
built so that difference is actually exercised rather than merely asserted.

⛔ ``files_exist`` applies an INTENT-DEPENDENT predicate: it skips
``write-replace`` outright, requires existence for ``read`` and ``delete``, and
inverts for ``write-new``. A fixture whose steps all carry ``write-replace``
therefore reports ``files_exist: 0`` no matter what its paths are — including
paths that do not exist — so asserting that zero would prove nothing about
existence. The end-to-end fixtures below use ``read`` intent on their steps and
real repository files, which makes the existence check actually run and actually
pass; ``test_files_exist_zero_is_load_bearing_not_vacuous`` pins that by
replacing the paths with absent ones and asserting ``files_exist`` goes
non-zero.
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from _qgate_closure_fixtures import (
    _REAL_A,
    _REAL_B,
    _STANDARDS_GLOB,
    _deliverable,
    _task,
    _write_outline,
    _write_task_file,
    check_declared_scope_reconciliation,
    check_declared_set_closure,
    cmd_qgate_mechanical,
    expand_declared_glob,
)

from conftest import PROJECT_ROOT


def test_expand_declared_glob_reports_expandability_separately_from_emptiness():
    """A pattern matching nothing and a pattern that cannot expand differ."""
    empty = expand_declared_glob(
        'marketplace/bundles/plan-marshall/skills/manage-tasks/no-such-dir/*.md', PROJECT_ROOT
    )
    absolute = expand_declared_glob('/etc/*.conf', PROJECT_ROOT)

    assert empty.matches == [] and empty.expandable is True and empty.truncated is False
    assert empty.directories_matched == 0
    assert absolute.matches == [] and absolute.expandable is False


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


def test_qgate_reports_closure_gap_while_files_exist_stays_clean(plan_context):
    """Every declared path resolves, and the set is still incomplete.

    This is the fixture the plan names: existence passes, closure does not. The
    steps carry ``read`` intent, so ``files_exist`` runs its existence predicate
    over real files and passes on the merits — its zero is a measured verdict,
    not the skip ``write-replace`` would have produced. The companion test below
    proves that zero can move.
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


def test_files_exist_zero_is_load_bearing_not_vacuous(plan_context):
    """The end-to-end fixture's ``files_exist: 0`` moves when the paths vanish.

    Without this, ``files_exist: 0`` could not be told from the skip that
    ``write-replace`` intent produces, and the "existence passes, closure does
    not" claim would be unearned. The SAME shape as the fixture above, with the
    declared and targeted paths swapped for absent ones: the existence check
    must now report, which is what makes its zero elsewhere a measurement.
    """
    plan_dir = plan_context.plan_dir_for('closure-files-exist-control')
    absent_a, absent_b = 'src/ABSENT-A.java', 'src/ABSENT-B.java'
    assert not (PROJECT_ROOT / absent_a).exists(), 'precondition: the control path must be absent'
    _write_outline(
        plan_dir,
        f'### 1. Widen the sweep\n\n'
        f'**Affected files:**\n- `{absent_a}` (write-replace)\n- `{absent_b}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [absent_a]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-files-exist-control', no_emit=True))

    assert result['checks']['files_exist']['failed'] == 1
    assert result['checks']['declared_set_closure']['failed'] == 1


def test_a_declared_glob_escaping_the_repo_is_unmeasured_not_empty():
    """An escaping pattern is rejected, and the escape target really exists.

    The precondition is asserted rather than assumed: the pattern must resolve
    to a directory that is BOTH outside the repository and populated, or the
    test would pass for the uninteresting reason that there was nothing out
    there to find either way.

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

    Left unnormalised, ``Path.glob`` walks out of the repository and returns
    nothing, so a scope nothing examined reports a clean zero — the very defect
    this module reports on outlines, committed by the module itself.
    """
    # parts[0] is '/', so the remaining count is the depth to climb to reach it.
    up = '/'.join(['..'] * (len(PROJECT_ROOT.resolve().parts) - 1))
    escape = f'{up}/etc/*.conf'
    outside = (PROJECT_ROOT / f'{up}/etc').resolve()
    assert outside == Path('/etc'), 'precondition: the pattern must leave the repo'
    assert list(outside.glob('*.conf')), 'precondition: the escape target must be populated'

    expansion = expand_declared_glob(escape, PROJECT_ROOT)
    assert expansion.expandable is False

    deliverable = _deliverable(1, survey=[escape])
    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert [g['kind'] for g in gaps] == ['unexpandable_glob']
    assert population['globs_unexpandable'] == 1
    assert population['population_complete'] is False


def test_an_in_repo_dotdot_glob_expands_to_canonical_paths():
    """``doc/../marketplace/…`` and the plain path name the same file.

    Without normalisation the expansion returned the literal ``doc/../…``
    spelling, which compares unequal to the canonical declaration — so the check
    manufactured a claim_vs_index finding against a path the deliverable HAD
    enumerated.
    """
    canonical = sorted(
        p.relative_to(PROJECT_ROOT).as_posix() for p in PROJECT_ROOT.glob(_STANDARDS_GLOB)
    )
    assert canonical, 'positive-population guard: the glob must match something'
    detoured = 'doc/../' + _STANDARDS_GLOB

    expansion = expand_declared_glob(detoured, PROJECT_ROOT)

    assert expansion.matches == canonical
    gaps, _population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=[detoured, *canonical])], PROJECT_ROOT
    )
    assert gaps == []
