#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``refire-report`` subcommand of manage-execution-manifest.py.

A finalize step can fire many times in one run: the dispatcher's HEAD-advance
re-entry check re-fires every head-dependent step whose recorded SHA is
superseded, and each of the pipeline's HEAD-advancing events supersedes every
verdict recorded before it. Reducing that count needs an instrument that can
count it, and the instrument must not be a new emitter — ``record-step`` already
appends one ``execution_log[]`` row per firing, for dispatched AND inline steps
alike. This verb derives the count from those existing rows.

These tests pin the derivation and, just as importantly, its two coverage
boundaries:

- ``refires`` is ``max(0, firings - 1)`` per step, so a step that fired once
  reports zero re-fires and a step that fired seven reports six;
- a ``skipped`` row is counted separately and NEVER folded into ``firings`` — a
  skip is precisely the outcome a preserved verdict produces, so folding it in
  would make the instrument unable to measure the thing it exists to measure;
- the token column is a FLOOR (an inline step's caller omits the flags, and the
  writer records that omission as the ``unmeasured`` token), and the payload
  carries a ``token_population`` field saying so — plus per-state
  ``unmeasured_columns`` / ``unrecognised_columns`` counts that SIZE the floor —
  rather than presenting a bare number that merely looks comparable;
- ``--phase`` restricts the derivation, so a finalize figure is not inflated by
  phase-5 rows;
- rows are ordered worst-offender-first so the report reads as a diagnosis.
"""

from argparse import Namespace

import pytest

from conftest import get_script_path, load_script_module, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')


_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_refire_script'
)
cmd_compose = _mem.cmd_compose
cmd_record_step = _mem.cmd_record_step
cmd_refire_report = _mem.cmd_refire_report
summarize_refires = _mem.summarize_refires
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log writes so tests don't depend on a
# running executor / a resolvable plan log dir.
_mem._log_decision = lambda *a, **kw: None
_mem._log_record_step = lambda *a, **kw: None


# =============================================================================
# Namespace helpers
# =============================================================================


def _compose_ns(plan_id: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=5,
        phase_5_steps='quality-gate,module-tests',
        phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
        commit_and_push=None,
    )


def _record_ns(
    plan_id: str,
    step_id: str,
    phase: str = '6-finalize',
    outcome: str = 'executed',
    total_tokens: int = 0,
    tool_uses: int = 0,
    duration_ms: int = 0,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        step_id=step_id,
        phase=phase,
        outcome=outcome,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
    )


def _report_ns(plan_id: str, phase: str | None = '6-finalize') -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase)


def _row(step_id: str, phase: str = '6-finalize', outcome: str = 'executed', **kw) -> dict:
    return {
        'step_id': step_id,
        'phase': phase,
        'outcome': outcome,
        'total_tokens': kw.get('total_tokens', 0),
        'tool_uses': kw.get('tool_uses', 0),
        'duration_ms': kw.get('duration_ms', 0),
        'timestamp': '2026-01-01T00:00:00+00:00',
    }
