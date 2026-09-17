#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for pr-doctor — validation and error envelopes.
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch
import pytest
from conftest import get_script_path, run_script
import pr_doctor
from pr_doctor import diagnose_pr, merge_handoff_with_params, set_project_dir, validate_handoff
from triage_helpers import make_error, parse_json_arg


SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-pr-doctor', 'pr_doctor.py')


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
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================
def run_doctor_script(args: list) -> tuple:
    """Run pr_doctor.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


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


def test_invalid_json():
    """Test error on invalid JSON."""
    result = _parse_and_merge('not-json')

    assert result['status'] == 'error'
    assert 'Invalid' in result['error']
    assert 'JSON' in result['error']


def test_handoff_not_dict():
    """Test error when handoff is not a dict."""
    result = _parse_and_merge('[1,2,3]')

    assert result['status'] == 'error'
    assert 'object' in result['error']


def test_validation_warns_on_bad_pr_number():
    """Test validation warns on invalid PR number."""
    handoff = {'artifacts': {'pr_number': -1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['validation']['valid'] is False
    assert any('pr_number' in w for w in result['validation']['warnings'])


def test_validation_warns_on_bad_checks():
    """Test validation warns on invalid checks value."""
    handoff = {'decisions': {'checks': 'invalid'}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['validation']['valid'] is False
    assert any('checks' in w for w in result['validation']['warnings'])


def test_validation_warns_on_unknown_keys():
    """Test validation warns on unknown top-level keys."""
    handoff = {'artifacts': {}, 'extra_key': 'value'}

    result = _parse_and_merge(json.dumps(handoff))

    assert any('Unknown' in w for w in result['validation']['warnings'])


def test_validation_warns_on_bad_auto_fix_type():
    """Test validation warns when auto_fix is not a bool."""
    handoff = {'decisions': {'auto_fix': 'yes'}}

    result = _parse_and_merge(json.dumps(handoff))

    assert any('auto_fix' in w for w in result['validation']['warnings'])


def test_validation_warns_on_bad_max_fix_attempts():
    """Test validation warns when max_fix_attempts is not a positive int."""
    handoff = {'constraints': {'max_fix_attempts': 0}}

    result = _parse_and_merge(json.dumps(handoff))

    assert any('max_fix_attempts' in w for w in result['validation']['warnings'])


def test_validation_warns_on_bad_protected_files():
    """Test validation warns when protected_files contains non-strings."""
    handoff = {'constraints': {'protected_files': [1, 2]}}

    result = _parse_and_merge(json.dumps(handoff))

    assert any('protected_files' in w for w in result['validation']['warnings'])


# =============================================================================
# diagnose input validation for malformed data
# =============================================================================
def test_diagnose_build_failures_missing_keys():
    """Test diagnose handles build failures without expected keys."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'unexpected_key': 'value'}],
    )

    assert result['status'] == 'success'
    build_issue = next(i for i in result['issues'] if i['category'] == 'build')
    assert build_issue['step'] == 'unknown'
    assert build_issue['detail'] == 'Build failure'


def test_diagnose_review_comments_non_dict_entries():
    """Test diagnose handles non-dict entries in review comments array."""
    result = diagnose_pr(
        review_comments=[
            {'priority': 'high'},
            'not-a-dict',
            42,
        ]
    )

    assert result['status'] == 'success'
    assert result['review_comments'] == 3


def test_diagnose_sonar_issues_non_dict_entries():
    """Test diagnose handles non-dict entries in sonar issues array."""
    result = diagnose_pr(
        sonar_issues=[
            {'severity': 'MAJOR'},
            'invalid-entry',
        ]
    )

    assert result['status'] == 'success'
    assert result['sonar_issues'] == 2


def test_diagnose_build_failures_non_dict_entries():
    """Test diagnose handles non-dict entries in build failures array."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=['not-a-dict', 42],
    )

    assert result['status'] == 'success'
    for issue in result['issues']:
        if issue['category'] == 'build':
            assert issue['step'] == 'unknown'


def test_no_subcommand():
    """Test error when no subcommand provided."""
    _, stderr, code = run_doctor_script([])

    assert code != 0


def test_invalid_category():
    """Test that invalid category is rejected by argparse."""
    _, stderr, code = run_doctor_script(
        [
            'track-attempt',
            '--category',
            'invalid',
            '--current',
            '0',
        ]
    )

    assert code != 0
    assert 'invalid' in stderr


def test_main_emits_mutually_exclusive_error_on_both_flags(clean_project_dir):
    """Both router-level --plan-id and --project-dir → mutually_exclusive_args."""
    argv = [
        'pr_doctor.py',
        '--plan-id',
        'task-routing-canonical',
        '--project-dir',
        '/tmp/explicit',
        'diagnose',
        '--build-status',
        'success',
    ]

    # main() may or may not propagate the SystemExit depending on how
    # extract_routing_args handles the error — it calls sys.exit(2) directly.
    buf = io.StringIO()
    with patch.object(sys, 'argv', argv):
        with pytest.raises(SystemExit) as ctx:
            with redirect_stdout(buf):
                pr_doctor.main()

    assert ctx.value.code == 2
    assert 'mutually_exclusive_args' in buf.getvalue()

