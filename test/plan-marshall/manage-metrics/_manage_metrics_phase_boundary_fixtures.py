#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage metrics phase boundary`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Tests for the `phase-boundary` subcommand of manage_metrics.

Covers:
  - end-of-prev + start-of-next persisted in a single call
  - optional token/duration/tool-uses forwarded to end-phase
  - metrics.md regenerated as a side-effect
  - invalid phase names rejected for either side
  - boundary works even when the previous phase had no start_time
"""


import importlib.util
import json

from conftest import get_script_path

# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location(
    'manage_metrics', get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
)


assert _spec is not None and _spec.loader is not None


manage_metrics = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(manage_metrics)


cmd_phase_boundary = manage_metrics.cmd_phase_boundary


cmd_start_phase = manage_metrics.cmd_start_phase


cmd_end_phase = manage_metrics.cmd_end_phase


cmd_boundary_status = manage_metrics.cmd_boundary_status


cmd_generate = manage_metrics.cmd_generate


cmd_accumulate_agent_usage = manage_metrics.cmd_accumulate_agent_usage


# =============================================================================
# require_plan_exists guard fixtures
# =============================================================================
#
# TASK-1 added a require_plan_exists guard to every plan-scoped writer in
# manage-metrics.py (start-phase, end-phase, generate, phase-boundary,
# accumulate-agent-usage, enrich). The guard returns ``error: plan_not_found``
# unless the plan directory carries a ``status.json`` sentinel. The
# ``plan_context`` fixture creates plan dirs without that sentinel, so every
# positive test would otherwise trip the guard.
#
# The autouse fixture below patches ``manage_metrics.require_plan_exists`` so
# that, during these tests, it auto-materialises the ``status.json`` sentinel for
# any plan whose dir exists but is not explicitly registered as "unseeded". This
# is the real guard chokepoint — it fires regardless of whether a test resolves
# its plan dir before or after calling the writer. Guard-negative tests register
# their plan_id via ``_register_unseeded`` so the patched guard lets the genuine
# ``plan_not_found`` branch run.

_UNSEEDED_PLAN_IDS: set[str] = set()


def _register_unseeded(plan_id: str) -> str:
    """Mark ``plan_id`` so the autouse guard-seeder leaves it un-sentinelled.

    Returns the plan_id for inline use. Negative guard tests call this so the
    patched ``require_plan_exists`` runs its genuine ``plan_not_found`` branch.
    """
    _UNSEEDED_PLAN_IDS.add(plan_id)
    return plan_id


def _phase_block(content: str, phase: str) -> str:
    """Return the metrics.toon text block for a single [phase] section."""
    start = content.index(f'[{phase}]')
    rest = content[start + len(f'[{phase}]'):]
    nxt = rest.find('\n[')
    return rest if nxt == -1 else rest[:nxt]


def _field(block: str, key: str) -> str | None:
    for line in block.splitlines():
        s = line.strip()
        if s.startswith(f'{key}:'):
            return s.split(':', 1)[1].strip()
    return None


# =============================================================================
# 1-init start_time backfill (D4)
# =============================================================================


def _seed_status_created(plan_dir, created_ts: str) -> None:
    """Write a minimal status.json with the given `created` timestamp."""
    status_path = plan_dir / 'status.json'
    status_path.write_text(
        json.dumps({'plan_id': plan_dir.name, 'created': created_ts}),
        encoding='utf-8',
    )


# =============================================================================
# Accumulate-on-re-entry write path
# =============================================================================
#
# A phase can legitimately close more than once — a finalize loop-back re-enters
# an earlier phase under the same phase key. The write site ACCUMULATES rather
# than replacing, under three distinct rules:
#
#   Rule A — provenance-keyed: an explicit-flag value is a per-close delta and is
#            ADDED; an accumulator-sourced value is already cumulative and is
#            ASSIGNED (adding it would double-count every re-close).
#   Rule B — duration_seconds adds the per-close ACTIVE span, anchored at
#            max(start_time, prior_end_time).
#   Rule C — agent_duration_ms accumulates FIRST, then the SUM is clamped to the
#            accumulated wall span.
#
# Every test drives a frozen clock so the spans are exact rather than
# real-wall-clock approximations.


def _freeze_clock(monkeypatch, timestamp: str) -> None:
    """Pin ``now_utc_iso`` to an exact ISO timestamp for deterministic spans."""
    monkeypatch.setattr(manage_metrics, 'now_utc_iso', lambda: timestamp)


def _read_block(plan_context, plan_id: str, phase: str) -> str:
    content = (plan_context.plan_dir_for(plan_id) / 'work' / 'metrics.toon').read_text()
    return _phase_block(content, phase)
