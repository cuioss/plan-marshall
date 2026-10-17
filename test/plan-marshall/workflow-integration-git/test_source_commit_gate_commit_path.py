#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D2 — the finalize commit gate reads the plan's REAL phase and manifest.

The gate predicate (``evaluate_source_commit_gate``) is driven through the REAL
commit path — the ``git-workflow commit`` verb — against the REAL layout:

* the plan's ``status.json`` is written by ``manage-status`` (its field is
  ``current_phase``, never ``phase``) and lives where the main-anchored plan
  resolution finds it — NOT under ``<worktree>/.plan/local/plans`` and never
  "the first plan found";
* the phase-6 manifest step ids come from the plan's composed ``execution.toon``.

Pinned clauses:

* a finalize-phase source commit with no sanction is refused, exit non-zero;
* a composed-manifest ``--step`` id sanctions the commit; an unknown step does not;
* a runbook-lane worktree (no plan record) passes;
* an unresolvable phase reports ``unknown`` and refuses (fail closed);
* ``--phase`` is not caller-settable on the commit verb.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')
MANAGE_STATUS = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

# Loaded for the pure-predicate pin; ``register=False`` publishes nothing.
git_workflow = load_script_module(
    'plan-marshall',
    'workflow-integration-git',
    'git-workflow.py',
    module_name='git_workflow_commit_path',
    register=False,
)

_PHASES = '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize'


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    subprocess.run(['git', 'init', str(root)], check=True, capture_output=True)
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'baseline.txt').write_text('baseline\n', encoding='utf-8')
    _git(root, 'add', 'baseline.txt')
    _git(root, 'commit', '-m', 'baseline')


def _base_dir(root: Path) -> Path:
    """The ``.plan/local`` base a real plan's state resolves under."""
    return root / '.plan' / 'local'


def _env(root: Path) -> dict[str, str]:
    """Environment overrides that anchor plan-state resolution to *root*."""
    return {'PLAN_BASE_DIR': str(_base_dir(root)), 'PLAN_DIR_NAME': '.plan'}


def _write_plan(root: Path, plan_id: str, *, phase: str = '6-finalize', steps: list[str] | None = None) -> Path:
    """Create a REAL plan whose status is written by ``manage-status``.

    Returns the plan directory (main-anchored). The commit gate's resolution
    honours ``PLAN_BASE_DIR``, so the status lands where the gate looks.
    """
    env = _env(root)
    created = run_script(
        MANAGE_STATUS, 'create', '--plan-id', plan_id, '--title', 't', '--phases', _PHASES, env_overrides=env
    )
    assert created.returncode == 0, f'manage-status create failed: {created.stdout}{created.stderr}'
    payload = parse_toon(created.stdout)
    assert payload.get('status') == 'success', f'manage-status create refused: {payload!r}'
    shifted = run_script(MANAGE_STATUS, 'set-phase', '--plan-id', plan_id, '--phase', phase, env_overrides=env)
    assert shifted.returncode == 0, f'manage-status set-phase failed: {shifted.stdout}{shifted.stderr}'
    plan_dir = _base_dir(root) / 'plans' / plan_id
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    assert status.get('current_phase') == phase, f'manage-status did not persist current_phase: {status!r}'
    if steps is not None:
        (plan_dir / 'execution.toon').write_text(_manifest_toon(plan_id, steps), encoding='utf-8')
    return plan_dir


def _manifest_toon(plan_id: str, steps: list[str]) -> str:
    head = f'manifest_version: 1\nplan_id: {plan_id}\nphase_6:\n  steps[{len(steps)}]:\n'
    return head + ''.join(f'    - {step}\n' for step in steps)


def _worktree(root: Path, plan_id: str) -> Path:
    """The plan worktree path whose basename names the plan (created on disk)."""
    path = _base_dir(root) / 'worktrees' / plan_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stage(root: Path, name: str, content: str = 'x\n') -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    _git(root, 'add', name)


def _commit_count(root: Path) -> int:
    return len([line for line in _git(root, 'log', '--oneline').stdout.splitlines() if line.strip()])


def _run_commit(root: Path, worktree: Path, *extra: str) -> tuple[dict, int]:
    result = run_script(
        SCRIPT_PATH,
        'commit',
        '--project-dir',
        str(worktree),
        '--message',
        'fix: a thing',
        *extra,
        env_overrides=_env(root),
    )
    return parse_toon(result.stdout), result.returncode


# =============================================================================
# Refusal and sanctions
# =============================================================================


def test_finalize_source_commit_refused_through_commit_verb(tmp_path: Path) -> None:
    """(a) + (e): a finalize source commit with no sanction is refused, exit non-zero."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'))

    assert result.get('refused') is True, f'expected a refusal payload, got {result!r}'
    assert result['reason'] == 'no_sanction'
    assert result['phase'] == '6-finalize'
    assert code != 0, 'a refusal must exit non-zero, not report status: success, allowed: false'
    assert _commit_count(tmp_path) == 1, 'the refused commit must not have been created'


def test_composed_manifest_step_sanctions_the_commit(tmp_path: Path) -> None:
    """A step id of the plan's composed phase-6 manifest sanctions the commit."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate', 'push'])
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'), '--step', 'pre-push-quality-gate')

    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'settle_band_step'
    assert code == 0
    assert _commit_count(tmp_path) == 2, 'the sanctioned commit must have been created'


def test_unknown_step_id_is_refused(tmp_path: Path) -> None:
    """``--step not-a-step`` sanctions nothing — only a composed-manifest id does."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'), '--step', 'not-a-step')

    assert result.get('refused') is True, f'expected a refusal payload, got {result!r}'
    assert result['reason'] == 'no_sanction'
    assert code != 0
    assert _commit_count(tmp_path) == 1


def test_review_rubric_section6_record_sanctions_the_commit(tmp_path: Path) -> None:
    """A review-rubric section-6 inline-correction record still sanctions a finalize commit."""
    _init_repo(tmp_path)
    plan_dir = _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    findings = plan_dir / 'artifacts' / 'findings'
    findings.mkdir(parents=True, exist_ok=True)
    (findings / 'qgate-6-finalize.jsonl').write_text(
        json.dumps(
            {
                'title': 'Code review finding per review-rubric section 6',
                'detail': 'inline-correction applied for the section-6 loop-back',
            }
        )
        + '\n',
        encoding='utf-8',
    )
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'))

    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'section6_record'
    assert code == 0


def test_plan_only_commit_passes(tmp_path: Path) -> None:
    """A ``.plan/``-only commit passes with no sanction, even in a finalize plan."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=[])
    _stage(tmp_path, '.plan/local/plans/PLAN-A/notes.txt', 'plan state\n')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'))

    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'plan_only'
    assert code == 0


def test_non_finalize_plan_commit_passes_through_the_verb(tmp_path: Path) -> None:
    """Outside 6-finalize the verb commits a source change untouched."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=['pre-push-quality-gate'])
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'))

    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'not_finalize'
    assert code == 0


def test_runbook_lane_worktree_without_plan_record_passes(tmp_path: Path) -> None:
    """A runbook-lane worktree (no plan status) is identified and passes."""
    _init_repo(tmp_path)
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'lb-99-runbook-lane'))

    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'not_finalize'
    assert code == 0
    assert _commit_count(tmp_path) == 2


def test_unresolvable_phase_reports_unknown_and_refuses(tmp_path: Path) -> None:
    """A plan whose ``current_phase`` cannot be read reports ``unknown`` and refuses."""
    _init_repo(tmp_path)
    plan_dir = _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    # Simulate an unusable record: the real path, but no readable ``current_phase``.
    (plan_dir / 'status.json').write_text(json.dumps({'plan_id': 'plan-a'}), encoding='utf-8')
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'))

    assert result.get('refused') is True, f'expected a refusal payload, got {result!r}'
    assert result['phase'] == 'unknown'
    assert result['reason'] == 'no_sanction'
    assert code != 0


def test_commit_verb_rejects_a_caller_supplied_phase(tmp_path: Path) -> None:
    """``--phase`` is not caller-settable on the commit verb."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    _stage(tmp_path, 'src/a.py')

    result = run_script(
        SCRIPT_PATH,
        'commit',
        '--project-dir',
        str(_worktree(tmp_path, 'plan-a')),
        '--phase',
        '5-execute',
        '--message',
        'fix: a thing',
        env_overrides=_env(tmp_path),
    )

    assert result.returncode != 0, f'--phase must not be accepted: {result.stdout}{result.stderr}'
    assert 'unrecognized arguments' in result.stderr, result.stderr


# =============================================================================
# Pure predicate pins
# =============================================================================


def test_pure_gate_sanctions_a_composed_manifest_step() -> None:
    """The predicate sanctions by a composed-manifest step id, not by any string."""
    verdict = git_workflow.evaluate_source_commit_gate(
        '6-finalize',
        ['src/a.py'],
        [],
        [],
        step='pre-push-quality-gate',
        manifest_steps={'pre-push-quality-gate', 'push'},
    )
    assert verdict['allowed'] is True
    assert verdict['reason'] == 'settle_band_step'


def test_pure_gate_refuses_a_step_outside_the_manifest() -> None:
    """A step not in the composed manifest sanctions nothing."""
    verdict = git_workflow.evaluate_source_commit_gate(
        '6-finalize',
        ['src/a.py'],
        [],
        [],
        step='not-a-step',
        manifest_steps={'pre-push-quality-gate'},
    )
    assert verdict['allowed'] is False
    assert verdict['reason'] == 'no_sanction'


def test_pure_gate_treats_unknown_phase_as_fail_closed() -> None:
    """An ``unknown`` phase refuses a source commit — fail closed, not fail open."""
    verdict = git_workflow.evaluate_source_commit_gate('unknown', ['src/a.py'], [], [])
    assert verdict['allowed'] is False
    assert verdict['reason'] == 'no_sanction'
    assert verdict['phase'] == 'unknown'


def test_pure_gate_passes_when_no_plan_record() -> None:
    """``None`` phase — no plan record at all — passes a source commit."""
    verdict = git_workflow.evaluate_source_commit_gate(None, ['src/a.py'], [], [])
    assert verdict['allowed'] is True
    assert verdict['reason'] == 'not_finalize'


def test_plan_id_from_worktree_path_names_the_plan() -> None:
    """The plan id is the segment the worktree path names (innermost when nested)."""
    assert git_workflow._plan_id_from_worktree_path('/repo/.plan/local/worktrees/plan-a') == 'plan-a'
    assert git_workflow._plan_id_from_worktree_path('/repo/.plan/local/worktrees/plan-a/sub') == 'plan-a'
    nested = '/outer/.plan/local/worktrees/outer/.plan/local/worktrees/plan-b'
    assert git_workflow._plan_id_from_worktree_path(nested) == 'plan-b'
    assert git_workflow._plan_id_from_worktree_path('/repo/src') is None
