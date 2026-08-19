#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the assert-step-recorded subcommand of manage-status.

The verb is the read-only post-dispatch guard the phase-6-finalize dispatcher
calls after every dispatched-step return to detect the silent gap where a step
returns ``status: success`` but skips its mandated ``mark-step-done``
side-effect. A record counts as *recorded* iff a dict entry with a terminal
``outcome`` in ``{done, skipped, loop_back, failed}`` exists under
``status.metadata.phase_steps[phase][step]``. The verb performs zero writes.
"""


from argparse import Namespace

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_assert_step_lifecycle')


_assert_step = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_assert_step_recorded.py', '_assert_step_cmd'
)


_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_assert_step_mark_step')


_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_assert_step_core')


cmd_create = _lifecycle.cmd_create


cmd_assert_step_recorded = _assert_step.cmd_assert_step_recorded


cmd_mark_step_done = _mark_step.cmd_mark_step_done


read_status = _status_core.read_status


write_status = _status_core.write_status


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Assert Step Recorded Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _mark_args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    head_at_completion: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=False,
        display_detail=None,
        head_at_completion=head_at_completion,
        loop_back_target=None,
    )


def _assert_args(plan_id: str, phase: str, step: str, require_terminal: bool = False) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        require_terminal=require_terminal,
    )


def _seed_step(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    head_at_completion: str | None = None,
) -> None:
    """Mark a step done via the production verb (clean-worktree stubbed for may-mutate steps).

    ``head_at_completion`` is required when seeding a ``done`` record for a step
    whose doc declares ``head_dependent: true`` — the production verb refuses an
    unanchored head-dependent ``done``, so a seed without it would never write
    the record the assertion under test reads back.
    """
    cmd_mark_step_done(
        _mark_args(plan_id, phase, step, outcome, head_at_completion=head_at_completion)
    )
