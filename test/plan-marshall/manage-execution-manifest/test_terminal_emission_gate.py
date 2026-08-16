#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the terminal-emission orchestration gate (plan 302 D2).

``default:emit-landing`` writes the run's ``kind: landing`` message to the
governing epic's inbox, and a non-orchestrated plan has no epic inbox. The
compose-time gate ``_apply_terminal_emission_orchestration_gate`` therefore drops
the step from a non-orchestrated plan as an OBSERVABLE decision — the drop is
visible in the compose result and logged — never a silent runtime no-op that
would leave a dead step in the manifest.

The verification the plan demands (D2): compose a non-orchestrated plan and read
that the step is ABSENT and WHY. Both the direct-function level and the end-to-end
``cmd_compose`` level are pinned, plus the positive control (an orchestrated plan
KEEPS the step) so the gate is not a vacuous always-drop.

Orchestration is classified through the single sanctioned detector
(``_orchestrator_inbox.classify_source_id``) over the ``source_id`` pointer
``phase-1-init`` persists — this test verifies no second detector was introduced by
driving the gate through real ``request.md`` files.
"""

from __future__ import annotations

from pathlib import Path

from argparse import Namespace
from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_gate_script'
)
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
_apply_gate = _mem._apply_terminal_emission_orchestration_gate
_TERMINAL_EMISSION_STEP = _mem._TERMINAL_EMISSION_STEP

# Quiet the best-effort decision-log subprocess.
_mem._log_decision = lambda *a, **kw: None

#: A settled orchestrator plan-spec pointer that classify_source_id accepts.
_ORCHESTRATED_POINTER = '.plan/local/orchestrator/truthful-signals/plans/PLAN-55-inbox.md'


def _write_request(plan_dir: Path, *, source: str, source_id: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        f'# Request: {plan_dir.name}\n\n'
        f'source: {source}\n'
        f'source_id: {source_id}\n'
        'created: 2026-06-30T00:00:00Z\n\n'
        '## Original Input\n\n'
        'do the thing\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _candidates() -> list[str]:
    # A minimal candidate list carrying the terminal step plus a neighbour, so the
    # gate's drop is observable against a surviving step.
    return ['record-metrics', _TERMINAL_EMISSION_STEP, 'archive-plan']


# =============================================================================
# Direct-function level
# =============================================================================


class TestGateFunction:
    def test_orchestrated_plan_keeps_the_terminal_step(self, plan_context):
        plan_id = 'gate-orchestrated'
        _write_request(
            plan_context.plan_dir_for(plan_id), source='orchestrator', source_id=_ORCHESTRATED_POINTER
        )

        kept, dropped = _apply_gate(_candidates(), plan_id)

        assert _TERMINAL_EMISSION_STEP in kept
        assert dropped == []

    def test_non_orchestrated_plan_drops_the_terminal_step_with_a_reason(self, plan_context):
        plan_id = 'gate-non-orchestrated'
        _write_request(plan_context.plan_dir_for(plan_id), source='description', source_id='none')

        kept, dropped = _apply_gate(_candidates(), plan_id)

        # The step is ABSENT ...
        assert _TERMINAL_EMISSION_STEP not in kept
        # ... its neighbours survive (the gate narrows, never rewrites) ...
        assert 'record-metrics' in kept
        assert 'archive-plan' in kept
        # ... and the drop is reported as a {step, reason} record naming WHY.
        assert len(dropped) == 1
        assert dropped[0]['step'] == _TERMINAL_EMISSION_STEP
        assert 'not orchestrated' in dropped[0]['reason']
        assert 'detection=' in dropped[0]['reason']

    def test_gate_is_a_no_op_when_the_step_is_absent(self, plan_context):
        plan_id = 'gate-absent'
        _write_request(plan_context.plan_dir_for(plan_id), source='description', source_id='none')

        candidates = ['record-metrics', 'archive-plan']
        kept, dropped = _apply_gate(candidates, plan_id)

        assert kept == candidates
        assert dropped == []


# =============================================================================
# End-to-end through cmd_compose — the D2 verification the plan names
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
        # Explicit CSV carrying the terminal step — it is default-on via discovery
        # but deliberately absent from the DEFAULT_PHASE_6_STEPS fallback, so the
        # test seeds it directly to exercise the gate.
        phase_6_steps=','.join(_candidates()),
        commit_and_push=None,
    )


class TestGateThroughCompose:
    def test_non_orchestrated_compose_emits_the_step_out_observably(self, plan_context):
        plan_id = 'compose-non-orchestrated'
        _write_request(plan_context.plan_dir_for(plan_id), source='description', source_id='none')

        result = cmd_compose(_compose_ns(plan_id))

        assert result is not None and result['status'] == 'success'
        # Absent from the composed manifest written to disk ...
        manifest = read_manifest(plan_id)
        assert _TERMINAL_EMISSION_STEP not in manifest['phase_6']['steps']
        # ... and the drop is surfaced in the compose result (observable), not silent.
        assert result['terminal_emission_dropped'] == [_TERMINAL_EMISSION_STEP]

    def test_orchestrated_compose_keeps_the_step(self, plan_context):
        plan_id = 'compose-orchestrated'
        _write_request(
            plan_context.plan_dir_for(plan_id), source='orchestrator', source_id=_ORCHESTRATED_POINTER
        )

        result = cmd_compose(_compose_ns(plan_id))

        assert result is not None and result['status'] == 'success'
        manifest = read_manifest(plan_id)
        assert _TERMINAL_EMISSION_STEP in manifest['phase_6']['steps']
        assert result['terminal_emission_dropped'] == []
