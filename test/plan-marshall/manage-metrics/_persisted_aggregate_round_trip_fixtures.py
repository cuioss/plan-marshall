#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``persisted aggregate round trip`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


import importlib.util
from pathlib import Path

from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_start_phase,
)

from conftest import get_script_path

_spec = importlib.util.spec_from_file_location(
    'manage_metrics_aggregate', get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
)


assert _spec is not None and _spec.loader is not None


manage_metrics = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(manage_metrics)


cmd_start_phase = manage_metrics.cmd_start_phase


cmd_end_phase = manage_metrics.cmd_end_phase


cmd_generate = manage_metrics.cmd_generate


cmd_record_dispatch_boundary = manage_metrics.cmd_record_dispatch_boundary


cmd_accumulate_agent_usage = manage_metrics.cmd_accumulate_agent_usage


#: The Total row's six value columns, keyed as `_TOTALS_FIELDS` keys them. Read
#: from production so a column added there is covered here without an edit — a
#: hand-listed copy would reproduce the very drift these tests exist to catch.
_TOTAL_COLUMNS = tuple(manage_metrics._TOTALS_FIELDS)


def _store(plan_context, plan_id: str) -> str:
    path: Path = plan_context.plan_dir_for(plan_id) / 'work' / 'metrics.toon'
    return path.read_text(encoding='utf-8')


def _report(plan_context, plan_id: str) -> str:
    path: Path = plan_context.plan_dir_for(plan_id) / 'metrics.md'
    return path.read_text(encoding='utf-8')


def _top_level_field(content: str, key: str) -> str | None:
    """Read a top-level `metrics.toon` key — the text above the first [phase]."""
    header = content.split('\n[', 1)[0]
    for line in header.splitlines():
        stripped = line.strip()
        if stripped.startswith(f'{key}:'):
            return stripped.split(':', 1)[1].strip()
    return None


def _phase_block(content: str, phase: str) -> str:
    start = content.index(f'[{phase}]')
    rest = content[start + len(f'[{phase}]'):]
    nxt = rest.find('\n[')
    return rest if nxt == -1 else rest[:nxt]


def _phase_field(content: str, phase: str, key: str) -> str | None:
    for line in _phase_block(content, phase).splitlines():
        stripped = line.strip()
        if stripped.startswith(f'{key}:'):
            return stripped.split(':', 1)[1].strip()
    return None


def _total_row_cells(report: str) -> list[str]:
    """Return the rendered Total row's cells, un-bolded and stripped."""
    for line in report.splitlines():
        if line.startswith('| **Total**'):
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            return [cell.strip('*').strip() for cell in cells]
    raise AssertionError('no Total row rendered')


def _drive_two_dispatched_phases(plan_id: str) -> None:
    """Close 4-plan and 5-execute with usage; leave the other four phases absent."""
    cmd_start_phase(ns_start_phase(plan_id, '4-plan'))
    cmd_end_phase(ns_end_phase(plan_id, '4-plan', total_tokens=30000, tool_uses=12, duration_ms=45000))
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=70000, tool_uses=25, duration_ms=90000))
