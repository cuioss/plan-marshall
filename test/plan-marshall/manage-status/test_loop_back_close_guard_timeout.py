#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``loop-back close`` when the status guard times out at the waiver stamp.

The step is recorded ``done`` before the waivers are stamped, so a guard that
cannot be taken at the stamp is an incomplete close, not a refusal and not an
exception: the return names every requested waiver as not landed, and the
step's ``done`` record stays.
"""

from __future__ import annotations

from argparse import Namespace
from typing import Any, cast

from _mark_step_done_fixtures import _tmp_repo_two_heads

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_close_timeout_lifecycle')
_loop_back = load_script_module('plan-marshall', 'manage-status', '_cmd_loop_back.py', '_close_timeout_cmd')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_close_timeout_status_core')

_PHASE = '6-finalize'
_STEP = 'pre-submission-self-review'
_WAIVED_STEPS = ['pre-push-quality-gate', 'push']
_TIMEOUT_TEXT = 'could not acquire coordination guard status.json.lock within 30.0s'


def _step_records(plan_id: str) -> dict[str, Any]:
    steps = _status_core.read_status(plan_id).get('metadata', {}).get('phase_steps', {}).get(_PHASE, {})
    return cast(dict[str, Any], steps)


def test_a_guard_timeout_at_the_waiver_stamp_is_an_incomplete_close(plan_context, tmp_path, monkeypatch):
    """The close returns close_incomplete naming each waiver, and the step stays done."""
    plan_id = 'loop-back-close-guard-timeout'
    _lifecycle.cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-back Close Guard Timeout Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    closing_head, completed_at = _tmp_repo_two_heads(tmp_path, monkeypatch)
    for name in _WAIVED_STEPS:
        marked = _loop_back.cmd_mark_step_done(
            Namespace(
                plan_id=plan_id,
                phase=_PHASE,
                step=name,
                outcome='done',
                display_detail=f'{name} completed',
                head_at_completion=completed_at,
                loop_back_target=None,
                fact=None,
                force=False,
                no_completion_log=False,
            )
        )
        assert marked is not None and marked['status'] == 'success', marked

    def _guard_never_frees(path: Any, mutate: Any) -> Any:
        raise TimeoutError(_TIMEOUT_TEXT)

    # Only the waiver stamp goes through this module's binding; the mark that
    # records the step done commits through its own.
    monkeypatch.setattr(_loop_back, 'rmw_json', _guard_never_frees)

    result = _loop_back.cmd_loop_back_close(
        Namespace(
            plan_id=plan_id,
            step=_STEP,
            head=closing_head,
            rationale='the operator closes with the re-fires waived',
            accept=None,
            waive_refire=_WAIVED_STEPS,
        )
    )

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'close_incomplete'
    assert result['outcome'] == 'done'
    assert result['waived_steps'] == []
    refusals = result['waiver_refusals']
    assert len(refusals) == len(_WAIVED_STEPS)
    for name, refusal in zip(_WAIVED_STEPS, refusals, strict=True):
        assert repr(name) in refusal
        assert _TIMEOUT_TEXT in refusal

    records = _step_records(plan_id)
    assert records[_STEP]['outcome'] == 'done'
    assert records[_STEP]['head_at_completion'] == closing_head
    for name in _WAIVED_STEPS:
        assert 'refire_waiver' not in records[name]
