#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Parser cluster — extract_project_dir, router project_dir and body flags."""

import json

# Import the ci router module directly for unit tests of private helpers.
# conftest bootstraps PYTHONPATH so tools-integration-ci scripts are importable.
import _ci_barrier
import ci as ci_module
import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'ci.py')


def _sig(name, state, head):
    return (name, state, head)


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert (
        'provider-agnostic' in result.stdout.lower()
        or 'router' in result.stdout.lower()
        or 'ci' in result.stdout.lower()
    )


def test_no_args_exits_gracefully():
    """Test that running without args exits without crashing."""
    result = run_script(SCRIPT_PATH)
    # Two valid outcomes depending on marshal.json state:
    # - No CI provider: exit 0 with TOON error
    # - CI provider configured: exit 2 from argparse (no subcommand)
    assert result.returncode in (0, 2)


def test_pr_subcommand_returns_success():
    """Test that pr subcommand returns exit 0."""
    result = run_script(SCRIPT_PATH, 'pr', '--help')
    # Either delegates to provider (shows help) or returns TOON error
    assert result.success


def test_router_rejects_legacy_body_flag(tmp_path):
    """Router must refuse the legacy inline body flag at the ci.py level.

    Since ci.py delegates argument parsing to the provider, a provider parser
    configured with the new path-allocate flow will raise SystemExit when
    handed the legacy inline-body flag on any mutating subcommand. Exercise
    this via a configured GitHub provider so the delegated call reaches
    github_ops.py's build_parser.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal = {
        'providers': [
            {
                'skill_name': 'plan-marshall:workflow-integration-github',
                'category': 'ci',
            },
        ],
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal))

    result = run_script(
        SCRIPT_PATH,
        'pr',
        'create',
        '--title',
        'T',
        '--plan-id',
        'p',
        '--body',
        'X',
        cwd=tmp_path,
    )
    # argparse unknown-arg → non-zero exit; accept either 1 or 2 depending on
    # provider's error handling, but not success.
    assert result.returncode != 0


# =============================================================================
# ci_base re-export compatibility tests
# =============================================================================


def test_ci_router_extract_project_dir_is_ci_base_function():
    """Verify ci.extract_project_dir is the ci_base canonical implementation."""
    import ci_base

    assert ci_module.extract_project_dir is ci_base.extract_project_dir


def test_ci_router_output_error_is_ci_base_function():
    """Verify ci.output_error comes from ci_base (not a local definition)."""
    import ci_base

    assert ci_module.output_error is ci_base.output_error


def test_ci_router_safe_main_is_ci_base_re_export():
    """Verify ci.safe_main is the ci_base re-export of file_ops.safe_main."""
    import ci_base

    assert ci_module.safe_main is ci_base.safe_main


def test_ci_router_set_default_cwd_is_ci_base_function():
    """Verify ci.set_default_cwd comes from ci_base."""
    import ci_base

    assert ci_module.set_default_cwd is ci_base.set_default_cwd


# =============================================================================
# --project-dir pre-parse (extract_project_dir, hoisted to ci_base)
# =============================================================================


def test_extract_project_dir_space_form():
    """`--project-dir PATH` must be consumed and stripped from argv."""
    project_dir, remaining = ci_module.extract_project_dir(['--project-dir', '/tmp/wt', 'pr', 'view'])
    assert project_dir == '/tmp/wt'
    assert remaining == ['pr', 'view']


def test_extract_project_dir_equals_form():
    """`--project-dir=PATH` must be consumed and stripped from argv."""
    project_dir, remaining = ci_module.extract_project_dir(['--project-dir=/tmp/wt', 'pr', 'view'])
    assert project_dir == '/tmp/wt'
    assert remaining == ['pr', 'view']


def test_extract_project_dir_absent():
    """When --project-dir is absent, argv passes through unchanged and value is None."""
    argv = ['pr', 'view', '--pr-number', '42']
    project_dir, remaining = ci_module.extract_project_dir(argv)
    assert project_dir is None
    assert remaining == argv


def test_extract_project_dir_empty_value_rejected():
    """`--project-dir=` (empty value) must abort with exit code 2."""
    with pytest.raises(SystemExit) as excinfo:
        ci_module.extract_project_dir(['--project-dir=', 'pr', 'view'])
    assert excinfo.value.code == 2


def test_extract_project_dir_missing_arg_rejected():
    """`--project-dir` at the end with no PATH must abort with exit code 2."""
    with pytest.raises(SystemExit) as excinfo:
        ci_module.extract_project_dir(['--project-dir'])
    assert excinfo.value.code == 2


def test_extract_project_dir_only_first_consumed():
    """A second --project-dir must be left in argv for downstream rejection."""
    project_dir, remaining = ci_module.extract_project_dir(
        ['--project-dir', '/tmp/first', 'pr', 'view', '--project-dir', '/tmp/second']
    )
    assert project_dir == '/tmp/first'
    assert remaining == ['pr', 'view', '--project-dir', '/tmp/second']


def test_extract_project_dir_after_subcommand():
    """A --project-dir appearing after the subcommand is still consumed (pre-parse)."""
    # The pre-parse is position-agnostic: it scans the full argv. This documents
    # the current contract so downstream changes that try to enforce positional
    # constraints must update this test.
    project_dir, remaining = ci_module.extract_project_dir(['pr', '--project-dir', '/tmp/wt', 'view'])
    assert project_dir == '/tmp/wt'
    assert remaining == ['pr', 'view']


def test_extract_project_dir_default_behavior_preserved(tmp_path):
    """End-to-end: running without --project-dir behaves as before.

    A router invocation with no --project-dir and an unconfigured marshal.json
    must still exit with the standard 'not configured' TOON error, proving
    the pre-parse step is a no-op when the flag is absent.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text(json.dumps({'providers': []}))

    result = run_script(SCRIPT_PATH, cwd=tmp_path)
    assert result.success
    assert 'not configured' in result.stdout


def test_router_accepts_project_dir_with_unconfigured_provider(tmp_path):
    """End-to-end: passing --project-dir must not break the unconfigured path.

    The router must consume --project-dir before looking up the provider. With
    providers[] empty the call still returns the standard 'not configured' TOON
    error — the flag is silently accepted and does not reach the provider.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text(json.dumps({'providers': []}))

    result = run_script(SCRIPT_PATH, '--project-dir', str(tmp_path), cwd=tmp_path)
    assert result.success
    assert 'not configured' in result.stdout


def test_router_rejects_empty_project_dir(tmp_path):
    """End-to-end: `--project-dir=` must fail before provider lookup."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text(json.dumps({'providers': []}))

    result = run_script(SCRIPT_PATH, '--project-dir=', cwd=tmp_path)
    assert result.returncode == 2
    assert 'non-empty' in result.stderr or 'PATH' in result.stderr


# =============================================================================
# Two-state ``--plan-id`` / ``--project-dir`` routing contract
# =============================================================================
#
# The CI router pre-parses both flags via
# ``ci_base.extract_routing_args`` before delegating to the provider.
# The same two-state contract applies: --plan-id auto-routes,
# --project-dir is the explicit escape hatch, both → mutually exclusive,
# neither → main checkout fallback.


def test_router_rejects_both_plan_id_and_project_dir(tmp_path):
    """End-to-end: providing both flags MUST surface mutually_exclusive_args."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text(json.dumps({'providers': []}))

    result = run_script(
        SCRIPT_PATH,
        '--plan-id',
        'task-routing-canonical',
        '--project-dir',
        str(tmp_path),
        cwd=tmp_path,
    )
    # The router emits a TOON error payload via emit_mutually_exclusive_error
    # before any provider lookup happens.
    assert result.returncode == 2, f'Expected exit 2, got {result.returncode}; stdout={result.stdout!r}'
    # The error payload is printed via serialize_toon — surface check rather
    # than full TOON parse so we tolerate different formatting paths.
    assert 'mutually_exclusive_args' in result.stdout, (
        f'Expected mutually_exclusive_args in TOON output, got: {result.stdout!r}'
    )


def test_router_accepts_plan_id_only_flag(tmp_path):
    """`--plan-id` alone must be parsed (auto-routes via manage-status).

    With no real plan persisted at PLAN_BASE_DIR, the resolver fails — but
    the failure mode is ``worktree_resolution_failed`` (not the legacy
    "no provider configured" path), proving the routing flag was consumed
    before the provider lookup.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text(json.dumps({'providers': []}))

    result = run_script(
        SCRIPT_PATH,
        '--plan-id',
        'task-routing-canonical',
        cwd=tmp_path,
    )
    # Either:
    # - resolver runs and surfaces worktree_resolution_failed (exit 2), or
    # - resolver succeeds against the test cwd's main checkout and we hit
    #   the legacy "not configured" path (exit 0).
    # Both are valid outcomes — the regression we're guarding against is
    # an argparse failure at the router (exit 2 + argparse error to stderr).
    assert result.returncode in (0, 2), f'Unexpected returncode {result.returncode}; stderr={result.stderr!r}'
    assert 'unrecognized arguments' not in result.stderr, '--plan-id must be consumed by the router, not rejected'


# =============================================================================
# Concurrent finalize-wait barrier coordinator (_ci_barrier + `ci barrier`)
# =============================================================================
#
# The barrier is a provider-agnostic per-signal-proceed / bounded-re-settle
# state machine intercepted by the router BEFORE provider dispatch. These tests
# cover the pure state machine (compute_barrier_state) and the router-level
# `ci barrier` CLI wiring, including the three deliverable-4 paths:
# concurrent per-signal-proceed, bounded re-settle over affected signals only,
# and convergence in <=1-2 iterations.

# The three finalize-wait barrier signals, per phase-6-finalize.
_H1 = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'  # settled HEAD
_H2 = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'  # post-re-settle HEAD
