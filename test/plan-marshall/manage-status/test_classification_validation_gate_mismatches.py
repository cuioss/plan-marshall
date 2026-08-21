#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the deterministic classification-validation gate.

Its sections, in order:

* Folded into planning-lane route — pre-route pass, never blocks the lane
* Both mismatches together
* Dedup on re-run
* Subcommand wrapper + missing-plan handling
"""


from __future__ import annotations

from _classification_validation_gate_fixtures import (
    _BUGFIX_BODY,
    _FEATURE_BODY,
    _MULTI_MODULE_MIN_PATHS,
    _body_with_paths,
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


def test_class_two_and_class_three_are_mutually_exclusive(plan_context):
    """Classes 2 and 3 can never co-fire, so all three classes cannot fire at once.

    Class 2 requires ``scope_estimate`` to be null / empty / ``none``; class 3
    requires it to be exactly ``surgical``. The two predicates are disjoint on the
    same field by construction. Recording this keeps ``mismatch_count`` honest — the
    gate has three classes but its ceiling is two, and a future reader must not
    infer a maximum of three from the class count.
    """
    plan_dir = plan_context.plan_dir_for('cv-mutual-exclusion')
    _write_request(plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS))
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    # A null scope satisfies class 2 and, by the same value, disqualifies class 3.
    _write_references(plan_dir, scope_estimate=None, affected_files=['a/b.py'])

    result = run_classification_validation('cv-mutual-exclusion')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'non_empty_affected_files_with_null_scope' in classes
    assert 'scale_mismatch_light_routing' not in classes


def test_class_one_and_class_three_co_fire_two_findings(plan_context):
    """The reachable two-class maximum: a feature-shaped bug_fix stamp over a large body."""
    plan_dir = plan_context.plan_dir_for('cv-one-and-three')
    _write_request(
        plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS, lead=f'{_FEATURE_BODY} ')
    )
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-one-and-three')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'feature_as_bug_fix', 'scale_mismatch_light_routing'}
    assert result['mismatch_count'] == 2
    assert result['findings_emitted'] == 2
    assert result['blocked'] is False


def test_route_is_not_blocked_by_a_scale_mismatch(plan_context):
    """A fired class-3 finding rides along on the route return without gating the lane."""
    plan_dir = plan_context.plan_dir_for('cv-scale-route')
    _write_request(plan_dir, _body_with_paths(_MULTI_MODULE_MIN_PATHS))
    _write_status(plan_dir, metadata={'change_type': 'tech_debt', 'plan_source': 'lesson'})
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('cv-scale-route'))

    assert result['status'] == 'success'
    assert result['planning_lane'] in ('light', 'deep')
    cv = result['classification_validation']
    assert 'scale_mismatch_light_routing' in {m['mismatch'] for m in cv['mismatches']}


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


# =============================================================================
# Both mismatches together
# =============================================================================


def test_both_mismatches_fire_two_findings(plan_context):
    """A plan tripping both classes records two distinct findings without blocking."""
    # bug_fix over a feature narrative AND affected_files without scope.
    plan_dir = plan_context.plan_dir_for('cv-both')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['a/b.py'])

    result = run_classification_validation('cv-both')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'feature_as_bug_fix', 'non_empty_affected_files_with_null_scope'}
    assert result['mismatch_count'] == 2
    assert result['findings_emitted'] == 2
    assert result['blocked'] is False


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
