#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
"""Tests for the clean-tree post-condition at the 5-execute → 6-finalize boundary.

``cmd_transition`` enforces a clean worktree when the next phase is a
blocking boundary: after the inline strict-verify guard passes, the guard
runs ``git -C {worktree_path} status --porcelain`` and refuses with
``error: worktree_dirty_at_boundary`` (listing the dirty paths, skipping
``write_status``) when the tree carries uncommitted changes. Proves:

(a) a dirty worktree refuses the transition, lists the dirty paths, and
    leaves ``current_phase`` at ``5-execute``;
(b) a clean worktree passes;
(c) ``use_worktree=false`` plans skip the guard entirely;
(d) the error is a member of ``VERIFY_REFUSAL_ERRORS`` so the CLI wrapper
    in ``manage-status.py`` main() exits 1 in lockstep with the in-process
    refusal (``verify_blocks_transition``).

The companion implementation lives in ``_cmd_lifecycle.py``
(``_clean_tree_refusal``, wired into ``cmd_transition``'s blocking-boundary
branch after the strict-verify guard).
"""

import json
import subprocess
import sys as _sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle_boundary'
)
_query = load_script_module(
    'plan-marshall', 'manage-status', '_status_query.py', '_status_query_boundary'
)

cmd_create = _lifecycle.cmd_create
cmd_transition = _lifecycle.cmd_transition

# Standard imports for the handshake modules so the invariant stubs hit the
# same module instance ``_cmd_lifecycle.cmd_verify`` reads at runtime
# (mirrors test_manage_status_transition.py).
_PLAN_HANDSHAKE_SCRIPTS_DIR = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'scripts'
)
if _PLAN_HANDSHAKE_SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _PLAN_HANDSHAKE_SCRIPTS_DIR)

import _handshake_commands as _cmds
import _invariants as _inv

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry so the inline strict-verify guard
    passes cleanly and the clean-tree guard is the only variable under test."""
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
    return state


@pytest.fixture
def _stub_metadata(monkeypatch):
    """Replace ``_load_status_metadata`` so cmd_verify's own worktree
    assertion stays out of the way — the clean-tree guard reads metadata from
    the status dict directly, independent of this stub."""
    md: dict = {}
    monkeypatch.setattr(_cmds, '_load_status_metadata', lambda _pid: md)
    return md


@pytest.fixture
def git_worktree(tmp_path: Path) -> Path:
    """Minimal committed git repo standing in for the plan worktree.

    ``.gitignore`` covers ``.plan/`` so worktree-resident plan state never
    shows up in ``git status --porcelain`` (matches the real worktree layout).
    """
    repo = tmp_path / 'wt'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / '.gitignore').write_text('.plan/\n')
    (repo / 'src.py').write_text('x = 1\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)
    return repo


def _seed_boundary_plan(plan_context, plan_id: str, metadata: dict) -> Path:
    """Create a plan at 5-execute with a captured handshake row and the given
    ``status.metadata``. Returns the plan's status.json path."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Boundary Guard Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        _query.cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    _query.cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))

    status_path: Path = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_path.read_text(encoding='utf-8'))
    status['metadata'] = metadata
    status_path.write_text(json.dumps(status), encoding='utf-8')

    _cmds.cmd_capture(
        Namespace(plan_id=plan_id, phase='5-execute', override=False, reason=None, strict=False)
    )
    return status_path


# =============================================================================
# (a) Dirty worktree refuses the transition
# =============================================================================


def test_dirty_worktree_refuses_transition_and_lists_paths(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree
):
    """Uncommitted changes at the guarded boundary → worktree_dirty_at_boundary."""
    plan_id = 'boundary-dirty-refuses'
    status_path = _seed_boundary_plan(
        plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)}
    )
    # Dirty the tree: one modified tracked file + one untracked file.
    (git_worktree / 'src.py').write_text('x = 2\n')
    (git_worktree / 'stray.py').write_text('y = 3\n')
    before = json.loads(status_path.read_text(encoding='utf-8'))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'worktree_dirty_at_boundary', (
        f'Expected the clean-tree refusal at the guarded boundary, got {result!r}. '
        f'The _clean_tree_refusal guard in cmd_transition is not firing.'
    )
    assert set(result['dirty_files']) == {'src.py', 'stray.py'}, (
        f"Refusal must list the dirty paths, got {result['dirty_files']!r}."
    )
    after = json.loads(status_path.read_text(encoding='utf-8'))
    assert after['current_phase'] == before['current_phase'] == '5-execute', (
        'cmd_transition wrote status despite the dirty-tree refusal — the '
        'guard must short-circuit before write_status.'
    )
    assert after['phases'] == before['phases'], (
        'Phase list mutated despite the dirty-tree refusal — write_status fired.'
    )


# =============================================================================
# (b) Clean worktree passes
# =============================================================================


def test_clean_worktree_passes_transition(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree
):
    """A clean tree at the guarded boundary transitions normally."""
    plan_id = 'boundary-clean-passes'
    status_path = _seed_boundary_plan(
        plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)}
    )

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success', (
        f'Clean worktree must pass the boundary guard, got {result!r}.'
    )
    assert result['next_phase'] == '6-finalize'
    after = json.loads(status_path.read_text(encoding='utf-8'))
    assert after['current_phase'] == '6-finalize'


def test_plan_state_under_gitignored_dot_plan_stays_clean(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree
):
    """Worktree-resident plan state under gitignored ``.plan/`` never dirties
    the boundary — the porcelain read must not see it."""
    plan_id = 'boundary-plan-state-ignored'
    _seed_boundary_plan(
        plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)}
    )
    plan_state = git_worktree / '.plan' / 'local' / 'plans' / plan_id
    plan_state.mkdir(parents=True)
    (plan_state / 'status.json').write_text('{}')

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['status'] == 'success', (
        f'Gitignored .plan/ state must not trip the clean-tree guard, got {result!r}.'
    )


# =============================================================================
# (c) use_worktree=false plans skip the guard
# =============================================================================


def test_use_worktree_false_skips_guard(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree
):
    """Main-checkout plans (use_worktree=false) never run the porcelain read —
    even when a stale worktree_path points at a dirty tree."""
    plan_id = 'boundary-no-worktree-skips'
    _seed_boundary_plan(
        plan_context,
        plan_id,
        {'use_worktree': False, 'worktree_path': str(git_worktree)},
    )
    (git_worktree / 'src.py').write_text('x = 99\n')  # dirty — must be ignored

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['status'] == 'success', (
        f'use_worktree=false must skip the clean-tree guard, got {result!r}.'
    )
    assert result['next_phase'] == '6-finalize'


def test_empty_worktree_path_defers_to_verify_guard(
    plan_context, _stubbed_invariants, _stub_metadata
):
    """``use_worktree=true`` with an empty path is the strict-verify guard's
    refusal territory (worktree_unresolved) — the clean-tree guard itself must
    not fire on an empty path."""
    assert _lifecycle._clean_tree_refusal('any-plan', {}) is None
    assert (
        _lifecycle._clean_tree_refusal(
            'any-plan', {'metadata': {'use_worktree': True, 'worktree_path': ''}}
        )
        is None
    )


# =============================================================================
# (d) VERIFY_REFUSAL_ERRORS membership → CLI exit-1 lockstep
# =============================================================================


def test_error_is_member_of_verify_refusal_errors():
    """``worktree_dirty_at_boundary`` is in VERIFY_REFUSAL_ERRORS — the single
    source of truth both cmd_transition and the CLI exit-code wrapper consume."""
    assert 'worktree_dirty_at_boundary' in _lifecycle.VERIFY_REFUSAL_ERRORS


def test_refusal_dict_blocks_transition_for_cli_wrapper(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree
):
    """The actual refusal dict returned by cmd_transition satisfies
    ``verify_blocks_transition`` — the exact predicate manage-status.py main()
    gates its exit-1 on, keeping the CLI wrapper in lockstep."""
    plan_id = 'boundary-cli-lockstep'
    _seed_boundary_plan(
        plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)}
    )
    (git_worktree / 'src.py').write_text('x = 42\n')

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['error'] == 'worktree_dirty_at_boundary'
    assert _lifecycle.verify_blocks_transition(result) is True, (
        'The dirty-tree refusal dict must block via verify_blocks_transition — '
        'otherwise the CLI wrapper exits 0 while the in-process guard refuses.'
    )


# =============================================================================
# Fail-closed: unreadable tree cannot be proven clean
# =============================================================================


def test_git_status_failure_fails_closed(outside_repo_dir: Path):
    """A path where ``git status`` fails (not a repo) refuses fail-closed."""
    # ``plain`` must be OUTSIDE the repo: pytest's tmp_path now roots under the
    # repo-local --basetemp, where ``git status`` succeeds (the dir is inside a
    # git worktree) instead of failing as this fail-closed test requires.
    plain = outside_repo_dir / 'not-a-repo'
    plain.mkdir()

    refusal = _lifecycle._clean_tree_refusal(
        'any-plan', {'metadata': {'use_worktree': True, 'worktree_path': str(plain)}}
    )

    assert refusal is not None
    assert refusal['error'] == 'worktree_dirty_at_boundary'
    assert refusal['dirty_files'] == []
    assert 'cannot prove' in refusal['message']
