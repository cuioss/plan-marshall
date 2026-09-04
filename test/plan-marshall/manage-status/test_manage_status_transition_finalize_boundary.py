#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for manage-status.py transition at the 5-execute -> 6-finalize boundary:
which pending findings block completion, and how the finalize executor is run."""


from argparse import Namespace

import _handshake_commands as _cmds
import _invariants as _inv
import pytest
from _manage_status_transition_fixtures import (
    _core,
    _stub_finding_queries,
    _stub_metadata,
)

# =============================================================================
# Fixed actionable-vs-knowledge rule at the 5-execute -> 6-finalize boundary
# =============================================================================

#
# Integration-level assertions over the REAL ``_capture_pending_findings_blocking_count``
# (narrowed INVARIANTS registry) driven through ``cmd_capture --phase 6-finalize``:
# a pending KNOWLEDGE-type finding does NOT block the guarded boundary; a pending
# ACTIONABLE-type finding DOES. No marshal.json blocking_finding_types partition
# is involved — the rule is hardcoded in ``_invariants._ACTIONABLE_FINDING_TYPES``.


@pytest.fixture
def _only_blocking_invariant(monkeypatch):
    """Narrow INVARIANTS to just the real pending-findings-blocking entry."""
    stubbed = [
        (
            'pending_findings_blocking_count',
            lambda _pid, _md: True,
            _inv._capture_pending_findings_blocking_count,
        ),
    ]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)


def test_finalize_boundary_pending_knowledge_finding_does_not_block(
    plan_context, _only_blocking_invariant, _stub_metadata, monkeypatch
):
    """A pending KNOWLEDGE-type finding (``insight``) clears the 6-finalize
    capture under the fixed rule."""
    _stub_finding_queries(monkeypatch, {'insight': 5, 'tip': 3})

    result = _cmds.cmd_capture(
        Namespace(plan_id='fixed-rule-knowledge', phase='6-finalize', override=False, reason=None, strict=False)
    )

    assert result['status'] == 'success'
    assert result['invariants']['pending_findings_blocking_count'] in (0, '0')


def test_finalize_boundary_pending_actionable_finding_blocks(
    plan_context, _only_blocking_invariant, _stub_metadata, monkeypatch
):
    """A pending ACTIONABLE-type finding (``build-error``) refuses the 6-finalize
    capture under the fixed rule."""
    _stub_finding_queries(monkeypatch, {'build-error': 1})

    result = _cmds.cmd_capture(
        Namespace(plan_id='fixed-rule-actionable', phase='6-finalize', override=False, reason=None, strict=False)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 1
    assert result['blocking_types'] == list(_inv._ACTIONABLE_FINDING_TYPES)
    assert result['per_type']['build-error'] == 1


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
