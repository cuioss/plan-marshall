#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``ledger reconciliation`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Cross-ledger reconciliation: a disagreement becomes a finding, not a silent choice.

The two row ledgers — `execution.toon`'s `execution_log[]` and each phase's
`work/metrics-dispatch-boundaries-{phase}.toon` — are written by independent
call sites with no shared transaction and no shared key, so a dispatch can land
in one and not the other in BOTH directions. Nothing previously reconciled them,
and nothing told a reader that only their union counts every dispatch.

These tests pin that the reconciliation emits one finding per divergent row in
each direction, that the two partiality shapes are labelled DISTINCTLY (a phase
whose boundary never closed versus a row with no partner), that a re-entered
phase is called out as its own shape, and that a structurally-impossible absence
is declared rather than reported. Each includes a negative control, because a
reconciliation that fires on agreement is worse than none.
"""


import importlib.util
from datetime import datetime

from _manage_metrics_fixtures import (
    ns,
)
from toon_parser import serialize_toon

from conftest import get_script_path, load_script_module

_spec = importlib.util.spec_from_file_location(
    'manage_metrics_reconcile', get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
)


assert _spec is not None and _spec.loader is not None


manage_metrics = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(manage_metrics)


cmd_start_phase = manage_metrics.cmd_start_phase


cmd_end_phase = manage_metrics.cmd_end_phase


cmd_record_dispatch_boundary = manage_metrics.cmd_record_dispatch_boundary


cmd_reconcile_ledgers = manage_metrics.cmd_reconcile_ledgers


_ledger = load_script_module(
    'plan-marshall', 'manage-metrics', '_ledger_reconciliation.py', 'ledger_reconciliation_mod'
)


def _ns_reconcile(plan_id: str, window_seconds: int | None = None):
    argv = ['reconcile-ledgers', '--plan-id', plan_id]
    if window_seconds is not None:
        argv += ['--window-seconds', str(window_seconds)]
    return ns(*argv)


def _write_execution_log(plan_context, plan_id: str, rows: list[tuple[str, str, str, int]]) -> None:
    """Write an `execution.toon` holding the given `execution_log[]` rows.

    Each row is `(step_id, phase, timestamp, total_tokens)`. Serialized through
    the PRODUCTION `serialize_toon`, so the reconciliation is exercised against
    the tabular `execution_log[N]{cols}:` bytes the manifest writer actually
    produces. A hand-written shape would let these tests pass against a form
    nothing emits — and the first draft of this helper did exactly that, guessing
    a dotted `execution_log.0.step_id` layout the writer never emits.

    An empty row list writes a manifest carrying no `execution_log` key at all:
    that is the readable-but-empty state, which the reconciliation must
    distinguish from an unreadable manifest.
    """
    manifest: dict = {'plan_id': plan_id}
    if rows:
        manifest['execution_log'] = [
            {
                'step_id': step_id,
                'phase': phase,
                'outcome': 'executed',
                'total_tokens': total_tokens,
                'tool_uses': 0,
                'duration_ms': 0,
                'timestamp': timestamp,
            }
            for step_id, phase, timestamp, total_tokens in rows
        ]
    plan_dir = plan_context.plan_dir_for(plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'execution.toon').write_text(serialize_toon(manifest), encoding='utf-8')


def _boundary_timestamps(plan_context, plan_id: str, phase: str) -> list[str]:
    path = plan_context.plan_dir_for(plan_id) / 'work' / f'metrics-dispatch-boundaries-{phase}.toon'
    return [
        line.split(',', 1)[0].strip()
        for line in path.read_text(encoding='utf-8').splitlines()
        if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
    ]


def _parse_stamp(raw: str) -> datetime:
    """Parse a recorded ISO timestamp, tolerating the writer's `Z` suffix."""
    return datetime.fromisoformat(raw.strip().replace('Z', '+00:00'))


def _findings_of(result: dict, kind: str) -> list[dict]:
    return [finding for finding in result['findings'] if finding['finding'] == kind]
