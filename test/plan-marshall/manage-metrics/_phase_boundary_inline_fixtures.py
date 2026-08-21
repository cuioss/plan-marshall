#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``phase boundary inline`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""


import importlib.util

import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_enrich,
    ns_phase_boundary,
    ns_start_phase,
)

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


cmd_generate = manage_metrics.cmd_generate


cmd_enrich = manage_metrics.cmd_enrich


# Production-shaped per-phase enrich buckets — the exact shape the runtime's
# ``metrics normalized-tokens`` op returns for the three inline phases (the
# canonical ``message.usage`` four-field keys plus the billing-weighted total),
# NOT a synthetic pre-normalization transcript shape.
_INLINE_ENRICH_BUCKETS = {
    # cache_read DOMINATES 1-init (11M) — two orders above the comparable
    # input+output+cache_creation (60K). enrich's inline total_tokens EXCLUDES
    # cache_read, so it must surface ~60K, not the ~11M four-field sum.
    '1-init': {
        'input_tokens': 40000,
        'output_tokens': 15000,
        'cache_read_input_tokens': 11000000,
        'cache_creation_input_tokens': 5000,
        'billing_weighted_total': 12000,
    },
    '2-refine': {
        'input_tokens': 6000,
        'output_tokens': 1500,
        'cache_read_input_tokens': 30000,
        'cache_creation_input_tokens': 0,
        'billing_weighted_total': 9000,
    },
    '3-outline': {
        'input_tokens': 5000,
        'output_tokens': 1200,
        'cache_read_input_tokens': 20000,
        'cache_creation_input_tokens': 0,
        'billing_weighted_total': 7000,
    },
}


# The three-field sum enrich derives into total_tokens for the inline 1-init row
# (input + output + cache_creation — cache_read EXCLUDED). ~60K, not ~11M.
_INIT_INLINE_TOTAL = 40000 + 15000 + 5000


# The cache_read magnitude the derived total must NOT reach.
_INIT_CACHE_READ = 11000000


def _run_inline_enrich(plan_id: str, monkeypatch, buckets: dict | None = None) -> dict:
    """Drive the real cmd_enrich with the runtime op stubbed to inline buckets.

    ``cmd_enrich`` hands the phase windows to the platform-runtime transcript
    engine over a subprocess boundary; the unit test replaces that one seam with
    a production-shaped return so the rest of enrich (four-field raw write + the
    three-field inline total_tokens derivation) runs for real.
    """
    resolved = _INLINE_ENRICH_BUCKETS if buckets is None else buckets

    def _fake_op(session_id, windows):
        counters = {'message_count': 42, 'four_field_phases_attributed': len(resolved)}
        return dict(resolved), counters, 'success'

    monkeypatch.setattr(manage_metrics, '_run_normalized_tokens_op', _fake_op)
    result: dict = cmd_enrich(ns_enrich(plan_id, 'sess-inline'))
    return result


# =============================================================================
# Namespace helpers
# =============================================================================


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


def _drive_full_six_phase_plan(plan_id: str) -> None:
    """Record a complete six-phase plan with the inline phases closed usage-free.

    Models the shipped topology: phase-1-init and the recipe-inline refine /
    outline phases run inline (no agent `<usage>`), so their closing
    `phase-boundary` calls OMIT the token/duration/tool-uses flags. The
    dispatched phases (4-plan, 5-execute, 6-finalize) close with usage data.
    Every phase ends up with an `end_time`, so the plan is fully recorded.
    """
    # 1-init opens via the phase-1-init Step 3a self-record, then closes inline.
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    # Inline boundaries — usage flags OMITTED (no agent <usage> envelope).
    cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase='1-init', next_phase='2-refine'))
    cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase='2-refine', next_phase='3-outline'))
    cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase='3-outline', next_phase='4-plan'))
    # Dispatched boundaries — usage data present.
    cmd_phase_boundary(
        ns_phase_boundary(plan_id, prev_phase='4-plan', next_phase='5-execute', total_tokens=42000, tool_uses=15)
    )
    cmd_phase_boundary(
        ns_phase_boundary(plan_id, prev_phase='5-execute', next_phase='6-finalize', total_tokens=88000, tool_uses=30)
    )
    cmd_end_phase(ns_end_phase(plan_id, phase='6-finalize', total_tokens=31000, tool_uses=12))


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        plan_dir = real_get_plan_dir(plan_id)
        plan_dir.mkdir(parents=True, exist_ok=True)
        sentinel = plan_dir / 'status.json'
        if not sentinel.is_file():
            sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context
