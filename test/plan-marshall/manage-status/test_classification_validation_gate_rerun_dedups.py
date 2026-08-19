#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the deterministic classification-validation gate."""


from __future__ import annotations

from _classification_validation_gate_fixtures import (
    _BUGFIX_BODY,
    _FEATURE_BODY,
    _ns,
    _ns_route,
    _write_marshal,
    _write_references,
    _write_request,
    _write_status,
    cmd_classification_validate,
    cmd_planning_lane_route,
    run_classification_validation,
)

# =============================================================================
# Dedup on re-run
# =============================================================================


def test_rerun_dedups_findings(plan_context):
    """Re-running the gate does not record duplicate findings (title dedup)."""
    plan_dir = plan_context.plan_dir_for('cv-dedup')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    # Run twice.
    first = run_classification_validation('cv-dedup')
    second = run_classification_validation('cv-dedup')

    # First records the finding; the second dedups (0 new emitted).
    assert first['findings_emitted'] == 1
    assert second['mismatch_count'] == 1
    assert second['findings_emitted'] == 0
    assert second['mismatches'][0]['finding_status'] == 'deduplicated'


# =============================================================================
# Subcommand wrapper + missing-plan handling
# =============================================================================


def test_cmd_returns_error_for_missing_plan(plan_context):
    """The subcommand returns a structured error when the plan dir is absent."""
    # No plan dir created.
    result = cmd_classification_validate(_ns('cv-nonexistent'))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Folded into planning-lane route — pre-route pass, never blocks the lane
# =============================================================================


def test_route_surfaces_classification_without_blocking(plan_context):
    """planning-lane route runs the gate as a pre-route pass and still resolves a lane."""
    # A plan that trips a mismatch (affected_files without scope).
    plan_dir = plan_context.plan_dir_for('cv-route')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['a/b.py'])
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('cv-route'))

    # Routing succeeded and resolved a lane; the gate result rides along.
    assert result['status'] == 'success'
    assert result['planning_lane'] in ('light', 'deep')
    cv = result['classification_validation']
    assert cv['mismatch_count'] >= 1
    assert 'non_empty_affected_files_with_null_scope' in {m['mismatch'] for m in cv['mismatches']}
