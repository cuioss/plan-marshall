#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the clean-tree post-condition at the 5-execute → 6-finalize boundary.

``cmd_transition`` enforces a clean worktree when the next phase is a
blocking boundary: after the inline strict-verify guard passes, the guard
runs ``git -C {worktree_path} status --porcelain`` and refuses (skipping
``write_status``) on either of TWO distinct tree-state codes. Proves:

(a) a dirty worktree refuses with ``worktree_dirty_at_boundary``, lists the
    dirty paths, and leaves ``current_phase`` at ``5-execute``;
(b) a clean worktree passes;
(c) ``use_worktree=false`` plans skip the guard entirely;
(d) BOTH codes are members of ``VERIFY_REFUSAL_ERRORS`` so the CLI wrapper
    in ``manage-status.py`` main() exits 1 in lockstep with the in-process
    refusal (``verify_blocks_transition``);
(e) an UNREADABLE tree refuses with ``worktree_unreadable_at_boundary`` and
    publishes NO ``dirty_files`` key at all.

Cases (a) and (e) are a matched pair over one question — what the porcelain read
found — and the split is load-bearing because the REMEDIES differ: a dirty tree
needs the boundary settlement commit, whereas an unreadable one needs the worktree
itself repaired. Reporting one code for both sent the reader to the wrong remedy.

The companion implementation lives in ``_cmd_lifecycle.py``
(``_clean_tree_refusal``, wired into ``cmd_transition``'s blocking-boundary
branch after the strict-verify guard).

D2 extension: the same boundary additionally pins the 5-execute end-marker
post-condition (``_phase_end_marker_refusal``, after the clean-tree guard) —
committed-but-unrecorded deliverable commits refuse with
``execute_commits_unrecorded`` (enumerated) or ``phase_end_markers_missing``
(wholly missing or unreadable store, no list), and full coverage passes.
"""

import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

# PLAIN imports, deliberately — see the MODULE IDENTITY note below.
import _handshake_commands as _cmds
import _invariants as _inv
import pytest

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle_boundary')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_query_boundary')

cmd_create = _lifecycle.cmd_create
cmd_transition = _lifecycle.cmd_transition


# =============================================================================
# MODULE IDENTITY
# =============================================================================


def test_the_handshake_modules_are_the_instance_the_production_path_resolves():
    """The stubs in this module patch the module objects ``cmd_verify`` reads.

    Plain imports are what make that true, and the property is asserted rather
    than inferred from a green run. ``conftest.load_script_module`` would bind a
    SECOND copy under the same name: the stub would then patch an object the
    production path never consults, and every stubbed test here would pass while
    verifying nothing — a false green no ordinary assertion could distinguish
    from a real one.
    """
    assert sys.modules['_handshake_commands'] is _cmds
    assert sys.modules['_invariants'] is _inv


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

    _cmds.cmd_capture(Namespace(plan_id=plan_id, phase='5-execute', override=False, reason=None, strict=False))
    return status_path


# =============================================================================
# (a) Dirty worktree refuses the transition
# =============================================================================


def test_dirty_worktree_refuses_transition_and_lists_paths(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree
):
    """Uncommitted changes at the guarded boundary → worktree_dirty_at_boundary."""
    plan_id = 'boundary-dirty-refuses'
    status_path = _seed_boundary_plan(plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)})
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
        f'Refusal must list the dirty paths, got {result["dirty_files"]!r}.'
    )
    after = json.loads(status_path.read_text(encoding='utf-8'))
    assert after['current_phase'] == before['current_phase'] == '5-execute', (
        'cmd_transition wrote status despite the dirty-tree refusal — the guard must short-circuit before write_status.'
    )
    assert after['phases'] == before['phases'], (
        'Phase list mutated despite the dirty-tree refusal — write_status fired.'
    )


# =============================================================================
# (b) Clean worktree passes
# =============================================================================


def test_clean_worktree_passes_transition(plan_context, _stubbed_invariants, _stub_metadata, git_worktree):
    """A clean tree at the guarded boundary transitions normally."""
    plan_id = 'boundary-clean-passes'
    status_path = _seed_boundary_plan(plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)})
    # The end-marker gate needs a divergence base to establish its (here empty)
    # range — without references.json it refuses fail-closed.
    (plan_context.plan_dir_for(plan_id) / 'references.json').write_text(
        json.dumps({'base_branch': 'main'}), encoding='utf-8'
    )

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success', f'Clean worktree must pass the boundary guard, got {result!r}.'
    assert result['next_phase'] == '6-finalize'
    after = json.loads(status_path.read_text(encoding='utf-8'))
    assert after['current_phase'] == '6-finalize'


def test_plan_state_under_gitignored_dot_plan_stays_clean(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree
):
    """Worktree-resident plan state under gitignored ``.plan/`` never dirties
    the boundary — the porcelain read must not see it."""
    plan_id = 'boundary-plan-state-ignored'
    _seed_boundary_plan(plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)})
    # The end-marker gate needs a divergence base to establish its (here empty)
    # range — without references.json it refuses fail-closed.
    (plan_context.plan_dir_for(plan_id) / 'references.json').write_text(
        json.dumps({'base_branch': 'main'}), encoding='utf-8'
    )
    plan_state = git_worktree / '.plan' / 'local' / 'plans' / plan_id
    plan_state.mkdir(parents=True)
    (plan_state / 'status.json').write_text('{}')

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result['status'] == 'success', f'Gitignored .plan/ state must not trip the clean-tree guard, got {result!r}.'


# =============================================================================
# (c) use_worktree=false plans skip the guard
# =============================================================================


def test_use_worktree_false_skips_guard(plan_context, _stubbed_invariants, _stub_metadata, git_worktree):
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

    assert result['status'] == 'success', f'use_worktree=false must skip the clean-tree guard, got {result!r}.'
    assert result['next_phase'] == '6-finalize'


def test_empty_worktree_path_defers_to_verify_guard(plan_context, _stubbed_invariants, _stub_metadata):
    """``use_worktree=true`` with an empty path is the strict-verify guard's
    refusal territory (worktree_unresolved) — the clean-tree guard itself must
    not fire on an empty path."""
    assert _lifecycle._clean_tree_refusal('any-plan', {}) is None
    assert _lifecycle._clean_tree_refusal('any-plan', {'metadata': {'use_worktree': True, 'worktree_path': ''}}) is None


# =============================================================================
# (d) VERIFY_REFUSAL_ERRORS membership → CLI exit-1 lockstep
# =============================================================================


def test_both_tree_state_codes_are_members_of_verify_refusal_errors():
    """BOTH tree-state codes are in VERIFY_REFUSAL_ERRORS — the single source of
    truth that cmd_transition and the CLI exit-code wrapper consume.

    Splitting a code out of an existing one WITHOUT adding it here silently degrades
    the guard from fail-closed to fail-open: ``verify_blocks_transition`` would
    return False for the new code, so the transition would proceed and the CLI
    wrapper would exit 0 on a refusal the guard actually raised. Asserting the PAIR,
    rather than only the new member, is what keeps a future split from dropping
    either half.
    """
    for code in ('worktree_dirty_at_boundary', 'worktree_unreadable_at_boundary'):
        assert code in _lifecycle.VERIFY_REFUSAL_ERRORS, (
            f'{code} must be a VERIFY_REFUSAL_ERRORS member, or the boundary guard fails open for it.'
        )


def test_refusal_dict_blocks_transition_for_cli_wrapper(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree
):
    """The actual refusal dict returned by cmd_transition satisfies
    ``verify_blocks_transition`` — the exact predicate manage-status.py main()
    gates its exit-1 on, keeping the CLI wrapper in lockstep."""
    plan_id = 'boundary-cli-lockstep'
    _seed_boundary_plan(plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)})
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


def test_unreadable_tree_refuses_with_its_own_code_and_publishes_no_dirty_files(outside_repo_dir: Path):
    """A path where ``git status`` fails (not a repo) refuses fail-closed — and says
    the tree was UNREADABLE rather than dirty.

    The code carries the distinction: the porcelain read never happened, so "dirty"
    names a condition nobody observed, and it points at the wrong remedy (a
    settlement commit rather than repairing the worktree).

    ``dirty_files`` is ABSENT rather than ``[]``. An empty list here would be a
    measured-zero claim about a tree that was never enumerated — byte-identical to
    what a genuinely clean read produces — which is the same false zero the matched
    dirty case above refutes by carrying a real, non-empty list.
    """
    # ``plain`` must be OUTSIDE the repo: pytest's tmp_path now roots under the
    # repo-local --basetemp, where ``git status`` succeeds (the dir is inside a
    # git worktree) instead of failing as this fail-closed test requires.
    plain = outside_repo_dir / 'not-a-repo'
    plain.mkdir()

    refusal = _lifecycle._clean_tree_refusal(
        'any-plan', {'metadata': {'use_worktree': True, 'worktree_path': str(plain)}}
    )

    assert refusal is not None
    assert refusal['error'] == 'worktree_unreadable_at_boundary', (
        f'An unreadable tree must report its OWN code, not the dirty one; got {refusal!r}.'
    )
    assert 'dirty_files' not in refusal, (
        f'A tree that was never enumerated must publish no dirty_files key at all; got {refusal!r}.'
    )
    assert 'cannot prove' in refusal['message']
    assert _lifecycle.verify_blocks_transition(refusal) is True, (
        'The unreadable refusal must block via verify_blocks_transition — otherwise the '
        'CLI wrapper exits 0 while the in-process guard refuses, which is the fail-open '
        'degradation a code split must not introduce.'
    )


# =============================================================================
# D2 — 5-execute end-marker post-condition: committed-but-unrecorded work
# =============================================================================
#
# The clean-tree guard above only reads UNCOMMITTED state. A deliverable commit
# with no ``kind=change`` ledger row (a skipped Step 10a settlement) is the
# silent skip it cannot see — ``_phase_end_marker_refusal`` closes it. Pins:
#
# (a) ALL end-marker codes are members of ``VERIFY_REFUSAL_ERRORS``;
# (b) both refusal shapes satisfy ``verify_blocks_transition`` (CLI exit-1 lockstep);
# (c) a partially recorded branch refuses at the transition with
#     ``execute_commits_unrecorded``, enumerates the gap, and writes nothing;
# (d) full coverage passes the transition;
# (e) zero recorded rows refuse as ``phase_end_markers_missing`` (wholly missing);
# (f) an unreadable marker store refuses as ``phase_end_markers_missing`` with
#     NO ``unrecorded_commits`` key at all (the matched pair of (c)).


def test_both_end_marker_codes_are_members_of_verify_refusal_errors():
    """ALL end-marker codes are in VERIFY_REFUSAL_ERRORS — the single source of
    truth that cmd_transition and the CLI exit-code wrapper consume."""
    for code in ('phase_end_markers_missing', 'execute_commits_unrecorded', 'branch_range_unresolvable'):
        assert code in _lifecycle.VERIFY_REFUSAL_ERRORS, (
            f'{code} must be a VERIFY_REFUSAL_ERRORS member, or the end-marker guard fails open for it.'
        )


def test_end_marker_refusals_block_transition_for_cli_wrapper():
    """All end-marker refusal shapes satisfy ``verify_blocks_transition``."""
    for error in ('phase_end_markers_missing', 'execute_commits_unrecorded', 'branch_range_unresolvable'):
        assert _lifecycle.verify_blocks_transition({'status': 'error', 'error': error}) is True, (
            f'{error} must block via verify_blocks_transition — otherwise the CLI wrapper '
            'exits 0 while the in-process guard refuses.'
        )


def _seed_end_marker_plan(plan_context, plan_id: str, git_worktree) -> None:
    """Seed a 5-execute boundary plan with worktree metadata and a base_branch record."""
    _seed_boundary_plan(plan_context, plan_id, {'use_worktree': True, 'worktree_path': str(git_worktree)})
    refs_path = plan_context.plan_dir_for(plan_id) / 'references.json'
    refs_path.write_text(json.dumps({'base_branch': 'main', 'branch': f'feature/{plan_id}'}), encoding='utf-8')


def test_unrecorded_commits_refuse_transition_and_name_the_gap(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree, monkeypatch
):
    """A branch commit with no kind=change row refuses with execute_commits_unrecorded."""
    plan_id = 'end-marker-unrecorded-refuses'
    _seed_end_marker_plan(plan_context, plan_id, git_worktree)
    recorded_sha = 'a' * 40
    missing_sha = 'b' * 40
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [recorded_sha, missing_sha])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: {recorded_sha})
    status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    before = json.loads(status_path.read_text(encoding='utf-8'))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'execute_commits_unrecorded', (
        f'Expected the end-marker refusal at the guarded boundary, got {result!r}.'
    )
    assert result['unrecorded_commits'] == [missing_sha], (
        f'Refusal must enumerate the unrecorded commits, got {result!r}.'
    )
    assert result['recorded_count'] == 1
    assert result['branch_commit_count'] == 2
    assert 'mailbox' not in result, 'a refused transition carries no mailbox block'
    after = json.loads(status_path.read_text(encoding='utf-8'))
    assert after['current_phase'] == before['current_phase'] == '5-execute', (
        'cmd_transition wrote status despite the end-marker refusal — the guard must short-circuit before write_status.'
    )


def test_fully_recorded_markers_pass_transition(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree, monkeypatch
):
    """Full ledger coverage of the branch range transitions normally."""
    plan_id = 'end-marker-recorded-passes'
    _seed_end_marker_plan(plan_context, plan_id, git_worktree)
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: {'a' * 40})

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success', f'Fully recorded markers must pass the boundary guard, got {result!r}.'
    assert result['next_phase'] == '6-finalize'


def test_abbreviated_ledger_shas_compare_equal_to_full_branch_shas(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree, monkeypatch
):
    """An abbreviated ledger SHA still proves its full branch commit was recorded."""
    plan_id = 'end-marker-abbreviated-passes'
    _seed_end_marker_plan(plan_context, plan_id, git_worktree)
    full_sha = 'abcdef1234567890abcdef1234567890abcdef12'
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [full_sha])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: {full_sha[:7]})

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'success', (
        f'An abbreviated ledger SHA must compare equal to its full branch SHA, got {result!r}.'
    )
    assert result['next_phase'] == '6-finalize'


def test_short_prefix_below_git_floor_does_not_match(plan_context, monkeypatch):
    """A ledger prefix shorter than git's 7-char floor never counts as recorded."""
    plan_id = 'end-marker-short-prefix'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='End Marker Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    full_sha = 'abcdef1234567890abcdef1234567890abcdef12'
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [full_sha])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: {'abc'})

    refusal = _lifecycle._phase_end_marker_refusal(
        plan_id, {'metadata': {'use_worktree': True, 'worktree_path': '/tmp/any-worktree'}}
    )

    assert refusal is not None
    assert refusal['error'] == 'execute_commits_unrecorded', (
        f'A sub-floor prefix must not satisfy the end-marker guard, got {refusal!r}.'
    )


def test_zero_recorded_rows_refuse_as_markers_missing(plan_context, monkeypatch):
    """Zero kind=change rows with branch commits present is WHOLLY missing, not partial."""
    plan_id = 'end-marker-zero-rows'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='End Marker Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40, 'b' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: set())

    refusal = _lifecycle._phase_end_marker_refusal(
        plan_id, {'metadata': {'use_worktree': True, 'worktree_path': '/tmp/any-worktree'}}
    )

    assert refusal is not None
    assert refusal['error'] == 'phase_end_markers_missing', (
        f'A store holding zero rows must report missing, not partial coverage; got {refusal!r}.'
    )
    assert refusal['unrecorded_commits'] == ['a' * 40, 'b' * 40]
    assert refusal['recorded_count'] == 0
    assert _lifecycle.verify_blocks_transition(refusal) is True


def test_unreadable_store_refuses_missing_without_a_commit_list(plan_context, monkeypatch):
    """An unreadable marker store refuses fail-closed and publishes NO commit list.

    The store side was never enumerated, so a list — even of the git-side shas —
    would assert non-recording nobody verified. The omission mirrors the
    unreadable-tree guard publishing no ``dirty_files`` key.
    """
    plan_id = 'end-marker-store-unreadable'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='End Marker Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: None)

    refusal = _lifecycle._phase_end_marker_refusal(
        plan_id, {'metadata': {'use_worktree': True, 'worktree_path': '/tmp/any-worktree'}}
    )

    assert refusal is not None
    assert refusal['error'] == 'phase_end_markers_missing', (
        f'An unreadable store must report missing, not unrecorded; got {refusal!r}.'
    )
    assert 'unrecorded_commits' not in refusal, (
        f'A store that was never read must publish no commit list at all; got {refusal!r}.'
    )
    assert _lifecycle.verify_blocks_transition(refusal) is True


# =============================================================================
# D2 — guard ordering and refusal-shape completeness (TASK-4).
#
# The end-marker gate runs AFTER the clean-tree guard in cmd_transition's
# blocking-boundary branch, and the unreadable-store refusal carries a
# machine-readable ``reason``. These pins hold both properties: the ordering
# decides which remedy the reader reaches for when both gates would fire, and
# the reason names what the refusal DID establish where the commit list says
# what it does NOT claim.
# =============================================================================


def test_clean_tree_guard_fires_before_end_marker_guard(
    plan_context, _stubbed_invariants, _stub_metadata, git_worktree, monkeypatch
):
    """A dirty tree with unrecorded commits refuses as dirty, not unrecorded.

    The clean-tree guard runs first in cmd_transition's blocking-boundary
    branch: when both gates would fire, the reader is sent to the settlement
    commit for the uncommitted state, not to the ledger bookkeeping. The
    reversed order would name the wrong remedy while uncommitted edits are
    still on disk.
    """
    plan_id = 'ordering-dirty-before-markers'
    _seed_end_marker_plan(plan_context, plan_id, git_worktree)
    (git_worktree / 'src.py').write_text('x = 2\n')
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['b' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: set())

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'worktree_dirty_at_boundary', (
        f'The clean-tree guard must fire before the end-marker gate, got {result!r}.'
    )


def test_unreadable_store_refusal_carries_reason(plan_context, monkeypatch):
    """The unreadable-store refusal names WHY nothing was enumerated.

    Companions the no-commit-list pin above: the omission says what the
    refusal does NOT claim, and ``reason`` plus ``message`` say what it DID
    establish — the store side could not be read. A refusal carrying neither
    would be indistinguishable from a bare code.
    """
    plan_id = 'end-marker-store-reason'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='End Marker Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: None)

    refusal = _lifecycle._phase_end_marker_refusal(
        plan_id, {'metadata': {'use_worktree': True, 'worktree_path': '/tmp/any-worktree'}}
    )

    assert refusal is not None
    assert refusal['error'] == 'phase_end_markers_missing'
    assert refusal['reason'], 'the refusal must name why the store side went unread'
    assert refusal['message'], 'the refusal must carry a human-readable message'
