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
MANAGE_CHANGE_LEDGER = get_script_path('plan-marshall', 'manage-change-ledger', 'manage-change-ledger.py')

# Loaded for the pure-predicate pin; ``register=False`` publishes nothing.
git_workflow = load_script_module(
    'plan-marshall',
    'workflow-integration-git',
    'git-workflow.py',
    module_name='git_workflow_commit_path',
    register=False,
)
# The boundary guard whose enumeration the verb's rows must satisfy.
_lifecycle = load_script_module(
    'plan-marshall',
    'manage-status',
    '_cmd_lifecycle.py',
    module_name='lb126_status_lifecycle',
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


def _write_worktree_plan(
    worktree: Path, plan_id: str, *, phase: str = '6-finalize', steps: list[str] | None = None
) -> Path:
    """Create a REAL worktree-resident plan whose status is written by ``manage-status``.

    ``prepare_execute`` moves the plan directory INTO the worktree, so this is the
    layout a real finalize plan has: the record lives under the worktree's own
    ``.plan/local``. ``PLAN_BASE_DIR`` is pointed there so ``manage-status``
    writes it where the gate looks.
    """
    env = {'PLAN_BASE_DIR': str(worktree / '.plan' / 'local'), 'PLAN_DIR_NAME': '.plan'}
    created = run_script(
        MANAGE_STATUS, 'create', '--plan-id', plan_id, '--title', 't', '--phases', _PHASES, env_overrides=env
    )
    assert created.returncode == 0, f'manage-status create failed: {created.stdout}{created.stderr}'
    assert parse_toon(created.stdout).get('status') == 'success', f'manage-status create refused: {created.stdout}'
    shifted = run_script(MANAGE_STATUS, 'set-phase', '--plan-id', plan_id, '--phase', phase, env_overrides=env)
    assert shifted.returncode == 0, f'manage-status set-phase failed: {shifted.stdout}{shifted.stderr}'
    plan_dir = worktree / '.plan' / 'local' / 'plans' / plan_id
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    assert status.get('current_phase') == phase, f'manage-status did not persist current_phase: {status!r}'
    if steps is not None:
        (plan_dir / 'execution.toon').write_text(_manifest_toon(plan_id, steps), encoding='utf-8')
    return plan_dir


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
    assert code == 1, 'a refusal must exit 1'
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
    assert code == 1
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
    assert _commit_count(tmp_path) == 2, 'the sanctioned commit must have been created'


def test_plan_only_commit_passes(tmp_path: Path) -> None:
    """A ``.plan/``-only commit passes with no sanction, even in a finalize plan."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=[])
    _stage(tmp_path, '.plan/local/plans/PLAN-A/notes.txt', 'plan state\n')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'))

    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'plan_only'
    assert code == 0
    assert _commit_count(tmp_path) == 2, 'the plan-only commit must have been created'


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


def test_worktree_resident_plan_record_is_read(tmp_path: Path) -> None:
    """The LIVE record during phase 5+ is the worktree-resident one.

    ``prepare_execute`` MOVES the plan directory into the worktree, so a real
    finalize plan keeps its ``status.json`` under the worktree. The gate must read
    it (the recorded defect was that it did not engage on a real plan).
    """
    _init_repo(tmp_path)
    worktree = _worktree(tmp_path, 'plan-a')
    _write_worktree_plan(worktree, 'plan-a', steps=['pre-push-quality-gate'])
    _stage(tmp_path, 'src/a.py')

    refused, code = _run_commit(tmp_path, worktree)
    assert refused.get('refused') is True, f'{refused!r}'
    assert refused['phase'] == '6-finalize'
    assert refused['reason'] == 'no_sanction'
    assert code == 1

    sanctioned, ok = _run_commit(tmp_path, worktree, '--step', 'pre-push-quality-gate')
    assert sanctioned['status'] == 'success', f'{sanctioned!r}'
    assert sanctioned['reason'] == 'settle_band_step'
    assert ok == 0


def test_project_dir_in_a_worktree_subdirectory_still_refuses(tmp_path: Path) -> None:
    """A ``--project-dir`` in a SUBDIRECTORY of the worktree still resolves the plan."""
    _init_repo(tmp_path)
    worktree = _worktree(tmp_path, 'plan-a')
    _write_worktree_plan(worktree, 'plan-a')
    subdir = worktree / 'src'
    subdir.mkdir(parents=True)
    _stage(tmp_path, 'src/a.py')

    refused, code = _run_commit(tmp_path, subdir)

    assert refused.get('refused') is True, f'{refused!r}'
    assert refused['phase'] == '6-finalize'
    assert refused['reason'] == 'no_sanction'
    assert code == 1


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
    assert code == 1


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

    assert result.returncode == 2, f'--phase must be rejected by argparse: {result.stdout}{result.stderr}'
    assert 'unrecognized arguments' in result.stderr, result.stderr


# =============================================================================
# The finalize commit's own change-ledger row
#
# The 5-execute boundary refuses unless every branch commit carries a
# `kind=change` row, and phase 5's Step 10a settlement only ever wrote the
# deliverable commits'. So the commit verb — the one path every finalize commit
# goes through — writes the row for a `6-finalize` commit, and ONLY in that
# phase, which is what keeps Step 10a's row single.
# =============================================================================


def _ledger_path(root: Path) -> Path:
    """The change-ledger the commit verb's process resolves, under the test base."""
    return _base_dir(root) / 'work' / 'change-ledger.jsonl'


def _ledger_rows(root: Path) -> list[dict]:
    path = _ledger_path(root)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def test_a_step_commit_leaves_exactly_one_change_row(tmp_path: Path) -> None:
    """A 5f(b) commit is recorded, with git-sourced paths and the step as its id.

    Item 5f(b) relays `{step_id}` as `--step`; the row's `deliverable_id` is that
    id, and `changed_paths` comes from `git diff-tree` on the commit — the
    ledger's own sourcing rule, never the caller's staged list.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'), '--step', 'pre-push-quality-gate')

    assert code == 0, f'{result!r}'
    assert result['ledger_recorded'] is True
    assert result['ledger_deliverable_id'] == 'pre-push-quality-gate'
    rows = _ledger_rows(tmp_path)
    assert len(rows) == 1, rows
    row = rows[0]
    assert row['kind'] == 'change'
    assert row['commit_sha'] == result['commit_hash']
    assert row['changed_paths'] == ['src/a.py']
    assert row['deliverable_id'] == 'pre-push-quality-gate'


def test_the_inline_triage_commit_leaves_a_row_under_the_fixed_prefix(tmp_path: Path) -> None:
    """Item 7c(4a) passes no step; its commit is still recorded.

    The triage is not a manifest step, so the row's id is the constant
    `finalize-commit`. That id ends in no digit, which is what stops a reader
    that maps ids onto outline deliverables from reading a finalize commit as
    deliverable work.
    """
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

    assert code == 0, f'{result!r}'
    assert result['reason'] == 'section6_record'
    rows = _ledger_rows(tmp_path)
    assert [row['deliverable_id'] for row in rows] == ['finalize-commit']
    assert rows[0]['commit_sha'] == result['commit_hash']


def test_the_architecture_refresh_commit_leaves_a_row(tmp_path: Path) -> None:
    """The plan-only architecture refresh commit is a finalize commit like any other.

    `architecture-refresh` commits `.plan/project-architecture`, so the
    source-commit gate admits it as `plan_only` and it carries no step. It still
    owes a row: the boundary enumerates every branch commit, not only the source
    ones.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=[])
    _stage(tmp_path, '.plan/project-architecture/derived.json', '{"modules": []}\n')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'))

    assert code == 0, f'{result!r}'
    assert result['reason'] == 'plan_only'
    assert result['ledger_recorded'] is True
    rows = _ledger_rows(tmp_path)
    assert [row['changed_paths'] for row in rows] == [['.plan/project-architecture/derived.json']]


def test_a_main_checkout_commit_reads_its_phase_through_the_named_plan(tmp_path: Path, monkeypatch) -> None:
    """A `use_worktree: false` plan's row needs `--plan-id`: the tree cannot name it.

    The guard covers every plan, main-checkout ones included, so their finalize
    commits need rows too. Such a plan's tree IS the main checkout, so no path
    segment names it — the documented invocation therefore passes `--plan-id`,
    and the phase the row writer keys on is read through that id, from the
    main-anchored record.

    The tree-alone half cannot be asserted here: the suite's own basetemp lives
    under `.plan/local/worktrees/{plan}/`, so every temporary repository inherits
    a plan-named segment from its parent. The id-keyed lookup below is the
    load-bearing half either way.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    monkeypatch.setenv('PLAN_BASE_DIR', str(_base_dir(tmp_path)))

    assert git_workflow._plan_phase(tmp_path, 'plan-a') == '6-finalize'
    assert git_workflow._plan_phase(tmp_path, 'no-such-plan') is None, (
        'an id with no record must resolve nothing, so the phase above came from the record'
    )


def test_a_phase_5_commit_leaves_no_row_so_the_settlement_owns_the_only_one(tmp_path: Path) -> None:
    """Outside `6-finalize` the verb records nothing — Step 10a owns that row.

    This is the no-double-row control: the phase-5 commit itself writes none, and
    the settlement's append leaves exactly one.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=['pre-push-quality-gate'])
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, _worktree(tmp_path, 'plan-a'))

    assert code == 0, f'{result!r}'
    assert 'ledger_recorded' not in result
    assert _ledger_rows(tmp_path) == []

    head = _git(tmp_path, 'rev-parse', 'HEAD').stdout.strip()
    appended = run_script(
        MANAGE_CHANGE_LEDGER,
        'append',
        '--kind',
        'change',
        '--deliverable-id',
        '1',
        '--commit-sha',
        head,
        '--changed-paths',
        'src/a.py',
        '--worktree-root',
        str(tmp_path),
        env_overrides=_env(tmp_path),
    )
    assert appended.returncode == 0, f'{appended.stdout}{appended.stderr}'

    rows = _ledger_rows(tmp_path)
    assert [row['deliverable_id'] for row in rows] == ['1'], rows
    assert [row['commit_sha'] for row in rows] == [head]


# =============================================================================
# The ordinary finalize loop-back: both writers' rows admit the boundary
# =============================================================================


def _feature_branch_repo(tmp_path: Path) -> None:
    """A repo on `main` with a plan feature branch checked out."""
    _init_repo(tmp_path)
    _git(tmp_path, 'branch', '-M', 'main')
    _git(tmp_path, 'checkout', '-b', 'feature/lb-126')


def test_a_finalize_commit_then_a_loop_back_and_a_step_10a_commit_admit_the_boundary(
    tmp_path: Path, monkeypatch
) -> None:
    """The refused loop-back, reproduced and closed: both commits carry a row.

    The scenario the guard used to refuse: a finalize commit (item 5f(b)) lands,
    the review loop-backs to `5-execute`, and a Step 10a fix commit follows. At
    HEAD the finalize commit has no row, so the boundary refuses with
    `phase_end_markers_missing` and the plan can never re-enter `6-finalize`.
    The two writers together cover the branch, so the boundary admits it.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(_base_dir(tmp_path)))
    _feature_branch_repo(tmp_path)
    worktree = _worktree(tmp_path, 'plan-a')
    plan_dir = _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    status = {'plan_id': 'plan-a', 'metadata': {'use_worktree': True, 'worktree_path': str(tmp_path)}}

    # 5f(b): the dispatcher's finalize commit, through the verb.
    _stage(tmp_path, 'src/finalize.py')
    finalize_result, finalize_code = _run_commit(tmp_path, worktree, '--step', 'pre-push-quality-gate')
    assert finalize_code == 0, f'{finalize_result!r}'
    assert _lifecycle._phase_end_marker_refusal('plan-a', status) is None, (
        'the finalize commit alone must satisfy the boundary: it wrote its own row'
    )

    # Loop-back to 5-execute, then the Step 10a settlement commit.
    shifted = run_script(
        MANAGE_STATUS,
        'set-phase',
        '--plan-id',
        'plan-a',
        '--phase',
        '5-execute',
        env_overrides=_env(tmp_path),
    )
    assert shifted.returncode == 0, f'{shifted.stdout}{shifted.stderr}'
    _stage(tmp_path, 'src/fix.py')
    fix_result, fix_code = _run_commit(tmp_path, worktree)
    assert fix_code == 0, f'{fix_result!r}'
    fix_head = _git(tmp_path, 'rev-parse', 'HEAD').stdout.strip()
    appended = run_script(
        MANAGE_CHANGE_LEDGER,
        'append',
        '--kind',
        'change',
        '--deliverable-id',
        '1',
        '--commit-sha',
        fix_head,
        '--changed-paths',
        'src/fix.py',
        '--worktree-root',
        str(tmp_path),
        env_overrides=_env(tmp_path),
    )
    assert appended.returncode == 0, f'{appended.stdout}{appended.stderr}'

    assert _lifecycle._phase_end_marker_refusal('plan-a', status) is None, (
        'the loop-back branch must be admitted: each commit has exactly one row'
    )
    rows = _ledger_rows(tmp_path)
    assert len(rows) == len({row['commit_sha'] for row in rows}) == 2, rows


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
    assert verdict['step'] == 'pre-push-quality-gate'


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
    assert git_workflow._plan_id_from_worktree_path(None) is None
