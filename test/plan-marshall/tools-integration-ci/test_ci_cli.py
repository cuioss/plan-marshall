#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI cluster — barrier router dispatch, body consumers, reinjection."""

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
        f'review:settled:{_H2}',
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


def test_body_consumer_verbs_cover_reply_thread_reply_comment():
    """Router reinjection must cover reply, thread-reply and comment.

    These three verbs declare a required --plan-id via add_body_consumer_args;
    a router-position --plan-id consumed for worktree resolution must be
    reinjected for them, exactly as for create/edit/prepare-body/prepare-comment.
    """
    assert {'reply', 'thread-reply', 'comment'} <= set(ci_module._BODY_CONSUMER_VERBS)


def test_body_consumer_verbs_mirror_ci_base():
    """The reinjection set must not drift from the parser registrations in ci_base."""
    import ci_base

    assert ci_module._BODY_CONSUMER_VERBS == ci_base.BODY_CONSUMER_VERBS


def test_router_reinjection_triggers_for_reply_and_thread_reply():
    """A remaining argv carrying reply/thread-reply without --plan-id triggers reinjection."""
    for verb_argv in (['pr', 'reply'], ['pr', 'thread-reply'], ['issue', 'comment']):
        assert any(v in verb_argv for v in ci_module._BODY_CONSUMER_VERBS)
