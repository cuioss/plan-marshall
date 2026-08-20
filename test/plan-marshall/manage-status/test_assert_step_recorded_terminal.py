#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the assert-step-recorded subcommand of manage-status."""


import pytest
from _assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    _seed_step,
    cmd_assert_step_recorded,
    read_status,
    write_status,
)

# =============================================================================
# Step recorded and terminal -> success
# =============================================================================


def test_recorded_terminal_done_returns_success(plan_context):
    """A step recorded with a terminal 'done' outcome reports recorded=true."""
    plan_id = 'assert-recorded-done'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-a'))

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'
    assert result['phase'] == '1-init'
    assert result['step'] == 'step-a'


def test_recorded_terminal_done_with_require_terminal_returns_success(plan_context):
    """--require-terminal on a recorded terminal step still reports success."""
    plan_id = 'assert-recorded-require'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-a', require_terminal=True))

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'


@pytest.mark.parametrize('outcome', ['done', 'skipped', 'loop_back', 'failed'])
def test_each_terminal_outcome_counts_as_recorded(plan_context, outcome):
    """Every member of VALID_OUTCOMES counts as a terminal record."""
    plan_id = f'assert-terminal-{outcome.replace("_", "-")}'
    _make_plan(plan_id)
    # Seed directly to avoid the may-mutate / loop_back-target machinery of
    # cmd_mark_step_done; the verb under test reads the persisted dict shape.
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '2-refine': {'clarify': {'outcome': outcome, 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(_assert_args(plan_id, '2-refine', 'clarify', require_terminal=True))

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == outcome


# =============================================================================
# Step recorded but non-terminal value -> not recorded
# =============================================================================


def test_non_terminal_outcome_not_recorded(plan_context):
    """A dict entry with an out-of-vocabulary outcome does NOT count as recorded."""
    plan_id = 'assert-non-terminal'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '5-execute': {'impl': {'outcome': 'in_progress', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(_assert_args(plan_id, '5-execute', 'impl'))

    assert result['status'] == 'success'
    assert result['recorded'] is False
    assert result['outcome'] is None


def test_non_terminal_with_require_terminal_returns_error(plan_context):
    """--require-terminal escalates a recorded-but-non-terminal step to step_record_missing."""
    plan_id = 'assert-non-terminal-require'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '5-execute': {'impl': {'outcome': 'in_progress', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(_assert_args(plan_id, '5-execute', 'impl', require_terminal=True))

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_missing'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert result['phase'] == '5-execute'
    assert result['step'] == 'impl'


def test_non_terminal_near_miss_does_not_escalate_to_mismatched_key(plan_context):
    """A near-miss orphan whose outcome is NON-terminal must NOT trigger the
    mismatched-key branch — only a terminal orphan record counts as a near-miss.
    With no terminal record under any key, the verdict is step_record_missing."""
    plan_id = 'assert-near-miss-nonterminal'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospectiv': {'outcome': 'in_progress', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_missing'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert 'orphan_key' not in result


def test_bare_string_legacy_entry_not_recorded(plan_context):
    """A legacy bare-string entry is not a dict, so it does NOT count as recorded."""
    plan_id = 'assert-legacy-string'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {'1-init': {'step-a': 'done'}}
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-a'))

    assert result['status'] == 'success'
    assert result['recorded'] is False
    assert result['outcome'] is None


def test_bare_record_matches_default_prefixed_query(plan_context):
    """Record via ``push`` then assert via ``default:push`` → recorded (no mismatch)."""
    plan_id = 'assert-canon-bare-to-default'
    _make_plan(plan_id)
    _seed_step(plan_id, '6-finalize', 'push', 'done')

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'default:push', require_terminal=True)
    )

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'


# =============================================================================
# Step not recorded -> not recorded / error under --require-terminal
# =============================================================================


def test_step_absent_returns_not_recorded(plan_context):
    """A step never marked reports recorded=false under the default (no escalation)."""
    plan_id = 'assert-absent-step'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-missing'))

    assert result['status'] == 'success'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert result['phase'] == '1-init'
    assert result['step'] == 'step-missing'


def test_step_absent_with_require_terminal_returns_error(plan_context):
    """--require-terminal on an absent step escalates to step_record_missing.

    A terminal record under a completely unrelated key in the same phase does NOT
    trigger step_record_mismatched_key — near-miss detection is restricted to
    genuine near-misses (bare/qualified name variants or close typographic errors).
    An unrelated key like ``step-a`` is not a near-miss for ``step-missing``."""
    plan_id = 'assert-absent-require'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-missing', require_terminal=True))

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_missing'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert result['phase'] == '1-init'
    assert result['step'] == 'step-missing'
