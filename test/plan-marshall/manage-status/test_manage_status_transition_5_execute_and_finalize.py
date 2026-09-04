#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for manage-status.py transition: the 5-execute phase and the final-phase complete transition.

Its one section: D2 — Finalize completion boundary asserts the blocking-findings STATE.
"""


import json
from argparse import Namespace

import _handshake_commands as _cmds
import _invariants as _inv
import pytest
from _manage_status_transition_fixtures import (
    _seed_execute_phase_plan,
    _seed_finalize_phase_plan,
    _seed_plan_with_4_plan_capture,
    _seed_plan_with_5_execute_capture,
    _stub_finding_queries,
    _stub_metadata,
    cmd_transition,
)


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


def test_transition_5_execute_does_not_write_modified_files(plan_context):
    """The 5-execute transition must NOT add modified_files to references.json."""
    plan_dir = plan_context.plan_dir_for('transition-no-seed')
    _seed_execute_phase_plan(plan_dir, 'transition-no-seed')

    result = cmd_transition(Namespace(plan_id='transition-no-seed', completed='5-execute'))

    assert result['status'] == 'success'
    refs = json.loads((plan_dir / 'references.json').read_text(encoding='utf-8'))
    assert 'modified_files' not in refs, (
        f'5-execute transition seeded modified_files: {refs!r}. The footprint '
        f'ledger was removed — the transition must never touch references.json '
        f'for footprint.'
    )


def test_transition_5_execute_preserves_legacy_modified_files_untouched(plan_context):
    """A references.json that already carries a legacy modified_files key is
    left untouched by the transition — the transition neither reads nor
    rewrites the field.
    """
    plan_dir = plan_context.plan_dir_for('transition-legacy-untouched')
    _seed_execute_phase_plan(plan_dir, 'transition-legacy-untouched')
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
    assert result.get('message') == 'All phases completed', (
        f'expected terminal message, got {result}'
    )
    assert 'next_phase' not in result, (
        f'cmd_transition on the last phase must not return next_phase: {result}'
    )

    live_status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert live_status['current_phase'] == 'complete', (
        f"Expected current_phase='complete' after transition --completed "
        f'6-finalize, got {live_status["current_phase"]!r}. Symmetry '
        f'with cmd_archive regressed: cmd_transition is not setting '
        f'the post-finalize sentinel for the last phase.'
    )
    assert live_status['phases'][-1]['status'] == 'done', (
        f"Expected phases[-1].status='done', got "
        f'{live_status["phases"][-1]["status"]!r}.'
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
        'cmd_transition wrote status despite drift — the guard is not '
        'short-circuiting before write_status.'
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
    verify_result = _cmds.cmd_verify(
        Namespace(plan_id=plan_id, phase='5-execute', strict=True)
    )

    assert transition_result == verify_result, (
        'cmd_transition drift dict diverges from cmd_verify dict. '
        f'transition={transition_result!r} verify={verify_result!r}. '
        'The inline guard MUST return the verify result unchanged.'
    )


def test_transition_4_plan_skips_handshake_verify_on_drift(plan_context, _stubbed_invariants, _stub_metadata):
    """cmd_transition --completed 4-plan ignores handshake drift."""
    plan_id = 'transition-4plan-skip'
    _seed_plan_with_4_plan_capture(plan_id)

    _stubbed_invariants['main_sha'] = 'drifted-sha-4plan'

    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))

    assert result is not None
    assert result['status'] == 'success', (
        f'cmd_transition refused a non-guarded transition (4-plan -> '
        f'5-execute) despite drift, got {result!r}. The boundary set '
        f"_BLOCKING_BOUNDARIES MUST gate the verify call — non-guarded "
        f'transitions stay drift-blind.'
    )
    assert result['next_phase'] == '5-execute'

    status_after = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status_after['current_phase'] == '5-execute', (
        'Non-guarded transition failed to advance current_phase despite '
        'returning success — write_status did not fire.'
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
