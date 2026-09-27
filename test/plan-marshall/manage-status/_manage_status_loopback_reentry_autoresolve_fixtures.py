#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the loop-back handshake drift auto-resolution.

A loop-back (``cmd_set_phase`` backward move) structurally guarantees
handshake drift at the next guarded boundary: the re-entered phases
legitimately change the invariants the earlier capture recorded. The
auto-resolution contract, proven here:

(a) a backward ``set-phase`` persists ``metadata.loop_back_reentry``
    (``from_phase`` / ``to_phase`` / ``at``) alongside the phase write;
(b) ``cmd_transition`` with invariant drift AND the marker present
    auto-re-captures the handshake (row replaced with ``override=true``
    and the recorded reason), clears the marker, and advances the phase;
(c) drift WITHOUT the marker keeps today's blocking behavior unchanged;
(d) a forward ``set-phase`` writes no marker;
(e) ``cmd_archive`` is the SECOND consumption point for the SAME marker — a plan
    archived while a re-entry is still open never reaches a guarded boundary at
    all, so archive clears the marker and records
    ``metadata.loop_back_reentry_outcome`` stating that the re-entry ended
    without completing, with a matched control proving that outcome record is not
    written unconditionally.

Cases (b) and (c) are the two PRE-EXISTING transition-boundary consumptions, and
they are asserted here unchanged: adding the archive point must leave both of them
behaving exactly as before.

The companion implementation lives in ``_status_query.py``
(``cmd_set_phase`` marker persistence) and ``_cmd_lifecycle.py``
(``_loop_back_auto_override``, consumed by ``cmd_transition``'s
blocking-boundary guard, and the marker consumption folded into
``cmd_archive``'s phase-closing write).
"""

import json
import sys
from argparse import Namespace
from pathlib import Path

# PLAIN imports, deliberately — see the MODULE IDENTITY note below.
import _handshake_commands as _cmds
import _handshake_store as _store
import _invariants as _inv
import pytest

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle_loopback')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_query_loopback')

cmd_archive = _lifecycle.cmd_archive
cmd_create = _lifecycle.cmd_create
cmd_transition = _lifecycle.cmd_transition
cmd_set_phase = _query.cmd_set_phase


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry so drift can be induced by mutating a
    single state value between capture and transition."""
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
    """Replace ``_load_status_metadata`` so cmd_verify's / cmd_capture's own
    worktree assertion stays out of the way — the marker is read from the
    status dict directly, independent of this stub."""
    md: dict = {}
    monkeypatch.setattr(_cmds, '_load_status_metadata', lambda _pid: md)
    return md


def _seed_plan(plan_context, plan_id: str, metadata: dict | None = None) -> Path:
    """Create a plan at 5-execute with a captured handshake row. Returns the
    plan's status.json path."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-Back Auto-Resolve Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        _query.cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    _query.cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))

    status_path: Path = plan_context.plan_dir_for(plan_id) / 'status.json'
    if metadata is not None:
        status = json.loads(status_path.read_text(encoding='utf-8'))
        status['metadata'] = metadata
        status_path.write_text(json.dumps(status), encoding='utf-8')

    _cmds.cmd_capture(Namespace(plan_id=plan_id, phase='5-execute', override=False, reason=None, strict=False))
    return status_path


def _read_status(status_path: Path) -> dict:
    status: dict = json.loads(status_path.read_text(encoding='utf-8'))
    return status


def _is_true(value) -> bool:
    """Tolerate TOON round-trip bool spellings on stored handshake rows."""
    return value is True or str(value).strip().lower() == 'true'
