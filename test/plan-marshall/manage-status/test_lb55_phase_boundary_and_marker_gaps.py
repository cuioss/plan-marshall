#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-55 D2 — phase boundaries and the unrecorded-commit guard.

Five behaviours, each with the matched control that keeps it from passing vacuously:

(a) a phase that carries a metrics ``start_time`` and no ``end_time`` refuses the
    transition that would advance past it (``phase_boundary_unstamped``), and the
    same plan with the boundary closed passes;
(b) the unrecorded-commit guard applies to a MAIN-CHECKOUT plan (``use_worktree:
    false``), which it used to skip entirely;
(c) the guard reads the ledger of the plan's OWN checkout, so a transition run from
    another cwd does not read that cwd's ledger;
(d) the branch range is measured against ``origin/{base}``, so a rebase onto a newer
    remote base passes even when the local base branch is stale;
(e) ``set-phase`` into ``6-finalize`` runs the same guard as ``transition`` — the
    second door into finalize is not a bypass.
"""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path

# PLAIN import, deliberately: ``_status_query.cmd_set_phase`` imports
# ``_phase_end_marker_refusal`` from ``_cmd_lifecycle`` AT CALL TIME, so the module
# object it reaches is the one registered under the bare name. Patching only the
# ``load_script_module`` copy below would leave the set-phase path reading the
# unpatched production module — a stub that verifies nothing.
import _cmd_lifecycle as _cmd_lifecycle_plain
import _handshake_commands as _cmds
import _invariants as _inv
import pytest

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb55_lifecycle')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_lb55_status_query')

PHASES = '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize'


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry so the strict-verify guard passes."""
    state = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'main_dirty_files': [],
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'unfinished_tasks_count': 0,
        'pending_findings_by_type': '',
        'pending_findings_blocking_count': 0,
    }

    def always(_pid, _md):
        return True

    def make_capture(name):
        def _cap(_pid, _md, _phase):
            return state[name]

        return _cap

    stubbed = [(name, always, make_capture(name)) for name in state]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, '_load_status_metadata', lambda _pid: {})
    return state


def _seed_plan(plan_context, plan_id: str, metadata: dict) -> Path:
    """Create a plan at 5-execute with the given ``status.metadata``.

    Returns its plan directory.
    """
    _lifecycle.cmd_create(Namespace(plan_id=plan_id, title='LB-55 Boundary Test', phases=PHASES, force=False))
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        _query.cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    _query.cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))

    status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_path.read_text(encoding='utf-8'))
    status['metadata'] = metadata
    status_path.write_text(json.dumps(status), encoding='utf-8')
    plan_dir: Path = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    return plan_dir


def _write_metrics(plan_dir: Path, rows: dict[str, dict[str, str]]) -> None:
    """Write ``work/metrics.toon`` in the manage-metrics format, markers only."""
    work = plan_dir / 'work'
    work.mkdir(exist_ok=True)
    lines: list[str] = []
    for phase, fields in rows.items():
        lines.append(f'[{phase}]')
        for key, value in fields.items():
            lines.append(f'{key}: {value}')
    (work / 'metrics.toon').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ['git', '-C', str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, 'init', '-q', '-b', 'main')
    _git(root, 'config', 'user.email', 't@t.test')
    _git(root, 'config', 'user.name', 'Test')
    (root / '.gitignore').write_text('.plan/\n', encoding='utf-8')
    (root / 'a.txt').write_text('a\n', encoding='utf-8')
    _git(root, 'add', '.')
    _git(root, 'commit', '-q', '-m', 'A')


def _write_ledger(root: Path, shas: list[str]) -> None:
    work = root / '.plan' / 'work'
    work.mkdir(parents=True, exist_ok=True)
    rows = [
        json.dumps({'kind': 'change', 'commit_sha': sha, 'worktree_sha': sha, 'deliverable_id': 'D1'}) for sha in shas
    ]
    (work / 'change-ledger.jsonl').write_text('\n'.join(rows) + '\n', encoding='utf-8')


# =============================================================================
# (a) A start marker with no end marker refuses the advance past that phase
# =============================================================================


def test_a_start_without_end_marker_refuses_the_transition(plan_context, _stubbed_invariants, monkeypatch):
    """`4-plan` opened and never closed refuses the 5-execute completion."""
    plan_id = 'lb55-start-without-end-refuses'
    plan_dir = _seed_plan(plan_context, plan_id, {'use_worktree': False})
    _write_metrics(
        plan_dir,
        {
            '4-plan': {'start_time': '2026-10-24T08:00:00Z'},
            '5-execute': {'start_time': '2026-10-24T08:05:00Z'},
        },
    )
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [])
    status_path = plan_dir / 'status.json'
    before = json.loads(status_path.read_text(encoding='utf-8'))

    result = _lifecycle.cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == _lifecycle.PHASE_BOUNDARY_UNSTAMPED_ERROR, (
        f'the half-stamped 4-plan boundary must refuse the advance, got {result!r}'
    )
    assert result['boundaries'] == [{'phase': '4-plan', 'missing': 'end_time'}]
    assert _lifecycle.verify_blocks_transition(result) is True, 'the refusal must drive the CLI exit-1 wrapper'
    after = json.loads(status_path.read_text(encoding='utf-8'))
    assert after['current_phase'] == before['current_phase'] == '5-execute', (
        'cmd_transition wrote status despite the boundary refusal'
    )


def test_the_closed_boundary_passes_the_transition(plan_context, _stubbed_invariants, monkeypatch):
    """⛔ MATCHED CONTROL — the same plan with 4-plan's end marker closes passes."""
    plan_id = 'lb55-start-and-end-passes'
    plan_dir = _seed_plan(plan_context, plan_id, {'use_worktree': False})
    _write_metrics(
        plan_dir,
        {
            '4-plan': {'start_time': '2026-10-24T08:00:00Z', 'end_time': '2026-10-24T08:04:00Z'},
            '5-execute': {'start_time': '2026-10-24T08:05:00Z'},
        },
    )
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [])

    result = _lifecycle.cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success', f'a closed boundary must pass, got {result!r}'
    assert result['next_phase'] == '6-finalize'


def test_a_phase_that_never_recorded_a_boundary_is_not_applicable(plan_context, _stubbed_invariants, monkeypatch):
    """A phase with no metrics row never started recording — nothing to reconcile."""
    plan_id = 'lb55-no-metrics-row'
    _seed_plan(plan_context, plan_id, {'use_worktree': False})
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [])

    result = _lifecycle.cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['status'] == 'success', f'a plan with no metrics record must not be blocked, got {result!r}'


# =============================================================================
# (b) The unrecorded-commit guard also applies to a main-checkout plan
# =============================================================================


def test_a_main_checkout_plan_with_an_unrecorded_commit_refuses(plan_context, monkeypatch):
    """``use_worktree: false`` no longer skips the end-marker guard."""
    plan_id = 'lb55-main-checkout-unrecorded'
    plan_dir = _seed_plan(plan_context, plan_id, {'use_worktree': False})
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    missing = 'a' * 40
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [missing])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda _root=None: {'b' * 40})

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)

    assert refusal is not None, 'a main-checkout plan with an unrecorded commit must be refused'
    assert refusal['error'] == 'execute_commits_unrecorded'
    assert refusal['unrecorded_commits'] == [missing]


def test_a_main_checkout_plan_with_full_coverage_passes(plan_context, monkeypatch):
    """⛔ MATCHED CONTROL — the same plan with its commit recorded passes."""
    plan_id = 'lb55-main-checkout-recorded'
    plan_dir = _seed_plan(plan_context, plan_id, {'use_worktree': False})
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda _root=None: {'a' * 40})

    assert _lifecycle._phase_end_marker_refusal(plan_id, status) is None


# =============================================================================
# (c) The ledger read follows the plan's own checkout, never the cwd
# =============================================================================


def test_the_guard_reads_the_plans_own_checkout_ledger(plan_context, tmp_path, monkeypatch):
    """A row in the plan's worktree ledger counts even when the cwd ledger is empty."""
    plan_id = 'lb55-own-checkout-ledger'
    checkout = tmp_path / 'wt'
    checkout.mkdir()
    sha = 'c' * 40
    _write_ledger(checkout, [sha])
    plan_dir = _seed_plan(plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(checkout)})
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [sha])

    assert _lifecycle._phase_end_marker_refusal(plan_id, status) is None, (
        'the row is in the plan worktree ledger, so the commit IS recorded'
    )


def test_the_same_plan_refuses_when_the_own_checkout_ledger_is_empty(plan_context, tmp_path, monkeypatch):
    """⛔ MATCHED CONTROL — with that row removed, the same fixture refuses."""
    plan_id = 'lb55-own-checkout-ledger-negative'
    checkout = tmp_path / 'wt-empty'
    checkout.mkdir()
    _write_ledger(checkout, [])
    plan_dir = _seed_plan(plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(checkout)})
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['c' * 40])

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)

    assert refusal is not None
    assert refusal['error'] == 'phase_end_markers_missing'


# =============================================================================
# (d) The branch range is measured against the REMOTE base
# =============================================================================


def test_a_branch_rebased_onto_a_newer_origin_base_passes_with_a_stale_local_base(plan_context, tmp_path, monkeypatch):
    """The stale local base must not pull already-landed base commits into the range."""
    plan_id = 'lb55-stale-local-base'
    repo = tmp_path / 'repo'
    _init_repo(repo)
    base_old = _git(repo, 'rev-parse', 'HEAD')
    (repo / 'b.txt').write_text('b\n', encoding='utf-8')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'B')
    base_new = _git(repo, 'rev-parse', 'HEAD')
    _git(repo, 'checkout', '-q', '-b', 'feature')
    (repo / 'c.txt').write_text('c\n', encoding='utf-8')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'C')
    branch_sha = _git(repo, 'rev-parse', 'HEAD')
    # origin/main is current, local main is stale (points at the OLD base).
    _git(repo, 'update-ref', 'refs/remotes/origin/main', base_new)
    _git(repo, 'update-ref', 'refs/heads/main', base_old)
    _write_ledger(repo, [branch_sha])

    plan_dir = _seed_plan(plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(repo)})
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)

    assert refusal is None, (
        f'only the branch commit should be in the range; got {refusal!r}. '
        f'The stale local main ({base_old}) pulled base commit {base_new} into it.'
    )


def test_the_range_measured_against_the_stale_local_base_would_refuse(tmp_path):
    """⛔ MATCHED CONTROL — the local base still resolves, so the range is not empty.

    The control proves the case above passed because of the REMOTE comparison, not
    because the range came back empty either way: measuring the same repository
    against the stale local base includes the base commit, which carries no row.
    """
    repo = tmp_path / 'repo-control'
    _init_repo(repo)
    base_old = _git(repo, 'rev-parse', 'HEAD')
    (repo / 'b.txt').write_text('b\n', encoding='utf-8')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'B')
    base_new = _git(repo, 'rev-parse', 'HEAD')
    _git(repo, 'checkout', '-q', '-b', 'feature')
    (repo / 'c.txt').write_text('c\n', encoding='utf-8')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'C')
    _git(repo, 'update-ref', 'refs/remotes/origin/main', base_new)
    _git(repo, 'update-ref', 'refs/heads/main', base_old)

    against_remote = _lifecycle._branch_commit_shas(str(repo), 'main')
    local_only = subprocess.run(
        ['git', '-C', str(repo), 'rev-list', f'{base_old}..HEAD'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    assert against_remote is not None
    assert len(against_remote) == 1, f'the remote comparison must see only the branch commit, got {against_remote}'
    assert len(local_only) == 2, f'the stale local base must see the extra base commit, got {local_only}'


# =============================================================================
# (e) set-phase into 6-finalize runs the same guard
# =============================================================================


def test_set_phase_into_finalize_refuses_like_transition(plan_context, monkeypatch):
    """The second door into 6-finalize is not a bypass."""
    plan_id = 'lb55-set-phase-refuses'
    plan_dir = _seed_plan(plan_context, plan_id, {'use_worktree': False})
    missing = 'd' * 40
    for module in (_lifecycle, _cmd_lifecycle_plain):
        monkeypatch.setattr(module, '_branch_commit_shas', lambda _p, _b: [missing])
        monkeypatch.setattr(module, '_recorded_change_shas', lambda _root=None: {'e' * 40})
    status_path = plan_dir / 'status.json'
    before = json.loads(status_path.read_text(encoding='utf-8'))

    result = _query.cmd_set_phase(Namespace(plan_id=plan_id, phase='6-finalize'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'execute_commits_unrecorded', f'set-phase must run the guard, got {result!r}'
    after = json.loads(status_path.read_text(encoding='utf-8'))
    assert after['current_phase'] == before['current_phase'] == '5-execute'


def test_set_phase_into_finalize_passes_with_full_coverage(plan_context, monkeypatch):
    """⛔ MATCHED CONTROL — full coverage lets set-phase through."""
    plan_id = 'lb55-set-phase-passes'
    _seed_plan(plan_context, plan_id, {'use_worktree': False})
    for module in (_lifecycle, _cmd_lifecycle_plain):
        monkeypatch.setattr(module, '_branch_commit_shas', lambda _p, _b: ['d' * 40])
        monkeypatch.setattr(module, '_recorded_change_shas', lambda _root=None: {'d' * 40})

    result = _query.cmd_set_phase(Namespace(plan_id=plan_id, phase='6-finalize'))

    assert result is not None
    assert result['status'] == 'success', f'full coverage must not block set-phase, got {result!r}'
