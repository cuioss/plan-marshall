#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ci.py provider-agnostic router script.

Tests that the router correctly parses arguments and delegates.
Note: Without marshal.json, the router exits with an error (expected).
"""

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


def test_get_provider_ignores_legacy_ci_config(tmp_path):
    """Test that get_provider() ignores legacy config['ci'] and requires providers[]."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    # Legacy config['ci'] present but providers[] empty — resolver must ignore it.
    marshal = {
        'ci': {'provider': 'github', 'repo_url': 'https://github.com/org/repo'},
        'providers': [],
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal))

    result = run_script(SCRIPT_PATH, cwd=tmp_path)
    assert result.success
    assert 'not configured' in result.stdout


def test_get_provider_resolves_from_providers_array(tmp_path):
    """Test that get_provider() resolves from providers[] (canonical path)."""
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

    result = run_script(SCRIPT_PATH, cwd=tmp_path)
    assert result.returncode == 2 or 'not configured' not in result.stdout


def test_get_provider_returns_none_without_ci_entry(tmp_path):
    """Test that get_provider() returns None when no CI provider in providers array."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal = {
        'providers': [
            {
                'skill_name': 'plan-marshall:workflow-integration-sonar',
                'category': 'other',
            },
        ],
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal))

    result = run_script(SCRIPT_PATH, cwd=tmp_path)
    assert result.success
    assert 'not configured' in result.stdout


def test_get_provider_derives_from_skill_name(tmp_path):
    """Test that get_provider() derives provider key from skill_name when provider field missing."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal = {
        'providers': [
            {
                'skill_name': 'plan-marshall:workflow-integration-gitlab',
                'category': 'ci',
            },
        ],
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal))

    result = run_script(SCRIPT_PATH, cwd=tmp_path)
    # Should detect gitlab provider (derived from skill_name), not "not configured"
    assert result.returncode == 2 or 'not configured' not in result.stdout


# =============================================================================
# Path-allocate body flow — router-level regression
# =============================================================================


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


def _sig(name, state, head):
    return (name, state, head)


def test_barrier_all_settled_is_complete():
    """Every signal settled at the settled HEAD -> barrier_status: complete."""
    result = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'settled', _H1), _sig('review', 'settled', _H1), _sig('sonar', 'settled', _H1)],
        _H1,
    )
    assert result['barrier_status'] == 'complete'
    assert result['proceed'] == ['ci', 'review', 'sonar']
    assert result['pending'] == []
    assert result['affected'] == []


def test_barrier_pending_signal_is_waiting_and_proceeds_settled_arms():
    """A pending arm -> waiting; the already-settled arms still surface in proceed.

    This is the per-signal-proceed property: wall time approaches max(signal)
    because settled arms are reported independently of the slowest pending one.
    """
    result = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'settled', _H1), _sig('review', 'pending', ''), _sig('sonar', 'settled', _H1)],
        _H1,
    )
    assert result['barrier_status'] == 'waiting'
    assert result['proceed'] == ['ci', 'sonar']
    assert result['pending'] == ['review']


def test_barrier_failed_at_settled_head_is_failed():
    """A signal terminally failed at the settled HEAD -> barrier_status: failed."""
    result = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'failed', _H1), _sig('review', 'settled', _H1), _sig('sonar', 'settled', _H1)],
        _H1,
    )
    assert result['barrier_status'] == 'failed'
    assert result['failed'] == ['ci']
    assert result['affected'] == []


def test_barrier_stale_settled_signal_triggers_re_settle():
    """A settled signal observed at a stale HEAD -> re_settle, naming the affected arm.

    A finding posted after barrier entry was fixed and pushed, advancing HEAD
    from _H1 to _H2; the sonar arm settled against the now-stale _H1 and must be
    re-entered against _H2 (affected signals only).
    """
    result = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'settled', _H2), _sig('review', 'settled', _H2), _sig('sonar', 'settled', _H1)],
        _H2,
    )
    assert result['barrier_status'] == 're_settle'
    assert result['affected'] == ['sonar']
    # The arms already at the new HEAD proceed; only the stale one is affected.
    assert result['proceed'] == ['ci', 'review']


def test_barrier_re_settle_takes_precedence_over_failed_and_pending():
    """re_settle wins over a concurrent failed/pending signal (HEAD advanced)."""
    result = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'settled', _H1), _sig('review', 'pending', ''), _sig('sonar', 'failed', _H2)],
        _H2,
    )
    # ci was settled at the stale _H1 -> affected; the failed sonar is at the
    # current head, but the stale settled ci forces a re_settle first.
    assert result['barrier_status'] == 're_settle'
    assert result['affected'] == ['ci']


def test_barrier_bounded_re_settle_converges_next_iteration():
    """After re-entering the affected arm against the new HEAD, the barrier completes.

    Models the <=1-2 iteration convergence: iteration 1 pushed a fix (HEAD -> _H2)
    and left sonar stale; iteration 2 re-waits sonar against _H2 with no new
    finding, so every arm is settled at _H2 -> complete.
    """
    iteration_2 = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'settled', _H2), _sig('review', 'settled', _H2), _sig('sonar', 'settled', _H2)],
        _H2,
    )
    assert iteration_2['barrier_status'] == 'complete'
    assert iteration_2['affected'] == []


def test_barrier_invalid_state_raises_value_error():
    """An out-of-vocabulary signal state raises ValueError from the state machine."""
    with pytest.raises(ValueError, match='invalid signal state'):
        _ci_barrier.compute_barrier_state([_sig('ci', 'green', _H1)], _H1)


def test_barrier_parse_signal_forms():
    """NAME:STATE, NAME:STATE:HEAD, and NAME:STATE: (empty head) all parse."""
    assert _ci_barrier._parse_signal('review:pending') == ('review', 'pending', '')
    assert _ci_barrier._parse_signal('ci:settled:abc') == ('ci', 'settled', 'abc')
    assert _ci_barrier._parse_signal('sonar:settled:') == ('sonar', 'settled', '')


def test_barrier_parse_signal_rejects_missing_state():
    """A bare NAME with no STATE is rejected."""
    with pytest.raises(ValueError, match='expected NAME:STATE'):
        _ci_barrier._parse_signal('ci')


# --- Router-level `ci barrier` CLI wiring (intercepted before provider) ------


def test_router_barrier_waiting_without_provider(tmp_path):
    """`ci barrier` is provider-agnostic — it works with no CI provider configured."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text(json.dumps({'providers': []}))

    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H1,
        '--signal',
        f'ci:settled:{_H1}',
        '--signal',
        'review:pending',
        '--signal',
        f'sonar:settled:{_H1}',
        cwd=tmp_path,
    )
    assert result.success, f'barrier failed: {result.stderr}'
    # Provider-agnostic: never routes to the "not configured" provider path.
    assert 'not configured' not in result.stdout
    assert 'barrier_status: waiting' in result.stdout


def test_router_barrier_complete(tmp_path):
    """All arms settled at the settled HEAD -> complete via the CLI."""
    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H1,
        '--signal',
        f'ci:settled:{_H1}',
        '--signal',
        f'review:settled:{_H1}',
        '--signal',
        f'sonar:settled:{_H1}',
        cwd=tmp_path,
    )
    assert result.success
    assert 'barrier_status: complete' in result.stdout


def test_router_barrier_re_settle_names_affected(tmp_path):
    """A stale settled arm -> re_settle with the affected arm named in the TOON."""
    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H2,
        '--signal',
        f'ci:settled:{_H2}',
        '--signal',
        f'sonar:settled:{_H1}',
        cwd=tmp_path,
    )
    assert result.success
    assert 'barrier_status: re_settle' in result.stdout
    assert 'sonar' in result.stdout


def test_router_barrier_malformed_signal_is_soft_error(tmp_path):
    """A malformed --signal returns a status:error TOON (three-tier: exit 0)."""
    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H1,
        '--signal',
        'ci',
        cwd=tmp_path,
    )
    assert result.success
    assert 'status: error' in result.stdout
    assert 'invalid_signal' in result.stdout


def test_router_barrier_invalid_state_is_soft_error(tmp_path):
    """An out-of-vocabulary signal state returns a status:error TOON."""
    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H1,
        '--signal',
        f'ci:green:{_H1}',
        cwd=tmp_path,
    )
    assert result.success
    assert 'status: error' in result.stdout
    assert 'invalid_signal_state' in result.stdout


# =============================================================================
# Barrier-detach / wake decision surface (await-long-running finalize-barrier)
# =============================================================================
#
# D5 routes the barrier through the await-long-running detach seam. Detach/wake
# itself is orchestration (no script), but the seam's wake DECISIONS are driven
# by the pure `ci barrier` decision function: the seam wakes on a signal state
# transition (per-signal-proceed), stays parked while every arm is pending
# (until budget exhaustion), and — being pure — returns the identical decision
# whether awaited detached or via the synchronous fallback. These tests frame
# that decision surface deterministically.


def test_barrier_transition_wake_sequence_proceeds_per_signal():
    """A pending->settled transition on one arm wakes the barrier to proceed it.

    Models successive wakes: the seam parks on `waiting`, wakes when the review
    arm transitions pending->settled (per-signal-proceed advances it while sonar
    is still pending), then wakes again to `complete` once sonar settles.
    """
    # Wake 1: review still pending — only ci has settled.
    wake1 = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'settled', _H1), _sig('review', 'pending', ''), _sig('sonar', 'pending', '')],
        _H1,
    )
    assert wake1['barrier_status'] == 'waiting'
    assert wake1['proceed'] == ['ci']

    # Wake 2: review transitioned settled — the barrier proceeds it while still
    # awaiting sonar (per-signal-proceed, not all-or-nothing).
    wake2 = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'settled', _H1), _sig('review', 'settled', _H1), _sig('sonar', 'pending', '')],
        _H1,
    )
    assert wake2['barrier_status'] == 'waiting'
    assert wake2['proceed'] == ['ci', 'review']
    assert wake2['pending'] == ['sonar']

    # Wake 3: sonar settled — the barrier completes.
    wake3 = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'settled', _H1), _sig('review', 'settled', _H1), _sig('sonar', 'settled', _H1)],
        _H1,
    )
    assert wake3['barrier_status'] == 'complete'


def test_barrier_budget_exhaustion_proxy_stays_waiting():
    """An all-pending barrier stays `waiting` on every poll — the seam's budget-exhaustion input.

    The detach seam wakes on transition OR budget exhaustion; a barrier whose
    arms never leave `pending` is exactly the state the seam times out on. The
    decision function reports `waiting` with every arm still pending — never a
    spurious `complete` — so the seam's budget path is reached rather than a
    false settle.
    """
    result = _ci_barrier.compute_barrier_state(
        [_sig('ci', 'pending', ''), _sig('review', 'pending', ''), _sig('sonar', 'pending', '')],
        _H1,
    )
    assert result['barrier_status'] == 'waiting'
    assert result['pending'] == ['ci', 'review', 'sonar']
    assert result['proceed'] == []


def test_barrier_synchronous_fallback_decision_is_identical_to_detached():
    """The decision is pure — detached and synchronous-fallback awaits agree.

    `compute_barrier_state` depends only on its inputs, not on HOW the arms were
    awaited, so the await-long-running synchronous fallback (step g) yields the
    byte-identical decision as the detached path for the same signal snapshot.
    This is the property that lets the fallback stay behaviourally identical.
    """
    signals = [_sig('ci', 'settled', _H1), _sig('review', 'pending', ''), _sig('sonar', 'settled', _H1)]
    detached = _ci_barrier.compute_barrier_state(signals, _H1)
    synchronous = _ci_barrier.compute_barrier_state(list(signals), _H1)
    assert detached == synchronous


def test_barrier_re_settle_wake_re_enters_affected_arms_only(tmp_path):
    """A post-entry push wakes the barrier to re_settle only the affected arms (via CLI).

    Models the bounded-re-settle wake: a fix pushed after barrier entry advanced
    HEAD to _H2; the review arm settled against the stale _H1 and is the sole
    `affected` arm the seam re-detaches — never the arms already at _H2, and
    never a full replay.
    """
    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H2,
        '--signal',
        f'ci:settled:{_H2}',
        '--signal',
        f'review:settled:{_H1}',
        '--signal',
        f'sonar:settled:{_H2}',
        cwd=tmp_path,
    )
    assert result.success
    assert 'barrier_status: re_settle' in result.stdout
    # Only the stale review arm is re-entered; ci/sonar already at _H2 proceed.
    assert 'review' in result.stdout
