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

from _manage_metrics_record_dispatch_boundary_fixtures import (
    _boundary_path,
    _ns,
    _seed_status_json,
    cmd_record_dispatch_boundary,
)


def test_record_dispatch_boundary_with_initialized_plan_id_continues_to_work(plan_context):
    """Happy path: initialized plan_id (status.json present) → success.

    Pins that the require_plan_exists guard does not regress the existing
    cmd_record_dispatch_boundary contract for in-progress plans.
    """
    plan_dir = plan_context.plan_dir_for('disp-happy')
    _seed_status_json(plan_dir)
    result = cmd_record_dispatch_boundary(
        _ns(
            'disp-happy',
            phase='5-execute',
            termination_cause='voluntary_checkpoint',
            total_tokens=99,
            tool_uses=3,
            duration_ms=500,
        )
    )

    assert result['status'] == 'success'
    assert result['plan_id'] == 'disp-happy'
    assert result['rows_recorded'] == 1
    # The boundaries file was written to the expected path.
    path = _boundary_path(plan_dir, '5-execute')
    assert path.exists()
