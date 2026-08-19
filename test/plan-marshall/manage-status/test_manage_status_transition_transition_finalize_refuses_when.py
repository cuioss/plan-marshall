#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back.

Split from test_manage_status.py: covers cmd_transition (incl. inline
strict-verify guard for guarded boundaries, and last-phase symmetry with
cmd_archive), cmd_archive (incl. --reason flag), cmd_delete_plan (incl. the main-anchored
lesson carry-back, its five-value ``lesson_carry_back_action`` and that
vocabulary's stated relationship to ``_lessons_query.RESTORE_ACTIONS``, and the
veto that refuses the deletion when a carried lesson did not land), cmd_list (incl.
worktree moved-in plan discovery), cmd_list_orphans, and cmd_mark_step_done
loop-back target validation.
"""


import json
from argparse import Namespace

from _manage_status_transition_fixtures import (
    _core,
    _seed_finalize_phase_plan,
    _stub_finding_queries,
    cmd_archive,
    cmd_transition,
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


def test_archive_refuses_when_actionable_finding_pending(plan_context, monkeypatch):
    """NEGATIVE control: a normal-completion archive (no --reason) is REFUSED
    while an actionable finding is pending, and the plan dir is NOT moved."""
    _stub_finding_queries(monkeypatch, {'sonar-issue': 2})
    plan_id = 'finalize-block-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 2
    assert result['per_type']['sonar-issue'] == 2
    # The plan directory survives — no move happened.
    assert plan_context.plan_dir_for(plan_id).exists()
    assert 'archived_to' not in result


def test_archive_admits_when_no_actionable_finding(plan_context, monkeypatch):
    """POSITIVE control: a clean normal-completion archive proceeds."""
    _stub_finding_queries(monkeypatch, {})
    plan_id = 'finalize-clean-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result['status'] == 'success'
    assert 'archived_to' in result


def test_archive_with_reason_bypasses_findings_gate(plan_context, monkeypatch):
    """A DELIBERATE archive (--reason present, e.g. abandonment) is exempt from
    the completion gate: it archives even with a pending actionable finding, so a
    low-confidence / abandoned plan is never stranded behind its own findings.
    Confirms the gate discriminates on the completion intent."""
    _stub_finding_queries(monkeypatch, {'build-error': 3})
    plan_id = 'finalize-abandon-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence'))

    assert result['status'] == 'success', (
        'A --reason archive is a deliberate abandonment and must not be blocked '
        'by pending findings.'
    )
    assert 'archived_to' in result


def test_archive_dry_run_does_not_fire_findings_gate(plan_context, monkeypatch):
    """A dry-run archive returns before the gate — it makes no state change, so a
    pending finding must not turn a preview into a refusal."""
    _stub_finding_queries(monkeypatch, {'build-error': 1})
    plan_id = 'finalize-dryrun-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=True, reason=None))

    assert result['status'] == 'success'
    assert result.get('dry_run') is True
    assert 'would_archive_to' in result


def test_archive_of_already_complete_plan_not_blocked_by_pending_finding(plan_context, monkeypatch):
    """The cleanup pass archives already-`complete` plans (no --reason). A stale
    pending record on such a plan must NOT wedge cleanup — the completion gate
    fires only while the plan is actively in 6-finalize, not after it completed.
    This is exactly the pre-D3 residue (a permanently-pending qgate record) whose
    cleanup a broad gate would have blocked."""
    _stub_finding_queries(monkeypatch, {})  # clean, so the plan can complete
    plan_id = 'finalize-cleanup-complete'
    _seed_finalize_phase_plan(plan_id)
    # Complete it normally (clean) → current_phase becomes 'complete'.
    done = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))
    assert done['status'] == 'success'

    # A stale pending actionable record now appears (the pre-D3 residue).
    _stub_finding_queries(monkeypatch, {'build-error': 1})

    # The cleanup archive (no --reason) of the already-complete plan must proceed.
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', (
        'A cleanup archive of an already-complete plan must not be blocked by a '
        'stale pending finding — the completion gate fires only while in 6-finalize.'
    )
    assert 'archived_to' in result


def test_run_executor_skips_when_executor_absent(monkeypatch, tmp_path):
    """_run_executor is a no-op (no subprocess) when the executor is not on disk."""
    missing = tmp_path / 'execute-script.py'  # deliberately not created
    monkeypatch.setattr(_core, 'get_executor_path', lambda: missing)
    spawned = []
    monkeypatch.setattr(_core.subprocess, 'run', lambda *a, **k: spawned.append(a))

    _core._run_executor('plan-marshall:platform-runtime:platform_runtime', 'session', 'bind', '--plan-id', 'x')

    assert spawned == [], 'an absent executor must skip the subprocess spawn entirely'


def test_run_executor_spawns_when_executor_present(monkeypatch, tmp_path):
    """_run_executor spawns the executor subprocess when the script exists on disk."""
    present = tmp_path / 'execute-script.py'
    present.write_text('# stub executor\n', encoding='utf-8')
    monkeypatch.setattr(_core, 'get_executor_path', lambda: present)
    captured = []
    monkeypatch.setattr(_core.subprocess, 'run', lambda cmd, **k: captured.append(cmd))

    _core._run_executor(
        'plan-marshall:platform-runtime:platform_runtime', 'session', 'push-title-token', '--plan-id', 'x'
    )

    assert len(captured) == 1, f'exactly one spawn expected, got {captured!r}'
    cmd = captured[0]
    assert str(present) in cmd
    assert cmd[-4:] == ['session', 'push-title-token', '--plan-id', 'x']


def test_run_executor_swallows_subprocess_oserror(monkeypatch, tmp_path):
    """A subprocess OSError is swallowed — _run_executor never propagates."""
    present = tmp_path / 'execute-script.py'
    present.write_text('# stub executor\n', encoding='utf-8')
    monkeypatch.setattr(_core, 'get_executor_path', lambda: present)

    def _explode(*_a, **_k):
        raise OSError('simulated spawn failure')

    monkeypatch.setattr(_core.subprocess, 'run', _explode)

    # Must NOT raise.
    _core._run_executor('plan-marshall:platform-runtime:platform_runtime', 'session', 'bind', '--plan-id', 'x')
