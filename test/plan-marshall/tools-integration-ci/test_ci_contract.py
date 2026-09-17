#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Contract cluster — provider, barrier core, TOON contracts."""


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


# The three finalize-wait barrier signals, per phase-6-finalize.
_H1 = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'  # settled HEAD
_H2 = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'  # post-re-settle HEAD


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
    """An out-of-vocabulary signal state raises ValueError from the state machine.

    The snapshot is COMPLETE (one record per arm) so the completeness check
    passes and the per-signal state validation is what rejects the bad state.
    """
    with pytest.raises(ValueError, match='invalid signal state'):
        _ci_barrier.compute_barrier_state(
            [_sig('ci', 'green', _H1), _sig('review', 'settled', _H1), _sig('sonar', 'settled', _H1)],
            _H1,
        )


def test_barrier_missing_arm_raises():
    """A snapshot missing an arm is rejected fail-loud (never decided over)."""
    with pytest.raises(_ci_barrier.BarrierSignalSetError, match='missing'):
        _ci_barrier.compute_barrier_state(
            [_sig('ci', 'settled', _H1), _sig('review', 'settled', _H1)],
            _H1,
        )


def test_barrier_duplicate_arm_raises():
    """A snapshot with a duplicate arm record is rejected fail-loud."""
    with pytest.raises(_ci_barrier.BarrierSignalSetError, match='duplicate'):
        _ci_barrier.compute_barrier_state(
            [
                _sig('ci', 'settled', _H1),
                _sig('ci', 'settled', _H1),
                _sig('review', 'settled', _H1),
                _sig('sonar', 'settled', _H1),
            ],
            _H1,
        )


def test_barrier_unknown_name_raises():
    """A snapshot carrying an unknown signal name is rejected fail-loud."""
    with pytest.raises(_ci_barrier.BarrierSignalSetError, match='unknown'):
        _ci_barrier.compute_barrier_state(
            [
                _sig('ci', 'settled', _H1),
                _sig('review', 'settled', _H1),
                _sig('sonar', 'settled', _H1),
                _sig('lint', 'settled', _H1),
            ],
            _H1,
        )


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


def test_router_barrier_invalid_state_is_soft_error(tmp_path):
    """An out-of-vocabulary signal state returns a status:error TOON.

    The arm set is complete so completeness passes first; the bad state is what
    surfaces the invalid_signal_state error.
    """
    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H1,
        '--signal',
        f'ci:green:{_H1}',
        '--signal',
        f'review:settled:{_H1}',
        '--signal',
        f'sonar:settled:{_H1}',
        cwd=tmp_path,
    )
    assert result.success
    assert 'status: error' in result.stdout
    assert 'invalid_signal_state' in result.stdout


def test_router_barrier_missing_arm_is_soft_error(tmp_path):
    """A snapshot missing an arm returns a status:error incomplete_signals TOON."""
    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H1,
        '--signal',
        f'ci:settled:{_H1}',
        '--signal',
        f'review:settled:{_H1}',
        cwd=tmp_path,
    )
    assert result.success
    assert 'status: error' in result.stdout
    assert 'incomplete_signals' in result.stdout


def test_router_barrier_duplicate_arm_is_soft_error(tmp_path):
    """A snapshot with a duplicate arm returns a status:error incomplete_signals TOON."""
    result = run_script(
        SCRIPT_PATH,
        'barrier',
        '--settled-head',
        _H1,
        '--signal',
        f'ci:settled:{_H1}',
        '--signal',
        f'ci:settled:{_H1}',
        '--signal',
        f'review:settled:{_H1}',
        '--signal',
        f'sonar:settled:{_H1}',
        cwd=tmp_path,
    )
    assert result.success
    assert 'status: error' in result.stdout
    assert 'incomplete_signals' in result.stdout


def test_router_barrier_unknown_name_is_soft_error(tmp_path):
    """A snapshot carrying an unknown signal name returns incomplete_signals."""
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
        '--signal',
        f'lint:settled:{_H1}',
        cwd=tmp_path,
    )
    assert result.success
    assert 'status: error' in result.stdout
    assert 'incomplete_signals' in result.stdout


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


