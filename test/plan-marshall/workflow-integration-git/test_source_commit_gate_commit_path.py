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

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, get_skill_dir, load_script_module, run_script

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
# The commit's own change-ledger row
#
# The 5-execute boundary refuses unless every branch commit carries a
# `kind=change` row, and phase 5's Step 10a settlement writes only the
# deliverable commits'. The commit verb — the path every commit goes through —
# therefore writes the row a settlement does not own: a `6-finalize` commit
# always, and a phase-5 hand-back commit only when the caller marks it with
# `--record-change`. That marker is what keeps Step 10a's row single for an
# UNMARKED phase-5 commit, so no commit ever gets two rows.
# =============================================================================


def _ledger_path(root: Path) -> Path:
    """The change-ledger the commit verb's process resolves, under the test base."""
    return _base_dir(root) / 'work' / 'change-ledger.jsonl'


def _ledger_rows(root: Path) -> list[dict]:
    path = _ledger_path(root)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def _tree_ledger_rows(tree: Path) -> list[dict]:
    """The ledger a tree OWNS — the file the commit verb writes and the boundary reads.

    ``{tree}/.plan/work/change-ledger.jsonl`` is the checkout's own ledger, not
    the caller-cwd-resolved one, so it is where a commit made THROUGH the verb
    lands whatever directory the caller runs from.
    """
    path = tree / '.plan' / 'work' / 'change-ledger.jsonl'
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def _append_row(root: Path, sha: str, deliverable_id: str, changed_paths: list[str]) -> None:
    """Append one `kind=change` row through the ledger's own verb."""
    appended = run_script(
        MANAGE_CHANGE_LEDGER,
        'append',
        '--kind',
        'change',
        '--deliverable-id',
        deliverable_id,
        '--commit-sha',
        sha,
        '--changed-paths',
        ','.join(changed_paths),
        '--worktree-root',
        str(root),
        env_overrides=_env(root),
    )
    assert appended.returncode == 0, f'{appended.stdout}{appended.stderr}'


def test_a_step_commit_leaves_exactly_one_change_row(tmp_path: Path) -> None:
    """A 5f(b) commit is recorded, with git-sourced paths and the step as its id.

    Item 5f(b) relays `{step_id}` as `--step`; the row's `deliverable_id` is that
    id, and `changed_paths` comes from git on the commit — the ledger's own
    sourcing rule, never the caller's staged list. The row lands in the TARGET
    tree's ledger, the file the boundary guard reads.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    worktree = _worktree(tmp_path, 'plan-a')
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, worktree, '--step', 'pre-push-quality-gate')

    assert code == 0, f'{result!r}'
    assert result['ledger_recorded'] is True
    assert result['ledger_deliverable_id'] == 'pre-push-quality-gate'
    rows = _tree_ledger_rows(worktree)
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
    worktree = _worktree(tmp_path, 'plan-a')

    result, code = _run_commit(tmp_path, worktree)

    assert code == 0, f'{result!r}'
    assert result['reason'] == 'section6_record'
    rows = _tree_ledger_rows(worktree)
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
    worktree = _worktree(tmp_path, 'plan-a')
    _stage(tmp_path, '.plan/project-architecture/derived.json', '{"modules": []}\n')

    result, code = _run_commit(tmp_path, worktree)

    assert code == 0, f'{result!r}'
    assert result['reason'] == 'plan_only'
    assert result['ledger_recorded'] is True
    rows = _tree_ledger_rows(worktree)
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


def test_an_unmarked_phase_5_commit_leaves_no_row_so_step_10a_owns_the_only_one(tmp_path: Path) -> None:
    """An UNMARKED phase-5 commit records nothing — Step 10a owns that row.

    This is the no-double-row control: a commit that carries no
    ``--record-change`` marker is a deliverable commit, so the verb writes no row
    and the settlement's append leaves exactly one.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=['pre-push-quality-gate'])
    worktree = _worktree(tmp_path, 'plan-a')
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, worktree)

    assert code == 0, f'{result!r}'
    assert 'ledger_recorded' not in result
    assert _tree_ledger_rows(worktree) == []
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
# The phase-5 hand-back commit: the orchestrator's own commit, recorded by the
# verb under a non-deliverable id
#
# Step 10a owns every deliverable commit's row, and the verb cannot tell a
# Step 10a commit from an orchestrator hand-back commit on its own — Step 10a
# calls the same verb. `--record-change` IS that marker: it makes the verb append
# the row for a commit no settlement owns (a quality-gate rewrite, a style fix, a
# Javadoc fix made after the envelope), while an unmarked commit keeps recording
# nothing, so no commit ever gets two rows.
# =============================================================================


def test_a_marked_phase_5_commit_records_its_own_row_under_the_handback_id(tmp_path: Path) -> None:
    """A commit marked `--record-change` in `5-execute` leaves its own row.

    The row's `deliverable_id` is the constant `handback-commit`, and its
    `changed_paths` is the commit's own path list as git reports it — the
    ledger's sourcing rule, which the caller never supplies. The row lands in
    the TARGET tree's ledger, the file the boundary guard reads for this
    checkout.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=['pre-push-quality-gate'])
    worktree = _worktree(tmp_path, 'plan-a')
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, worktree, '--record-change')

    assert code == 0, f'{result!r}'
    assert result['ledger_recorded'] is True
    assert result['ledger_deliverable_id'] == 'handback-commit'
    rows = _tree_ledger_rows(worktree)
    assert len(rows) == 1, rows
    assert rows[0]['kind'] == 'change'
    assert rows[0]['commit_sha'] == result['commit_hash']
    assert rows[0]['changed_paths'] == ['src/a.py']
    assert rows[0]['deliverable_id'] == 'handback-commit'
    assert _ledger_rows(tmp_path) == [], 'the caller-resolved ledger must not receive the row'


def test_a_marked_commit_spanning_two_deliverables_needs_no_attribution(tmp_path: Path) -> None:
    """A commit touching two deliverables' files takes ONE row, under one id.

    The spec's constraint: such a commit must not need an operator attribution
    decision. The single constant is what makes that true — nothing maps a path
    back to a deliverable.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=[])
    worktree = _worktree(tmp_path, 'plan-a')
    _stage(tmp_path, 'src/module-a/a.py')
    _stage(tmp_path, 'src/module-b/b.py')

    result, code = _run_commit(tmp_path, worktree, '--record-change')

    assert code == 0, f'{result!r}'
    rows = _tree_ledger_rows(worktree)
    assert [row['deliverable_id'] for row in rows] == ['handback-commit'], rows
    assert rows[0]['changed_paths'] == ['src/module-a/a.py', 'src/module-b/b.py']


def test_a_marked_finalize_commit_still_records_exactly_one_row(tmp_path: Path) -> None:
    """`--record-change` on a `6-finalize` commit adds no second row."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    worktree = _worktree(tmp_path, 'plan-a')
    _stage(tmp_path, 'src/a.py')

    result, code = _run_commit(tmp_path, worktree, '--step', 'pre-push-quality-gate', '--record-change')

    assert code == 0, f'{result!r}'
    assert result['ledger_deliverable_id'] == 'pre-push-quality-gate'
    rows = _tree_ledger_rows(worktree)
    assert [row['deliverable_id'] for row in rows] == ['pre-push-quality-gate'], rows


def test_the_handback_id_is_not_read_as_an_outline_deliverable() -> None:
    """Neither non-deliverable constant resolves to a deliverable number."""
    validate = load_script_module(
        'plan-marshall',
        'phase-6-finalize',
        '_review_support_validate.py',
        module_name='lb153_review_support_validate',
        register=False,
    )
    for constant in (git_workflow._HAND_BACK_COMMIT_DELIVERABLE_ID, git_workflow._FINALIZE_COMMIT_DELIVERABLE_ID):
        assert validate.deliverable_number(constant) is None, constant
    assert validate.deliverable_number('D3') == 3, 'the reader must still resolve a real deliverable id'


def test_a_marked_commit_that_completes_a_merge_records_first_parent_paths(tmp_path: Path) -> None:
    """A merge commit records the work it brought onto the branch, not an empty list."""
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=[])
    worktree = _worktree(tmp_path, 'plan-a')
    start = _git(tmp_path, 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()

    _stage(tmp_path, 'src/base.py')
    _git(tmp_path, 'commit', '-m', 'feat: base work')
    _git(tmp_path, 'checkout', '-b', 'side')
    _stage(tmp_path, 'src/side.py')
    _git(tmp_path, 'commit', '-m', 'feat: side work')
    _git(tmp_path, 'checkout', start)
    _git(tmp_path, 'merge', '--no-commit', '--no-ff', 'side')

    result, code = _run_commit(tmp_path, worktree, '--record-change')

    assert code == 0, f'{result!r}'
    parents = _git(tmp_path, 'rev-list', '--parents', '-n', '1', result['commit_hash']).stdout.split()
    assert len(parents) == 3, f'the premise: the commit is a merge, got {parents}'
    assert (
        _git(tmp_path, 'diff-tree', '--no-commit-id', '--name-only', '-r', result['commit_hash']).stdout.split() == []
    ), 'the premise: diff-tree over a merge enumerates nothing'
    rows = _tree_ledger_rows(worktree)
    assert [row['changed_paths'] for row in rows] == [['src/side.py']], rows


def test_a_merge_commit_records_both_paths_of_a_renamed_file(tmp_path: Path) -> None:
    """A rename the merged branch made is recorded on BOTH sides.

    `git diff` follows the user's rename detection by default, so a first-parent
    diff built without `--no-renames` reports the rename's DESTINATION only and
    the row silently loses the path the merge removed. The enumeration turns
    rename detection off, so both the old and the new path reach the row.
    """
    _init_repo(tmp_path)
    _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=[])
    worktree = _worktree(tmp_path, 'plan-a')
    start = _git(tmp_path, 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()

    _stage(tmp_path, 'src/old_name.py')
    _git(tmp_path, 'commit', '-m', 'feat: base work')
    _git(tmp_path, 'checkout', '-b', 'side')
    _git(tmp_path, 'mv', 'src/old_name.py', 'src/new_name.py')
    _git(tmp_path, 'commit', '-m', 'refactor: rename the module')
    _git(tmp_path, 'checkout', start)
    _git(tmp_path, 'merge', '--no-commit', '--no-ff', 'side')

    result, code = _run_commit(tmp_path, worktree, '--record-change')

    assert code == 0, f'{result!r}'
    parents = _git(tmp_path, 'rev-list', '--parents', '-n', '1', result['commit_hash']).stdout.split()
    assert len(parents) == 3, f'the premise: the commit is a merge, got {parents}'
    # The premise of the defect: plain `git diff` follows the rename. Pinned
    # explicitly, because the host's `diff.renames` would otherwise decide
    # whether this test proves anything.
    assert _git(
        tmp_path, '-c', 'diff.renames=true', 'diff', '--name-only', f'{result["commit_hash"]}^1', result['commit_hash']
    ).stdout.split() == ['src/new_name.py'], 'the premise: rename detection collapses the rename to its destination'
    rows = _tree_ledger_rows(worktree)
    assert len(rows) == 1, rows
    assert set(rows[0]['changed_paths']) == {'src/new_name.py', 'src/old_name.py'}, (
        f'the row must carry the removed path as well as the added one: {rows[0]["changed_paths"]!r}'
    )


def test_a_finalize_commit_whose_row_cannot_be_written_reports_it(tmp_path: Path) -> None:
    """A failed row write is reported to the caller, and the commit still stands.

    No boundary can surface this one: the `bookkeeping_gap` refusal runs at the
    `5-execute` completion, which a `6-finalize` commit is made AFTER. The
    caller that made the commit is therefore the reader, and the result it
    already gets is what it must read: `ledger_recorded: false` beside the
    `ledger_error` that says why.
    """
    _init_repo(tmp_path)
    worktree = _worktree(tmp_path, 'plan-a')
    _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    # The target tree's ledger slot is unwritable: `.plan/work` is a FILE.
    ledger_slot = worktree / '.plan' / 'work'
    ledger_slot.parent.mkdir(parents=True, exist_ok=True)
    ledger_slot.write_text('not a directory\n', encoding='utf-8')

    _stage(tmp_path, 'src/finalize.py')
    result, code = _run_commit(tmp_path, worktree, '--step', 'pre-push-quality-gate')

    assert code == 0, f'the commit itself is not refused: {result!r}'
    assert result['commit_hash'], result
    assert result['ledger_recorded'] is False, result
    assert result['ledger_error'], result
    assert _tree_ledger_rows(worktree) == [], 'the premise: no row could be written'


def test_the_docstring_no_longer_claims_the_boundary_surfaces_a_finalize_row() -> None:
    """The replaced claim must be gone, and what replaces it names the real reader."""
    doc = git_workflow._record_commit_change.__doc__ or ''
    assert 'is what surfaces it' not in doc, (
        'the docstring still claims the boundary surfaces a failed row; it cannot see a 6-finalize commit'
    )
    assert 'ledger_recorded' in doc, 'the replacement must name what the caller reads'
    assert '6-finalize' in doc, 'the replacement must name the commit kind the boundary cannot see'


def test_the_commit_changes_flow_tells_the_caller_to_read_ledger_recorded() -> None:
    """The one statement of the writer carries the caller obligation."""
    skill = (get_skill_dir('plan-marshall', 'workflow-integration-git') / 'SKILL.md').read_text(encoding='utf-8')
    assert 'do not report the commit as cleanly settled' in skill, (
        'the Commit Changes flow must state the caller obligation a failed row write leaves behind'
    )
    assert 'append --kind change' in skill, 'the obligation must name the ready-to-run repair'
    assert 'rather than as a silent gap' not in skill, (
        "the claim that a finalize commit's missing row is surfaced by the boundary must be gone, "
        'not merely contradicted'
    )


def test_the_row_lands_in_the_target_tree_ledger_the_boundary_reads(tmp_path: Path, monkeypatch) -> None:
    """A verb run from another checkout records into the TARGET tree's ledger.

    The boundary guard reads `{worktree}/.plan/work/change-ledger.jsonl` for the
    plan's own checkout, so a row written to the caller-cwd-resolved ledger would
    leave a recorded commit reported as unrecorded.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(_base_dir(tmp_path)))
    _feature_branch_repo(tmp_path)
    worktree = _worktree(tmp_path, 'plan-a')
    plan_dir = _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=[])
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    status = {'plan_id': 'plan-a', 'metadata': {'use_worktree': True, 'worktree_path': str(worktree)}}

    _stage(tmp_path, 'src/a.py')
    result, code = _run_commit(tmp_path, worktree, '--record-change')

    assert code == 0, f'{result!r}'
    assert [row['commit_sha'] for row in _tree_ledger_rows(worktree)] == [result['commit_hash']]
    assert not _ledger_rows(tmp_path), 'the caller-resolved ledger must not receive the row'
    assert _lifecycle._phase_end_marker_refusal('plan-a', status) is None, (
        'the guard reads the same ledger the verb wrote'
    )


# =============================================================================
# The documented recovery for `execute_commits_unrecorded`
#
# A commit made outside all THREE row owners — Step 10a's chain tail, the
# boundary settlement, and the `workflow-integration-git` `commit` verb —
# carries no row, so the boundary refuses and names each such SHA with its own
# `append` invocation.
# `plan-marshall/workflow/execution.md` § "Execute Phase Completion" documents
# appending those rows — under `handback-commit` when no deliverable owns the
# commit — instead of halting for the operator. These are the three shapes the
# field reports name.
# =============================================================================


@pytest.mark.parametrize(
    ('scenario', 'paths'),
    [
        # The refusal path is kind-agnostic — it sees SHAs and paths, never a
        # commit's kind — so these ids are the field's three instances, not three
        # branches. `gate-rewrite` and `style-fix` exercise the same branch with
        # different footprints; `two-deliverable` is the shape that would need an
        # attribution decision if the row carried per-deliverable ids.
        ('gate-rewrite', ['src/generated/rewritten-test.py']),
        ('style-fix', ['src/imports/order.py']),
        ('two-deliverable', ['src/module-a/a.py', 'src/module-b/b.py']),
    ],
)
def test_an_unrecorded_commit_is_repaired_by_appending_the_named_row(
    tmp_path: Path, monkeypatch, scenario: str, paths: list[str]
) -> None:
    """The refusal names the SHA; the documented append is what clears it.

    The branch is PARTIALLY recorded, which is the field shape: the settlement's
    commit has its row, and the commit no settlement owns is the one missing.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(_base_dir(tmp_path)))
    _feature_branch_repo(tmp_path)
    plan_dir = _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=[])
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    status = {'plan_id': 'plan-a', 'metadata': {'use_worktree': True, 'worktree_path': str(tmp_path)}}

    _stage(tmp_path, 'src/settled.py')
    _git(tmp_path, 'commit', '-m', 'feat: a recorded deliverable commit')
    _append_row(tmp_path, _git(tmp_path, 'rev-parse', 'HEAD').stdout.strip(), '1', ['src/settled.py'])

    for path in paths:
        _stage(tmp_path, path)
    _git(tmp_path, 'commit', '-m', f'chore({scenario}): a commit no settlement owns')
    head = _git(tmp_path, 'rev-parse', 'HEAD').stdout.strip()

    refusal = _lifecycle._phase_end_marker_refusal('plan-a', status)
    assert refusal is not None, f'{scenario}: an unrecorded branch commit must be refused'
    assert refusal['error'] == 'execute_commits_unrecorded', refusal
    assert refusal['signature'] == 'bookkeeping_gap', refusal
    assert refusal['unrecorded_commits'] == [head], refusal
    # The documented recovery tells the reader to RUN the invocation the refusal
    # printed, so the message must carry it, placeholders included.
    assert 'append --kind change' in refusal['message'], refusal['message']
    assert 'DELIVERABLE_ID' in refusal['message'], refusal['message']
    assert 'CHANGED_PATHS' in refusal['message'], refusal['message']

    git_paths = _git(tmp_path, 'diff-tree', '--no-commit-id', '--name-only', '-r', head).stdout.split()
    _append_row(tmp_path, head, git_workflow._HAND_BACK_COMMIT_DELIVERABLE_ID, git_paths)

    assert _lifecycle._phase_end_marker_refusal('plan-a', status) is None, (
        f'{scenario}: the appended row is the repair the documented recovery names'
    )
    rows = _ledger_rows(tmp_path)
    assert [row['deliverable_id'] for row in rows] == ['1', 'handback-commit'], rows
    assert rows[-1]['changed_paths'] == git_paths, (rows, git_paths)


def test_a_wholly_unrecorded_branch_takes_the_same_append_recovery(tmp_path: Path, monkeypatch) -> None:
    """The zero-row shape names its SHAs too, and the same append clears it."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(_base_dir(tmp_path)))
    _feature_branch_repo(tmp_path)
    plan_dir = _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=[])
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    status = {'plan_id': 'plan-a', 'metadata': {'use_worktree': True, 'worktree_path': str(tmp_path)}}

    _stage(tmp_path, 'src/generated/rewritten-test.py')
    _git(tmp_path, 'commit', '-m', 'chore: the gate rewrote a test file')
    head = _git(tmp_path, 'rev-parse', 'HEAD').stdout.strip()

    refusal = _lifecycle._phase_end_marker_refusal('plan-a', status)
    assert refusal is not None
    assert refusal['error'] == 'phase_end_markers_missing', refusal
    assert refusal['unrecorded_commits'] == [head], refusal

    _append_row(tmp_path, head, git_workflow._HAND_BACK_COMMIT_DELIVERABLE_ID, ['src/generated/rewritten-test.py'])

    assert _lifecycle._phase_end_marker_refusal('plan-a', status) is None
    assert [row['deliverable_id'] for row in _ledger_rows(tmp_path)] == ['handback-commit']


def test_a_merge_commit_takes_its_first_parent_diff(tmp_path: Path, monkeypatch) -> None:
    """A merge commit has no single changed-path set; the recovery names its first parent.

    The premise the recovery doc relies on: `diff-tree` over a merge enumerates
    nothing, so an append built from it would record an empty path list and still
    satisfy the SHA-based boundary check.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(_base_dir(tmp_path)))
    _feature_branch_repo(tmp_path)
    plan_dir = _write_plan(tmp_path, 'plan-a', phase='5-execute', steps=[])
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    status = {'plan_id': 'plan-a', 'metadata': {'use_worktree': True, 'worktree_path': str(tmp_path)}}

    _stage(tmp_path, 'src/settled.py')
    _git(tmp_path, 'commit', '-m', 'feat: a recorded deliverable commit')
    _append_row(tmp_path, _git(tmp_path, 'rev-parse', 'HEAD').stdout.strip(), '1', ['src/settled.py'])

    _git(tmp_path, 'checkout', '-b', 'side')
    _stage(tmp_path, 'src/side.py')
    _git(tmp_path, 'commit', '-m', 'feat: side work')
    side = _git(tmp_path, 'rev-parse', 'HEAD').stdout.strip()
    _git(tmp_path, 'checkout', 'feature/lb-126')
    _git(tmp_path, 'merge', '--no-ff', 'side', '-m', 'merge: side into feature')
    merged = _git(tmp_path, 'rev-parse', 'HEAD').stdout.strip()

    assert _git(tmp_path, 'diff-tree', '--no-commit-id', '--name-only', '-r', merged).stdout.split() == [], (
        'the premise: diff-tree over a merge commit enumerates nothing'
    )
    first_parent = _git(tmp_path, 'diff', '--no-renames', '--name-only', f'{merged}^1', merged).stdout.split()
    assert first_parent == ['src/side.py'], first_parent

    refusal = _lifecycle._phase_end_marker_refusal('plan-a', status)
    assert refusal is not None
    assert set(refusal['unrecorded_commits']) == {side, merged}, refusal

    _append_row(tmp_path, side, git_workflow._HAND_BACK_COMMIT_DELIVERABLE_ID, ['src/side.py'])
    _append_row(tmp_path, merged, git_workflow._HAND_BACK_COMMIT_DELIVERABLE_ID, first_parent)

    assert _lifecycle._phase_end_marker_refusal('plan-a', status) is None
    merge_row = [row for row in _ledger_rows(tmp_path) if row['commit_sha'] == merged]
    assert [row['changed_paths'] for row in merge_row] == [['src/side.py']], merge_row


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
    """A loop-back with both commits carrying a row: the boundary admits it.

    A finalize commit (item 5f(b)) lands, the review loop-backs to `5-execute`,
    and a Step 10a fix commit follows. Both writers cover the branch, so the
    boundary admits it rather than refusing with `phase_end_markers_missing`.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(_base_dir(tmp_path)))
    _feature_branch_repo(tmp_path)
    worktree = _worktree(tmp_path, 'plan-a')
    plan_dir = _write_plan(tmp_path, 'plan-a', phase='6-finalize', steps=['pre-push-quality-gate'])
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    status = {'plan_id': 'plan-a', 'metadata': {'use_worktree': True, 'worktree_path': str(worktree)}}

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
    rows = _tree_ledger_rows(worktree) + _ledger_rows(tmp_path)
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
