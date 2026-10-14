#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the phase-completion artifact gates (PLAN-01).

``cmd_transition`` refuses bare 2-refine / 3-outline / 4-plan transitions
unless the phase artifact exists, with an explicit logged exemption for
legitimately artifact-free phases. Pins:

(a) bare 2-refine refuses with ``refine_bare_transition``;
(b) 2-refine passes with a clarified_request section;
(c) 2-refine passes with status.metadata.confidence;
(d) bare 3-outline refuses with ``outline_bare_transition``;
(e) 3-outline passes with a validating solution_outline.md;
(f) bare 4-plan refuses with ``plan_bare_transition``;
(g) 4-plan passes with a TASK file;
(h) 4-plan passes with a composed execution.toon;
(i) exemption without reason refuses with ``missing_exempt_reason``;
(j) exemption with reason succeeds, persists phase_exemptions, and is
    decision-logged.
"""

import json
from argparse import Namespace
from typing import Any

from _manage_status_transition_fixtures import cmd_create, cmd_transition, cmd_update_phase

from conftest import load_script_module

_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_query_gates')
cmd_set_phase = _query.cmd_set_phase

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle_gates')


def _seed_at_phase(plan_id: str, phase: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Phase Gate Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    order = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']
    idx = order.index(phase)
    for done_phase in order[:idx]:
        cmd_update_phase(Namespace(plan_id=plan_id, phase=done_phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase=phase))


def test_bare_2_refine_refuses(plan_context):
    plan_id = 'gate-bare-2refine'
    _seed_at_phase(plan_id, '2-refine')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='2-refine'))
    assert result['status'] == 'error'
    assert result['error'] == 'refine_bare_transition'
    assert result['phase'] == '2-refine'


def test_2_refine_passes_with_clarified_request(plan_context):
    plan_id = 'gate-2refine-clarified'
    _seed_at_phase(plan_id, '2-refine')
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'request.md').write_text(
        '# Request\n\n## Original Input\n\norig\n\n## Clarified Request\n\nclarified body\n',
        encoding='utf-8',
    )
    result = cmd_transition(Namespace(plan_id=plan_id, completed='2-refine'))
    assert result['status'] == 'success'
    assert result['next_phase'] == '3-outline'


def test_2_refine_passes_with_confidence(plan_context):
    plan_id = 'gate-2refine-confidence'
    _seed_at_phase(plan_id, '2-refine')
    plan_dir = plan_context.plan_dir_for(plan_id)
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    status.setdefault('metadata', {})['confidence'] = 82
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='2-refine'))
    assert result['status'] == 'success'


def test_bare_3_outline_refuses(plan_context):
    plan_id = 'gate-bare-3outline'
    _seed_at_phase(plan_id, '3-outline')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='3-outline'))
    assert result['status'] == 'error'
    assert result['error'] == 'outline_bare_transition'


def test_3_outline_passes_with_solution_outline(plan_context):
    plan_id = 'gate-3outline-ok'
    _seed_at_phase(plan_id, '3-outline')
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution\n\n## Deliverables\n\n### Deliverable 1\n\nBody\n',
        encoding='utf-8',
    )
    result = cmd_transition(Namespace(plan_id=plan_id, completed='3-outline'))
    assert result['status'] == 'success'
    assert result['next_phase'] == '4-plan'


def test_bare_4_plan_refuses(plan_context):
    plan_id = 'gate-bare-4plan'
    _seed_at_phase(plan_id, '4-plan')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_bare_transition'


def test_4_plan_passes_with_task_file(plan_context):
    plan_id = 'gate-4plan-task'
    _seed_at_phase(plan_id, '4-plan')
    plan_dir = plan_context.plan_dir_for(plan_id)
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').write_text('{"title": "t"}', encoding='utf-8')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'success'
    assert result['next_phase'] == '5-execute'


def test_4_plan_passes_with_manifest(plan_context):
    plan_id = 'gate-4plan-manifest'
    _seed_at_phase(plan_id, '4-plan')
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'execution.toon').write_text('manifest_version: 1\n', encoding='utf-8')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'success'


def test_exemption_without_reason_refuses(plan_context):
    plan_id = 'gate-exempt-no-reason'
    _seed_at_phase(plan_id, '2-refine')
    result = cmd_transition(
        Namespace(plan_id=plan_id, completed='2-refine', allow_bare_transition=True, bare_reason=None)
    )
    assert result['status'] == 'error'
    assert result['error'] == 'missing_exempt_reason'


def test_exemption_with_reason_persists_and_logs(plan_context):
    plan_id = 'gate-exempt-ok'
    _seed_at_phase(plan_id, '3-outline')
    result = cmd_transition(
        Namespace(
            plan_id=plan_id,
            completed='3-outline',
            allow_bare_transition=True,
            bare_reason='light-lane outline deferred to execute',
        )
    )
    assert result['status'] == 'success'
    assert result['next_phase'] == '4-plan'
    plan_dir = plan_context.plan_dir_for(plan_id)
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    exemptions = status.get('metadata', {}).get('phase_exemptions', {})
    assert exemptions.get('3-outline', {}).get('reason') == 'light-lane outline deferred to execute'
    assert 'granted_at' in exemptions['3-outline']


def test_4_plan_rejects_task_directory(plan_context):
    plan_id = 'gate-4plan-taskdir'
    _seed_at_phase(plan_id, '4-plan')
    plan_dir = plan_context.plan_dir_for(plan_id)
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').mkdir()
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_bare_transition'


def test_4_plan_rejects_manifest_directory(plan_context):
    plan_id = 'gate-4plan-manifestdir'
    _seed_at_phase(plan_id, '4-plan')
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'execution.toon').mkdir()
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_bare_transition'


# =============================================================================
# D2 — 5-execute end-marker refusal codes pin the boundary contract.
#
# The artifact gates above refuse bare planning-phase transitions at exit 0;
# the end-marker pair refuses the guarded 5-execute boundary at exit 1. These
# pins hold the pair to the same disciplines: membership in
# VERIFY_REFUSAL_ERRORS (the CLI exit-1 lockstep), a pass-through for plans
# with no worktree in play (no positive evidence, no refusal), and a payload
# that distinguishes wholly-missing from partially-unrecorded markers.
# =============================================================================


def test_end_marker_codes_are_verify_refusals():
    """All D2 codes block via verify_blocks_transition (exit-1 class, not exit-0)."""
    for code in ('phase_end_markers_missing', 'execute_commits_unrecorded', 'branch_range_unresolvable'):
        assert code in _lifecycle.VERIFY_REFUSAL_ERRORS, (
            f'{code} must be a VERIFY_REFUSAL_ERRORS member, or the end-marker guard fails open for it.'
        )
        assert _lifecycle.verify_blocks_transition({'status': 'error', 'error': code}) is True


def test_end_marker_gate_passes_without_a_worktree():
    """No worktree in play means no positive evidence — the gate passes."""
    assert _lifecycle._phase_end_marker_refusal('any-plan', {}) is None
    assert _lifecycle._phase_end_marker_refusal('any-plan', {'metadata': {'use_worktree': False}}) is None
    assert (
        _lifecycle._phase_end_marker_refusal('any-plan', {'metadata': {'use_worktree': True, 'worktree_path': ''}})
        is None
    )


# =============================================================================
# D2 — end-marker fail-closed branches (TASK-4) + unresolvable-range refusal.
#
# _phase_end_marker_refusal refuses (branch_range_unresolvable) on every
# unevaluable state WITHOUT a computable comparison, and passes (None) only
# where no comparison is owed at all: no worktree in play, no persisted path,
# or an empty range. A missing references.json (no divergence base), a
# non-string base_branch, and an unestablishable commit range each refuse —
# refusing on any of them would let unrecorded work reach finalize on a range
# nobody computed. The must-not-run stubs prove the gate returns BEFORE
# touching the seam on each refused branch — the refusal is structural, not
# an accident of stubbed-empty data.
#
# An UNESTABLISHABLE commit range is in that refused set: since TASK-24 it refuses
# fail-closed as ``branch_range_unresolvable`` (no comparison to run, so entry
# without it is the silent skip). Its test below pins the refusal shape, the
# omitted commit list, and the CLI exit-1 lockstep.
# =============================================================================


def _seed_worktree_status(plan_context, plan_id: str) -> dict:
    """Create a plan through the production create verb and inject worktree metadata."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='End Marker Pass-Through Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    status: dict[str, Any] = json.loads(
        (plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8')
    )
    status['metadata'] = {'use_worktree': True, 'worktree_path': '/tmp/any-worktree'}
    return status


def test_end_marker_gate_refuses_without_references_file(plan_context, monkeypatch):
    """A plan with no references.json carries no divergence base — the gate
    refuses fail-closed: without a base no range is enumerable, so recording
    cannot be proven."""
    plan_id = 'end-marker-no-refs'
    status = _seed_worktree_status(plan_context, plan_id)
    (plan_context.plan_dir_for(plan_id) / 'references.json').unlink(missing_ok=True)

    def _must_not_run(_p, _b):
        raise AssertionError('the commit range must not be computed without a divergence base')

    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', _must_not_run)

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)
    assert refusal is not None
    assert refusal['status'] == 'error'
    assert refusal['error'] == 'branch_range_unresolvable'


def test_end_marker_gate_refuses_on_non_string_base_branch(plan_context, monkeypatch):
    """A non-string base_branch is no base at all — the gate refuses fail-closed."""
    plan_id = 'end-marker-bad-base'
    status = _seed_worktree_status(plan_context, plan_id)
    (plan_context.plan_dir_for(plan_id) / 'references.json').write_text(
        json.dumps({'base_branch': 123}), encoding='utf-8'
    )

    def _must_not_run(_p, _b):
        raise AssertionError('the commit range must not be computed off a non-string base')

    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', _must_not_run)

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)
    assert refusal is not None
    assert refusal['status'] == 'error'
    assert refusal['error'] == 'branch_range_unresolvable'


def test_end_marker_gate_refuses_when_commit_range_unestablishable(plan_context, monkeypatch):
    """An unestablished range refuses fail-closed — entry without the comparison is the skip."""
    plan_id = 'end-marker-no-range'
    status = _seed_worktree_status(plan_context, plan_id)
    (plan_context.plan_dir_for(plan_id) / 'references.json').write_text(
        json.dumps({'base_branch': 'main'}), encoding='utf-8'
    )
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: None)

    def _must_not_run():
        raise AssertionError('the ledger must not be read when no range was established')

    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', _must_not_run)

    refusal = _lifecycle._phase_end_marker_refusal(plan_id, status)

    assert refusal is not None
    assert refusal['error'] == 'branch_range_unresolvable', (
        f'An unestablished range must refuse, not pass through; got {refusal!r}.'
    )
    assert 'unrecorded_commits' not in refusal, (
        f'A range that was never computed must publish no commit list at all; got {refusal!r}.'
    )
    assert refusal['base_branch'] == 'main'
    assert refusal['reason'], 'the refusal must name why the git side went unread'
    assert refusal['message'], 'the refusal must carry a human-readable message'
    assert _lifecycle.verify_blocks_transition(refusal) is True


def test_end_marker_gate_passes_on_empty_branch_range(plan_context, monkeypatch):
    """Zero branch commits means zero unrecorded work — the gate passes unread."""
    plan_id = 'end-marker-empty-range'
    status = _seed_worktree_status(plan_context, plan_id)
    (plan_context.plan_dir_for(plan_id) / 'references.json').write_text(
        json.dumps({'base_branch': 'main'}), encoding='utf-8'
    )
    monkeypatch.setattr(_lifecycle, '_branch_commit_shas', lambda _p, _b: [])

    def _must_not_run():
        raise AssertionError('the ledger must not be read for an empty range')

    monkeypatch.setattr(_lifecycle, '_recorded_change_shas', _must_not_run)

    assert _lifecycle._phase_end_marker_refusal(plan_id, status) is None
