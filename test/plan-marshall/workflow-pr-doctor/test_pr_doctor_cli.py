#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for pr-doctor — handoff parsing and CLI surface."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch
import pytest
from _resolve_project_dir_fixtures import worktree_query_result
from conftest import get_script_path, run_script
import pr_doctor
from pr_doctor import forward_project_dir, merge_handoff_with_params, run_child_cmd, set_project_dir, validate_handoff
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


# -- main() argv pre-parsing: space and equals forms -------------------
def _run_main_with_argv(argv):
    """Run pr_doctor.main() under patched argv with diagnose stubbed out."""
    # Stub cmd_diagnose to return quickly without doing real work — we only
    # care about what main() does to argv and _PROJECT_DIR before dispatch.
    stub = MagicMock(return_value={'status': 'success', 'overall': 'pass'})
    with patch.object(pr_doctor, 'cmd_diagnose', stub), patch.object(sys, 'argv', argv):
        pr_doctor.main()
    return stub


# =============================================================================
# parse-handoff (direct import)
# =============================================================================
def test_full_handoff():
    """Test parsing a complete handoff structure."""
    handoff = {
        'artifacts': {
            'pr_number': 123,
            'branch': 'feature/my-feature',
            'commit_hash': 'abc123',
            'plan_id': 'my-plan',
        },
        'decisions': {
            'auto_fix': True,
            'checks': 'all',
            'skip_sonar': False,
        },
        'constraints': {
            'max_fix_attempts': 3,
            'protected_files': ['README.md'],
        },
    }

    result = _parse_and_merge(json.dumps(handoff))

    assert result['status'] == 'success'
    merged = result['merged']
    assert merged['pr_number'] == 123
    assert merged['branch'] == 'feature/my-feature'
    assert merged['checks'] == 'all'
    assert merged['auto_fix']
    assert merged['max_fix_attempts'] == 3
    assert result['validation']['valid']
    assert len(result['validation']['warnings']) == 0


def test_minimal_handoff():
    """Test parsing a minimal handoff with defaults."""
    handoff = {'artifacts': {'pr_number': 42}}

    result = _parse_and_merge(json.dumps(handoff))

    merged = result['merged']
    assert merged['pr_number'] == 42
    assert merged['checks'] == 'all'
    assert merged['auto_fix'] is False
    assert merged['max_fix_attempts'] == 3


def test_explicit_params_override_handoff():
    """Test that explicit params override handoff values."""
    handoff = {
        'artifacts': {'pr_number': 100},
        'decisions': {'checks': 'all', 'auto_fix': False},
    }

    result = _parse_and_merge(json.dumps(handoff), pr=456, checks='build', auto_fix=True)

    merged = result['merged']
    assert merged['pr_number'] == 456
    assert merged['checks'] == 'build'
    assert merged['auto_fix']


def test_empty_handoff():
    """Test parsing empty handoff uses defaults."""
    result = _parse_and_merge('{}')

    merged = result['merged']
    assert merged['pr_number'] is None
    assert merged['checks'] == 'all'
    assert merged['auto_fix'] is False


def test_auto_fix_not_provided_uses_handoff():
    """Test that omitting auto_fix defers to handoff value."""
    handoff = {'decisions': {'auto_fix': False}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['auto_fix'] is False


def test_auto_fix_not_provided_defaults_false():
    """Test that omitting auto_fix without handoff defaults to False."""
    handoff = {'artifacts': {'pr_number': 1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['auto_fix'] is False


def test_no_wait_overrides_handoff():
    """Test that wait=False overrides handoff wait=true."""
    handoff = {'decisions': {'wait': True}}

    result = _parse_and_merge(json.dumps(handoff), wait=False)

    assert result['merged']['wait'] is False


def test_wait_defaults_true():
    """Test that wait defaults to True without flags."""
    handoff = {'artifacts': {'pr_number': 1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['wait']


def test_wait_override_true():
    """Test that wait=True overrides handoff wait=false."""
    handoff = {'decisions': {'wait': False}}

    result = _parse_and_merge(json.dumps(handoff), wait=True)

    assert result['merged']['wait']


def test_help():
    """Test help output."""
    stdout, _, code = run_doctor_script(['--help'])

    assert code == 0
    assert 'parse-handoff' in stdout
    assert 'track-attempt' in stdout
    assert 'diagnose' in stdout


# -- forward_project_dir unit-level behaviour --------------------------
def test_forward_noop_when_unset(clean_project_dir):
    """Absent --project-dir, forward_project_dir must not mutate cmd."""
    set_project_dir(None)
    cmd = ['ci', 'pr', 'checks', '--pr', '123']

    forwarded = forward_project_dir(cmd)

    assert forwarded == cmd
    assert '--project-dir' not in forwarded


def test_forward_appends_when_set(clean_project_dir):
    """When set, forward appends --project-dir <value> at the tail."""
    set_project_dir('/tmp/worktree')
    cmd = ['ci', 'pr', 'checks', '--pr', '123']

    forwarded = forward_project_dir(cmd)

    assert forwarded[-2:] == ['--project-dir', '/tmp/worktree']
    assert '--project-dir' not in cmd


def test_forward_preserves_list_identity(clean_project_dir):
    """forward_project_dir returns a new list, never mutates input."""
    set_project_dir('/tmp/worktree')
    cmd = ['build', 'run']

    forwarded = forward_project_dir(cmd)

    assert forwarded is not cmd
    assert cmd == ['build', 'run']


# -- run_child_cmd: subprocess.run monkey-patch ------------------------
def test_run_child_cmd_forwards_when_set(clean_project_dir, capture_run):
    """Every child script invocation must receive --project-dir."""
    set_project_dir('/tmp/worktree')
    child_cmds = [
        ['ci', 'pr', 'checks', '--pr', '123'],
        ['build', 'run', '--command-args', 'verify'],
        ['sonar', 'issues', 'list'],
        ['github', 'pr', 'review'],
        ['gitlab', 'mr', 'discussions'],
        ['architecture', 'resolve', '--command', 'compile'],
    ]

    for cmd in child_cmds:
        run_child_cmd(cmd)

    assert capture_run.call_count == len(child_cmds)
    for call in capture_run.call_args_list:
        forwarded = call.args[0]
        assert '--project-dir' in forwarded, f'missing flag in {forwarded}'
        idx = forwarded.index('--project-dir')
        assert forwarded[idx + 1] == '/tmp/worktree'


def test_run_child_cmd_noop_when_unset(clean_project_dir, capture_run):
    """Default (no --project-dir) must not append the flag."""
    set_project_dir(None)
    child_cmds = [
        ['ci', 'pr', 'checks', '--pr', '123'],
        ['build', 'run', '--command-args', 'verify'],
        ['sonar', 'issues', 'list'],
        ['github', 'pr', 'review'],
        ['gitlab', 'mr', 'discussions'],
        ['architecture', 'resolve', '--command', 'compile'],
    ]

    for cmd in child_cmds:
        run_child_cmd(cmd)

    assert capture_run.call_count == len(child_cmds)
    for call in capture_run.call_args_list:
        forwarded = call.args[0]
        assert '--project-dir' not in forwarded, f'unexpected flag in {forwarded}'


def test_run_child_cmd_passes_kwargs(clean_project_dir, capture_run):
    """run_child_cmd must transparently forward subprocess.run kwargs."""
    set_project_dir('/tmp/worktree')

    run_child_cmd(['ci', 'pr'], capture_output=True, text=True, check=False)

    assert capture_run.call_count == 1
    kwargs = capture_run.call_args.kwargs
    assert kwargs.get('capture_output')
    assert kwargs.get('text')
    assert kwargs.get('check') is False


def test_main_strips_project_dir_space_form(clean_project_dir, capture_run):
    """main() must pre-parse --project-dir PATH and store it."""
    argv = ['pr_doctor.py', '--project-dir', '/tmp/worktree', 'diagnose', '--build-status', 'success']

    _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() == '/tmp/worktree'
    assert '--project-dir' not in sys.argv
    assert '/tmp/worktree' not in sys.argv


def test_main_strips_project_dir_equals_form(clean_project_dir, capture_run):
    """main() must also accept --project-dir=PATH."""
    argv = ['pr_doctor.py', '--project-dir=/tmp/worktree', 'diagnose', '--build-status', 'success']

    _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() == '/tmp/worktree'
    assert '--project-dir' not in sys.argv
    assert not any(a.startswith('--project-dir') for a in sys.argv)


def test_main_without_project_dir_leaves_unset(clean_project_dir, capture_run):
    """Absent the flag, _PROJECT_DIR must remain None."""
    argv = ['pr_doctor.py', 'diagnose', '--build-status', 'success']

    _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() is None


# -- Two-state ``--plan-id`` / ``--project-dir`` routing contract ----
def test_main_plan_id_resolves_via_manage_status(clean_project_dir, capture_run):
    """Router-level --plan-id auto-resolves to the persisted worktree path."""
    # The manage-status shell-out seam lives in file_ops; resolve_project_dir
    # delegates the worktree face to file_ops.resolve_plan_context.
    import file_ops as _resolver_core

    argv = [
        'pr_doctor.py',
        '--plan-id',
        'task-routing-canonical',
        'diagnose',
        '--build-status',
        'success',
    ]

    with patch.object(
        _resolver_core,
        '_query_worktree_path',
        return_value=worktree_query_result(True, '/tmp/wt-pr-doctor'),
    ):
        _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() == '/tmp/wt-pr-doctor'


def test_main_plan_id_use_worktree_false_falls_back_to_main_checkout(clean_project_dir, capture_run):
    """``use_worktree=false`` resolution surfaces the main checkout root."""
    import file_ops as _resolver_core

    argv = [
        'pr_doctor.py',
        '--plan-id',
        'task-routing-canonical',
        'diagnose',
        '--build-status',
        'success',
    ]

    with (
        patch.object(_resolver_core, '_query_worktree_path', return_value=worktree_query_result(False)),
        patch.object(_resolver_core, 'cwd_checkout_root', return_value='/tmp/main-stub'),
    ):
        _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() == '/tmp/main-stub'
