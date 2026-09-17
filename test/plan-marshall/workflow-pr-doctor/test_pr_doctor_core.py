#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for pr-doctor — diagnosis checks and retry policy."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
import pr_doctor
from pr_doctor import check_attempt, diagnose_pr, merge_handoff_with_params, set_project_dir, validate_handoff
from triage_helpers import make_error, parse_json_arg


def _parse_and_merge(handoff_json, pr=None, checks=None, auto_fix=None, max_fix_attempts=None, wait=None):
    """Helper to parse JSON handoff and merge with params, returning result dict."""
    handoff, rc = parse_json_arg(handoff_json, '--handoff')
    if rc:
        return rc
    if not isinstance(handoff, dict):
        return make_error('Handoff must be a JSON object')
    warnings = validate_handoff(handoff)

    merged = merge_handoff_with_params(
        handoff,
        pr=pr,
        checks=checks,
        auto_fix=auto_fix,
        max_fix_attempts=max_fix_attempts,
        wait=wait,
    )

    return {
        'merged': merged,
        'validation': {
            'valid': len(warnings) == 0,
            'warnings': warnings,
        },
        'status': 'success',
    }


# =============================================================================
# --project-dir forwarding tests
#
# The contract is:
#   - main() pre-parses --project-dir via ci_base.extract_project_dir,
#     strips it from argv, and stores the value in _PROJECT_DIR.
#   - forward_project_dir(cmd) appends --project-dir <value> when set,
#     and is a no-op when _PROJECT_DIR is None (default inherited cwd).
#   - run_child_cmd(cmd, **kwargs) routes every subprocess invocation
#     through forward_project_dir — this is the monkey-patch target.
# =============================================================================
@pytest.fixture
def clean_project_dir():
    """Reset module project-dir state before and after each test."""
    set_project_dir(None)
    yield
    set_project_dir(None)


@pytest.fixture
def capture_run():
    """Patch pr_doctor.subprocess.run with a MagicMock for the test duration."""
    mock = MagicMock(return_value=MagicMock(returncode=0, stdout='', stderr=''))
    with patch.object(pr_doctor.subprocess, 'run', mock):
        yield mock


# =============================================================================
# track-attempt (direct import)
# =============================================================================
def test_first_attempt_proceeds():
    """Test that the first attempt (current=0) should proceed."""
    result = check_attempt('build', 0, 3)

    assert result['status'] == 'success'
    assert result['proceed']
    assert result['attempt'] == 1
    assert result['remaining'] == 2
    assert result['category'] == 'build'


def test_last_attempt_proceeds():
    """Test that the last attempt (current=2 with max=3) proceeds."""
    result = check_attempt('sonar', 2, 3)

    assert result['proceed']
    assert result['attempt'] == 3
    assert result['remaining'] == 0


def test_exceeds_max_stops():
    """Test that exceeding max attempts stops."""
    result = check_attempt('reviews', 3, 3)

    assert result['proceed'] is False
    assert result['attempt'] == 4
    assert result['remaining'] == 0
    assert 'reached max' in result['reason']


def test_custom_max_attempts():
    """Test with custom max-attempts value."""
    result = check_attempt('build', 4, 5)

    assert result['proceed']
    assert result['attempt'] == 5
    assert result['remaining'] == 0


def test_default_max_attempts():
    """Test that default max-attempts is 3."""
    result = check_attempt('build', 0, 3)

    assert result['max_attempts'] == 3


def test_max_fix_attempts_override():
    """Test that max_fix_attempts param overrides handoff."""
    handoff = {'constraints': {'max_fix_attempts': 5}}

    result = _parse_and_merge(json.dumps(handoff), max_fix_attempts=10)

    assert result['merged']['max_fix_attempts'] == 10


# =============================================================================
# diagnose (direct import)
# =============================================================================
def test_all_pass():
    """Test diagnosis with no issues."""
    result = diagnose_pr(build_status='success')

    assert result['status'] == 'success'
    assert result['overall'] == 'pass'
    assert result['build_status'] == 'PASS'
    assert result['review_comments'] == 0
    assert result['sonar_issues'] == 0
    assert len(result['issues']) == 0


def test_build_failure():
    """Test diagnosis with build failure."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'test', 'message': '3 tests failed'}],
    )

    assert result['overall'] == 'fail'
    assert result['build_status'] == 'FAIL'
    assert any(i['category'] == 'build' for i in result['issues'])
    assert any('build' in a.lower() for a in result['recommended_actions'])


def test_review_comments():
    """Test diagnosis with unresolved review comments."""
    result = diagnose_pr(
        review_comments=[
            {'priority': 'high', 'body': 'Fix this'},
            {'priority': 'low', 'body': 'Nit'},
        ]
    )

    assert result['overall'] == 'fail'
    assert result['review_comments'] == 2
    review_issue = next(i for i in result['issues'] if i['category'] == 'reviews')
    assert review_issue['severity'] == 'high'


def test_sonar_issues():
    """Test diagnosis with Sonar issues."""
    result = diagnose_pr(
        sonar_issues=[
            {'severity': 'BLOCKER', 'rule': 'java:S1234'},
            {'severity': 'MAJOR', 'rule': 'java:S5678'},
            {'severity': 'MINOR', 'rule': 'java:S9012'},
        ]
    )

    assert result['sonar_issues'] == 3
    sonar_issue = next(i for i in result['issues'] if i['category'] == 'sonar')
    assert sonar_issue['severity'] == 'high'


def test_combined_diagnosis():
    """Test diagnosis with all three categories."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'compile', 'message': 'error'}],
        review_comments=[{'priority': 'medium'}],
        sonar_issues=[{'severity': 'MAJOR'}],
    )

    assert result['overall'] == 'fail'
    categories = {i['category'] for i in result['issues']}
    assert categories == {'build', 'reviews', 'sonar'}
    assert len(result['recommended_actions']) == 3


def test_build_pass_with_review_issues():
    """Test diagnosis with passing build but unresolved review comments."""
    result = diagnose_pr(
        build_status='success',
        review_comments=[{'priority': 'high', 'body': 'Fix this'}],
    )

    assert result['overall'] == 'fail'
    assert result['build_status'] == 'PASS'
    assert result['review_comments'] == 1
    categories = {i['category'] for i in result['issues']}
    assert 'reviews' in categories
    assert 'build' not in categories


def test_no_inputs_is_pass():
    """Test that diagnose with no inputs reports pass."""
    result = diagnose_pr()

    assert result['overall'] == 'pass'
    assert result['build_status'] == 'UNKNOWN'


def test_sonar_severity_breakdown():
    """Test that Sonar diagnosis includes severity breakdown."""
    result = diagnose_pr(
        sonar_issues=[
            {'severity': 'CRITICAL'},
            {'severity': 'CRITICAL'},
            {'severity': 'MAJOR'},
        ]
    )

    sonar_issue = next(i for i in result['issues'] if i['category'] == 'sonar')
    assert sonar_issue['breakdown']['CRITICAL'] == 2
    assert sonar_issue['breakdown']['MAJOR'] == 1


# =============================================================================
# diagnose build severity
# =============================================================================
def test_lint_failure_is_medium():
    """Lint failure should be medium severity, not high."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'lint', 'message': 'ESLint errors'}],
    )

    build_issue = next(i for i in result['issues'] if i['category'] == 'build')
    assert build_issue['severity'] == 'medium'


def test_compile_failure_is_high():
    """Compile failure should be high severity."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'compile', 'message': 'Compilation error'}],
    )

    build_issue = next(i for i in result['issues'] if i['category'] == 'build')
    assert build_issue['severity'] == 'high'


def test_unknown_step_defaults_to_high():
    """Unknown step type should default to high severity."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'unknown', 'message': 'Something failed'}],
    )

    build_issue = next(i for i in result['issues'] if i['category'] == 'build')
    assert build_issue['severity'] == 'high'


# =============================================================================
# diagnose edge cases
# =============================================================================
def test_build_status_none_with_failures_skips_build():
    """When build_status is None, build failures are ignored."""
    result = diagnose_pr(
        build_failures=[{'step': 'test', 'message': 'fails'}],
    )

    assert result['build_status'] == 'UNKNOWN'
    build_issues = [i for i in result['issues'] if i['category'] == 'build']
    assert len(build_issues) == 0


# =============================================================================
# parse-handoff skip_sonar field
# =============================================================================
def test_skip_sonar_true():
    """Test that skip_sonar is extracted from handoff decisions."""
    handoff = {'decisions': {'skip_sonar': True}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['skip_sonar']


def test_skip_sonar_defaults_false():
    """Test that skip_sonar defaults to False when not in handoff."""
    handoff = {'artifacts': {'pr_number': 1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['skip_sonar'] is False


# =============================================================================
# parse-handoff automated_review field
# =============================================================================
def test_automated_review_true():
    """Test that automated_review is extracted from handoff decisions."""
    handoff = {'decisions': {'automated_review': True}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['automated_review']


def test_automated_review_defaults_false():
    """Test that automated_review defaults to False when not in handoff."""
    handoff = {'artifacts': {'pr_number': 1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['automated_review'] is False


# =============================================================================
# parse-handoff semantic validation
# =============================================================================
def test_checks_sonar_with_skip_sonar_warns():
    """checks=sonar + skip_sonar=true is contradictory — should warn."""
    handoff = {'decisions': {'checks': 'sonar', 'skip_sonar': True}}

    result = _parse_and_merge(json.dumps(handoff))

    warnings = result['validation']['warnings']
    assert any('sonar' in w.lower() and ('skip' in w.lower() or 'contradict' in w.lower()) for w in warnings), (
        f'Expected contradiction warning about sonar, got: {warnings}'
    )
