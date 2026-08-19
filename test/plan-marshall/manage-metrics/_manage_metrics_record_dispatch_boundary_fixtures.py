#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `record-dispatch-boundary` subcommand of manage_metrics.

phase-5-execute loses log coverage on agent-initiated re-dispatch without a
per-dispatch audit trail. That trail is captured by this subcommand.

A leading block pins the boundary MEASURE: the reader returns its row count
beside its token sum, because a sum cannot state its own coverage. The lettered
sections below pin the subcommand's own contract:

  (a) first invocation creates the artifact file with one row,
  (b) subsequent invocations append rows in order with monotonic timestamps,
  (c) every documented --termination-cause value is accepted (parametrized over
      the live DISPATCH_TERMINATION_CAUSES tuple, including budget_yield),
  (d) any other value rejected with non-zero exit before any file write,
  (e) missing required flags cause non-zero exit before any file write,
  (f) the artifact's TOON layout is parseable by the parse_toon helper.
"""


from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path

from _manage_metrics_fixtures import (
    ns_record_dispatch_boundary,
)

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')


# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('manage_metrics', SCRIPT_PATH)


assert _spec is not None and _spec.loader is not None


manage_metrics = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(manage_metrics)


DISPATCH_TERMINATION_CAUSES = manage_metrics.DISPATCH_TERMINATION_CAUSES


cmd_record_dispatch_boundary = manage_metrics.cmd_record_dispatch_boundary


def _ns(
    plan_id: str,
    phase: str = '5-execute',
    termination_cause: str = 'voluntary_checkpoint',
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
) -> Namespace:
    """A ``record-dispatch-boundary`` namespace from the script's own parser."""
    return ns_record_dispatch_boundary(
        plan_id,
        phase,
        termination_cause,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
    )


def _boundary_path(plan_dir: Path, phase: str = '5-execute') -> Path:
    return plan_dir / 'work' / f'metrics-dispatch-boundaries-{phase}.toon'


def _seed_status_json(plan_dir: Path) -> None:
    """Seed status.json so cmd_record_dispatch_boundary's require_plan_exists guard accepts the plan.

    The `PlanContext` helper creates the plan directory but does NOT write
    status.json — the per-plan sentinel that `require_plan_exists` checks for,
    the script-side guard against orphan-plan-dir creation.
    Tests that exercise the happy path of `cmd_record_dispatch_boundary` must
    call this helper after entering the context.
    """
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')


def _data_rows(content: str) -> list[str]:
    """Return only the data rows (skipping the TOON header lines)."""
    rows = []
    for line in content.splitlines():
        if not line:
            continue
        if line.startswith(('plan_id:', 'phase:', 'rows[]')):
            continue
        rows.append(line)
    return rows
