#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the deterministic classification-validation gate."""


from __future__ import annotations

from _classification_validation_gate_fixtures import (
    _BUGFIX_BODY,
    _FEATURE_BODY,
    _write_references,
    _write_request,
    _write_status,
    run_classification_validation,
)

# =============================================================================
# No false positives — valid input
# =============================================================================


def test_no_mismatch_on_valid_bug_fix(plan_context):
    """A bug_fix stamp over a bug-shaped request with a scope estimate yields no finding."""
    # bug_fix, bug-shaped narrative, scope set, no affected_files gap.
    plan_dir = plan_context.plan_dir_for('cv-valid-bugfix')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-valid-bugfix')

    assert result['status'] == 'success'
    assert result['mismatch_count'] == 0
    assert result['findings_emitted'] == 0
    assert result['blocked'] is False


def test_no_mismatch_when_scope_set_with_affected_files(plan_context):
    """A non-empty affected_files WITH a scope estimate does not trip mismatch class 2."""
    plan_dir = plan_context.plan_dir_for('cv-valid-scope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='single_module', affected_files=['a/b.py'])

    result = run_classification_validation('cv-valid-scope')

    assert result['mismatch_count'] == 0
    assert result['findings_emitted'] == 0


def test_no_mismatch_when_no_metadata(plan_context):
    """A plan with no change_type and no affected_files produces no finding."""
    # Minimal plan, nothing to cross-check.
    plan_dir = plan_context.plan_dir_for('cv-empty')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate=None)

    result = run_classification_validation('cv-empty')

    assert result['mismatch_count'] == 0
    assert result['blocked'] is False


# =============================================================================
# Mismatch class 1 — feature-as-bug_fix
# =============================================================================


def test_feature_as_bug_fix_fires(plan_context):
    """change_type=bug_fix over a feature-shaped narrative flags one finding."""
    plan_dir = plan_context.plan_dir_for('cv-feat-bug')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    result = run_classification_validation('cv-feat-bug')

    assert result['mismatch_count'] == 1
    assert result['mismatches'][0]['mismatch'] == 'feature_as_bug_fix'
    assert result['findings_emitted'] == 1
    assert result['blocked'] is False


def test_feature_as_bug_fix_does_not_fire_for_feature_change_type(plan_context):
    """A feature-shaped narrative correctly stamped change_type=feature is not flagged."""
    plan_dir = plan_context.plan_dir_for('cv-feat-ok')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'feature'})
    _write_references(plan_dir, scope_estimate='multi_module')

    result = run_classification_validation('cv-feat-ok')

    # No feature-as-bug_fix flag (change_type already matches).
    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'feature_as_bug_fix' not in classes


# =============================================================================
# Mismatch class 2 — affected_files without scope_estimate
# =============================================================================


def test_affected_files_without_scope_fires(plan_context):
    """Non-empty affected_files with a null scope_estimate flags one finding."""
    # affected_files set, scope_estimate absent.
    plan_dir = plan_context.plan_dir_for('cv-files-noscope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['x/y.py', 'x/z.py'])

    result = run_classification_validation('cv-files-noscope')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'non_empty_affected_files_with_null_scope'}
    assert result['findings_emitted'] == 1
    assert result['blocked'] is False


def test_affected_files_with_none_scope_string_fires(plan_context):
    """The literal scope_estimate 'none' counts as null for mismatch class 2."""
    plan_dir = plan_context.plan_dir_for('cv-files-nonescope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='none', affected_files=['x/y.py'])

    result = run_classification_validation('cv-files-nonescope')

    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'non_empty_affected_files_with_null_scope' in classes
