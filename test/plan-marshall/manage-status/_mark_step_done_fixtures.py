#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``mark step done`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from argparse import Namespace

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_mark_step_lifecycle')


_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_mark_step_cmd')


_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_mark_step_core')


cmd_create = _lifecycle.cmd_create


cmd_mark_step_done = _mark_step.cmd_mark_step_done


read_status = _status_core.read_status


write_status = _status_core.write_status


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Mark Step Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
    fact: list[str] | None = None,
) -> Namespace:
    """Build the mark-step-done Namespace.

    ``fact`` mirrors the CLI's ``action='append'`` accumulation: a list of raw
    ``KEY=VALUE`` tokens, or ``None`` when the caller passed no ``--fact`` at all.
    """
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=force,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
        loop_back_target=loop_back_target,
        fact=fact,
    )
