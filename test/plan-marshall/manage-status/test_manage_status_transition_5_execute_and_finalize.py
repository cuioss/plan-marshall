#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for manage-status.py transition: the 5-execute phase and the final-phase complete transition.

Its sections: D2 — Finalize completion boundary asserts the blocking-findings STATE;
D2 — 5-execute/finalize boundary end markers refuse unrecorded execute commits.
"""

import json
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import _handshake_commands as _cmds
import _invariants as _inv
import _ledger_core
import pytest
from _manage_status_transition_fixtures import (
    _lifecycle as _fixtures_lifecycle,
)
from _manage_status_transition_fixtures import (
    _seed_execute_phase_plan,
    _seed_finalize_phase_plan,
    _seed_plan_with_4_plan_capture,
    _seed_plan_with_5_execute_capture,
    _stub_finding_queries,
    _stub_metadata,
    cmd_transition,
)

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle_5exec')


@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry shared across cmd_capture / cmd_verify."""
    state = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'main_dirty_files': [],
        'worktree_sha': None,
        'worktree_dirty': None,
        'worktree_orphan': None,
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'unfinished_tasks_count': 2,
        'phase_steps_complete': None,
        'pending_findings_by_type': '',
        'pending_findings_blocking_count': 0,
    }

    def always(_pid, _md):
        return True

    def make_capture(name):
        def _cap(_pid, _md, _phase):
            return state[name]

        return _cap

    stubbed = [
        ('main_sha', always, make_capture('main_sha')),
        ('main_dirty', always, make_capture('main_dirty')),
        ('main_dirty_files', always, make_capture('main_dirty_files')),
        ('task_state_hash', always, make_capture('task_state_hash')),
        ('qgate_open_count', always, make_capture('qgate_open_count')),
        ('config_hash', always, make_capture('config_hash')),
        ('unfinished_tasks_count', always, make_capture('unfinished_tasks_count')),
        ('pending_findings_by_type', always, make_capture('pending_findings_by_type')),
        ('pending_findings_blocking_count', always, make_capture('pending_findings_blocking_count')),
    ]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)
    return state


def test_transition_5_execute_does_not_write_modified_files(plan_context, monkeypatch):
    """The 5-execute transition must NOT add modified_files to references.json."""
    plan_dir = plan_context.plan_dir_for('transition-no-seed')
    _seed_execute_phase_plan(plan_dir, 'transition-no-seed')
    # The end-marker guard now also covers a MAIN-CHECKOUT plan; this case is about
    # references.json, so it stubs an empty branch range rather than seeding a ledger.
    # Patch the module ``cmd_transition`` was bound from (the shared fixtures module's
    # load), not this test module's own copy — a second load is a second object.
    monkeypatch.setattr(_fixtures_lifecycle, '_branch_commit_shas', lambda _p, _b: [])

    result = cmd_transition(Namespace(plan_id='transition-no-seed', completed='5-execute'))

    assert result['status'] == 'success'
    refs = json.loads((plan_dir / 'references.json').read_text(encoding='utf-8'))
    assert 'modified_files' not in refs, (
        f'5-execute transition seeded modified_files: {refs!r}. The footprint '
        f'ledger was removed — the transition must never touch references.json '
        f'for footprint.'
    )


def test_transition_5_execute_preserves_legacy_modified_files_untouched(plan_context, monkeypatch):
    """A references.json that already carries a legacy modified_files key is
    left untouched by the transition — the transition neither reads nor
    rewrites the field.
    """
    plan_dir = plan_context.plan_dir_for('transition-legacy-untouched')
    _seed_execute_phase_plan(plan_dir, 'transition-legacy-untouched')
    monkeypatch.setattr(_fixtures_lifecycle, '_branch_commit_shas', lambda _p, _b: [])
    # Inject a legacy ledger (as an archived/pre-migration plan might carry).
    refs_path = plan_dir / 'references.json'
    legacy = json.loads(refs_path.read_text(encoding='utf-8'))
    legacy['modified_files'] = ['legacy-a.py', 'legacy-b.py']
    refs_path.write_text(json.dumps(legacy), encoding='utf-8')

    result = cmd_transition(Namespace(plan_id='transition-legacy-untouched', completed='5-execute'))

    assert result['status'] == 'success'
    refs = json.loads(refs_path.read_text(encoding='utf-8'))
    assert refs.get('modified_files') == ['legacy-a.py', 'legacy-b.py'], (
        f'Transition rewrote a legacy modified_files key: {refs!r}. The '
        f'transition must not read or mutate the field at all.'
    )


def test_transition_last_phase_sets_complete(plan_context):
    """cmd_transition must mirror cmd_archive when completing the LAST phase."""
    plan_id = 'transition-last-phase-complete'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))

    assert result['status'] == 'success'
    assert result.get('message') == 'All phases completed', f'expected terminal message, got {result}'
    assert 'next_phase' not in result, f'cmd_transition on the last phase must not return next_phase: {result}'

    live_status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert live_status['current_phase'] == 'complete', (
        f"Expected current_phase='complete' after transition --completed "
        f'6-finalize, got {live_status["current_phase"]!r}. Symmetry '
        f'with cmd_archive regressed: cmd_transition is not setting '
        f'the post-finalize sentinel for the last phase.'
    )
    assert live_status['phases'][-1]['status'] == 'done', (
        f"Expected phases[-1].status='done', got {live_status['phases'][-1]['status']!r}."
    )


def test_transition_5_execute_refuses_on_handshake_drift(plan_context, _stubbed_invariants, _stub_metadata):
    """cmd_transition refuses to advance when the captured 5-execute row drifts."""
    plan_id = 'transition-drift-5exec'
    _seed_plan_with_5_execute_capture(plan_id)

    _stubbed_invariants['main_sha'] = 'drifted-sha-xyz'
    plan_dir = plan_context.plan_dir_for(plan_id)
    status_before = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'drift', (
        f'Expected status: drift on guarded-boundary transition with drifted '
        f'capture, got {result!r}. The inline guard in cmd_transition is not '
        f'firing for 5-execute -> 6-finalize.'
    )
    assert result['phase'] == '5-execute'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'main_sha' in diff_names

    status_after = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    assert status_after['current_phase'] == status_before['current_phase'] == '5-execute', (
        'cmd_transition wrote status despite drift — the guard is not short-circuiting before write_status.'
    )
    assert status_after['phases'] == status_before['phases'], (
        'Phase status list mutated despite drift refusal — write_status fired.'
    )


def test_transition_5_execute_drift_toon_byte_equivalent(plan_context, _stubbed_invariants, _stub_metadata):
    """The dict returned by cmd_transition on drift must equal cmd_verify's dict."""
    plan_id = 'transition-drift-equiv'
    _seed_plan_with_5_execute_capture(plan_id)
    _stubbed_invariants['main_sha'] = 'drifted-sha-equiv'

    transition_result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
    verify_result = _cmds.cmd_verify(Namespace(plan_id=plan_id, phase='5-execute', strict=True))

    assert transition_result == verify_result, (
        'cmd_transition drift dict diverges from cmd_verify dict. '
        f'transition={transition_result!r} verify={verify_result!r}. '
        'The inline guard MUST return the verify result unchanged.'
    )


def test_transition_4_plan_skips_handshake_verify_on_drift(plan_context, _stubbed_invariants, _stub_metadata):
    """cmd_transition --completed 4-plan ignores handshake drift."""
    plan_id = 'transition-4plan-skip'
    _seed_plan_with_4_plan_capture(plan_id)
    # Phase-gate artifact: the 4-plan gate requires tasks or a manifest, so
    # seed one task file to isolate the drift-blindness under test from the
    # bare-transition refusal.
    plan_dir = plan_context.plan_dir_for(plan_id)
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').write_text('{"title": "seed"}', encoding='utf-8')

    _stubbed_invariants['main_sha'] = 'drifted-sha-4plan'

    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))

    assert result is not None
    assert result['status'] == 'success', (
        f'cmd_transition refused a non-guarded transition (4-plan -> '
        f'5-execute) despite drift, got {result!r}. The boundary set '
        f'_BLOCKING_BOUNDARIES MUST gate the verify call — non-guarded '
        f'transitions stay drift-blind.'
    )
    assert result['next_phase'] == '5-execute'

    status_after = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status_after['current_phase'] == '5-execute', (
        'Non-guarded transition failed to advance current_phase despite returning success — write_status did not fire.'
    )


# =============================================================================
# D2 — Finalize completion boundary asserts the blocking-findings STATE.
#
# The blocking-findings gate historically fired only when a
# `phase_handshake capture --phase 6-finalize` CALL was issued during finalize;
# a missing call left no row and raised nothing, so a plan could complete with
# actionable findings still `pending`, and "the gate never ran" was
# indistinguishable from "the gate passed". cmd_transition (completing
# 6-finalize) and cmd_archive (normal completion) now assert the STATE directly,
# armed by REACHING the completion boundary rather than by an optional call.
#
# These controls are the deliverable's proof. The NEGATIVE controls drive a
# pending actionable finding through the REAL blocking-count predicate (via
# `_stub_finding_queries`, the same seam the 5->6 boundary tests use) and assert
# the completion is REFUSED — and refused ONLY because the gate was added, so
# each fails against the pre-fix code. The POSITIVE controls confirm a clean plan
# is still admitted, and the abandonment exemption confirms the gate discriminates
# on the completion intent rather than blocking unconditionally.
# =============================================================================


def test_transition_finalize_refuses_when_actionable_finding_pending(plan_context, monkeypatch):
    """NEGATIVE control: completing 6-finalize is REFUSED while an actionable
    finding is pending. Fails against pre-fix code (no completion gate)."""
    _stub_finding_queries(monkeypatch, {'build-error': 1})
    plan_id = 'finalize-block-transition'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 1
    assert result['per_type']['build-error'] == 1
    # State unchanged: the plan is NOT marked complete.
    live = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert live['current_phase'] != 'complete', (
        'Completion boundary must not mark the plan complete while an actionable '
        'finding is pending — the gate is inert on the pre-fix code path.'
    )


def test_transition_finalize_admits_when_no_actionable_finding(plan_context, monkeypatch):
    """POSITIVE control: a clean plan (no pending actionable findings) still
    completes 6-finalize normally."""
    _stub_finding_queries(monkeypatch, {})
    plan_id = 'finalize-clean-transition'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))

    assert result['status'] == 'success'
    live = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert live['current_phase'] == 'complete'


def test_transition_finalize_admits_when_only_knowledge_finding_pending(plan_context, monkeypatch):
    """A pending KNOWLEDGE-type finding (``insight``) never blocks completion —
    the predicate is unchanged, only its arming moved to the boundary."""
    _stub_finding_queries(monkeypatch, {'insight': 9, 'tip': 4})
    plan_id = 'finalize-knowledge-transition'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))

    assert result['status'] == 'success'


# =============================================================================
# D2 — 5-execute/finalize boundary end markers.
#
# The 5-execute → 6-finalize transition is the one boundary whose end markers
# are ledger rows (one ``kind=change`` row per worktree-branch commit, written
# by the phase-5-execute Step 10a settlement). These unit pins drive
# ``_phase_end_marker_refusal`` directly with stubbed git/ledger seams, so no
# git repository is needed: the transition-level wiring (refusal leaves
# ``current_phase`` unchanged, carries no ``mailbox`` block) is pinned in
# ``test_transition_boundary_guards.py`` beside the clean-tree guard it follows.
# =============================================================================


def _execute_status_with_worktree(plan_context, plan_id: str) -> dict[str, Any]:
    """Seed an execute-phase plan and return its status with worktree metadata injected."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_execute_phase_plan(plan_dir, plan_id)
    status: dict[str, Any] = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    status['metadata'] = {'use_worktree': True, 'worktree_path': '/tmp/any-worktree'}
    return status


def test_5_execute_end_markers_refuse_unrecorded_with_payload_shape(plan_context, monkeypatch):
    """Partial recording refuses with execute_commits_unrecorded and the full payload shape."""
    plan_id = 'end-marker-5exec-unrecorded'
    status = _execute_status_with_worktree(plan_context, plan_id)
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40, 'b' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: {'a' * 40})

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)

    assert refusal is not None
    assert refusal['status'] == 'error'
    assert refusal['plan_id'] == plan_id
    assert refusal['error'] == 'execute_commits_unrecorded'
    assert refusal['phase'] == '5-execute'
    assert refusal['unrecorded_commits'] == ['b' * 40]
    assert refusal['unrecorded_count'] == 1
    assert refusal['branch_commit_count'] == 2
    assert refusal['recorded_count'] == 1
    assert refusal['message']
    assert _lifecycle.verify_blocks_transition(refusal) is True


def test_5_execute_end_markers_missing_on_zero_rows(plan_context, monkeypatch):
    """Zero recorded rows with branch commits present is wholly missing."""
    plan_id = 'end-marker-5exec-zero-rows'
    status = _execute_status_with_worktree(plan_context, plan_id)
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: set())

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)

    assert refusal is not None
    assert refusal['error'] == 'phase_end_markers_missing'
    assert refusal['recorded_count'] == 0
    assert refusal['unrecorded_commits'] == ['a' * 40]


def test_5_execute_end_markers_pass_on_full_coverage(plan_context, monkeypatch):
    """Every branch commit recorded passes (None)."""
    plan_id = 'end-marker-5exec-covered'
    status = _execute_status_with_worktree(plan_context, plan_id)
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40, 'b' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: {'a' * 40, 'b' * 40})

    assert _lifecycle._phase_end_marker_refusal(plan_id, status) is None


def test_5_execute_end_markers_pass_without_worktree_metadata(plan_context, monkeypatch):
    """A main-checkout plan with no branch work of its own carries no evidence — the gate passes.

    PLAN-LB-55 D2 put main-checkout plans under this guard. What keeps such a plan out
    of a refusal is the absence of a POSITIVE finding: an empty branch range. The empty
    range is stubbed here because the test's own checkout is a feature branch, which a
    plan that runs on the base branch never is.
    """
    plan_id = 'end-marker-5exec-no-worktree'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _seed_execute_phase_plan(plan_dir, plan_id)
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [])

    assert _lifecycle._phase_end_marker_refusal(plan_id, status) is None


# =============================================================================
# D2 — gate scoping, count shape, and seam contracts (TASK-4).
#
# Three properties the unit pins above leave open: the gate is wired ONLY
# behind ``completed == '5-execute'`` (earlier boundaries never consult the
# ledger), the wholly-missing refusal carries the same count shape as the
# partial one, and the two seams the refusal reads keep their own contracts —
# an unestablishable range and an unreadable store are unevaluable (None),
# never empty verdicts.
# =============================================================================


def test_end_marker_gate_scoped_to_5_execute_only(plan_context, _stubbed_invariants, _stub_metadata, monkeypatch):
    """A 4-plan transition with unrecorded branch commits still succeeds.

    The end-marker post-condition fires only when the completed phase IS
    5-execute: planning-phase boundaries never consult the change ledger, so
    unrecorded execute work cannot refuse a planning-phase advance. The
    worktree metadata is injected (not merely absent) so the pass is the
    scoping gate's doing, not the no-worktree pass-through's.
    """
    plan_id = 'end-marker-not-4plan'
    _seed_plan_with_4_plan_capture(plan_id)
    plan_dir = plan_context.plan_dir_for(plan_id)
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').write_text('{"title": "seed"}', encoding='utf-8')
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    status_path = plan_dir / 'status.json'
    status = json.loads(status_path.read_text(encoding='utf-8'))
    status['metadata'] = {'use_worktree': True, 'worktree_path': '/tmp/any-worktree'}
    status_path.write_text(json.dumps(status), encoding='utf-8')
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: set())

    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))

    assert result is not None
    assert result['status'] == 'success', f'The end-marker gate must not fire outside 5-execute, got {result!r}.'
    assert result['next_phase'] == '5-execute'


def test_5_execute_end_markers_missing_carries_count_shape(plan_context, monkeypatch):
    """The wholly-missing refusal enumerates the gap with counts, like the partial one."""
    plan_id = 'end-marker-5exec-missing-shape'
    status = _execute_status_with_worktree(plan_context, plan_id)
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: ['a' * 40])
    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', lambda: set())

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)

    assert refusal is not None
    assert refusal['error'] == 'phase_end_markers_missing'
    assert refusal['unrecorded_commits'] == ['a' * 40]
    assert refusal['unrecorded_count'] == 1
    assert refusal['branch_commit_count'] == 1
    assert refusal['recorded_count'] == 0


@pytest.fixture
def git_branch_repo(tmp_path: Path) -> Path:
    """A repo with one main commit and one feature-branch commit, no remote.

    No ``origin`` exists, so the range must resolve off the local base branch
    — the fallback path ``_branch_commit_shas`` takes when the remote ref is
    absent.
    """
    repo = tmp_path / 'branchrepo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'base.py').write_text('x = 1\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'base'], check=True)
    subprocess.run(['git', '-C', str(repo), 'checkout', '-q', '-b', 'feature'], check=True)
    (repo / 'work.py').write_text('y = 2\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'work'], check=True)
    return repo


def test_branch_commit_shas_falls_back_to_local_base(git_branch_repo):
    """With no origin ref, the range resolves off the local base branch."""
    head = subprocess.run(
        ['git', '-C', str(git_branch_repo), 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    shas = _lifecycle._branch_commit_shas(str(git_branch_repo), 'main')

    assert shas == [head], f'The feature-branch range must hold exactly the one feature commit, got {shas!r}.'


def test_branch_commit_shas_returns_none_when_range_unestablishable(outside_repo_dir: Path):
    """A path with no base ref yields None — unevaluable, never an empty verdict.

    Returning ``[]`` here would read as "no unrecorded work" and pass the
    gate; None passes it as "nothing was established", which is the only
    honest answer when merge-base itself failed.
    """
    plain = outside_repo_dir / 'not-a-repo'
    plain.mkdir()

    assert _lifecycle._branch_commit_shas(str(plain), 'main') is None


def test_recorded_change_shas_collects_only_change_rows(monkeypatch):
    """Only kind=change rows carrying a commit_sha contribute.

    Build rows, sha-less rows, and non-dict junk are ignored — the set is the
    deliverable-commit record, not the ledger population.
    """
    monkeypatch.setattr(
        _ledger_core,
        'read_entries',
        lambda: [
            {'kind': 'change', 'commit_sha': 'a' * 40},
            {'kind': 'build', 'commit_sha': 'b' * 40},
            {'kind': 'change'},
            {'kind': 'change', 'commit_sha': ''},
            'not-a-dict',
            {'kind': 'change', 'commit_sha': 'c' * 40},
        ],
    )

    assert _lifecycle._recorded_change_shas() == {'a' * 40, 'c' * 40}


def test_recorded_change_shas_returns_none_when_store_unreadable(monkeypatch):
    """A raising reader is unevaluable (None), never an empty store.

    The None/empty split is the contract the refusal's two codes rest on:
    None refuses as wholly-missing WITHOUT a commit list, while an empty set
    refuses as wholly-missing WITH the enumerated gap.
    """

    def _boom():
        raise OSError('ledger locked')

    monkeypatch.setattr(_ledger_core, 'read_entries', _boom)

    assert _lifecycle._recorded_change_shas() is None


def test_recorded_change_shas_returns_none_on_non_list_store(monkeypatch):
    """A store that does not read as a list is unevaluable, not empty."""
    monkeypatch.setattr(_ledger_core, 'read_entries', lambda: {'kind': 'change'})

    assert _lifecycle._recorded_change_shas() is None
