#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `record-dispatch-boundary` subcommand of manage_metrics.

Its one section: (h) Script-side require_plan_exists guard.
"""


from __future__ import annotations

from _manage_metrics_record_dispatch_boundary_fixtures import (
    _boundary_path,
    _ns,
    _seed_status_json,
    cmd_record_dispatch_boundary,
)

# =============================================================================
# (h) Script-side require_plan_exists guard
#
# cmd_record_dispatch_boundary MUST refuse to write a dispatch-boundary row
# under a plan directory that does not exist (or exists but lacks
# status.json). The guard returns the canonical TOON envelope and MUST NOT
# mkdir the plan tree as a side-effect.
# =============================================================================


def test_record_dispatch_boundary_rejects_unknown_plan_id_no_mkdir(tmp_path, monkeypatch):
    """Unknown plan_id: returns plan_not_found error, no plan dir created."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plans_dir = tmp_path / 'plans'
    # Pre-condition: plans/ tree absent.
    assert not plans_dir.exists()

    result = cmd_record_dispatch_boundary(
        _ns(
            'never-initialized',
            phase='5-execute',
            termination_cause='voluntary_checkpoint',
            total_tokens=1,
            tool_uses=1,
            duration_ms=1,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
    assert result['plan_id'] == 'never-initialized'
    assert 'never-initialized' in result['plan_dir']
    # Side-effect invariant: the guard MUST NOT have mkdir'd the plan tree.
    assert not plans_dir.exists()


def test_record_dispatch_boundary_rejects_plan_dir_missing_status_json_no_mkdir(
    tmp_path, monkeypatch
):
    """Plan dir exists but no status.json: returns plan_not_found error."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    half_dir = tmp_path / 'plans' / 'half-initialized'
    half_dir.mkdir(parents=True)
    assert not (half_dir / 'status.json').exists()

    result = cmd_record_dispatch_boundary(
        _ns(
            'half-initialized',
            phase='5-execute',
            termination_cause='voluntary_checkpoint',
            total_tokens=1,
            tool_uses=1,
            duration_ms=1,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
    assert result['plan_id'] == 'half-initialized'
    # The pre-existing directory remains, status.json is NOT auto-created,
    # and the work/ subtree (where the boundaries file would live) was NOT
    # materialised by the guard rejection.
    assert half_dir.is_dir()
    assert not (half_dir / 'status.json').exists()
    assert not (half_dir / 'work').exists()


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
