#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the assert-step-recorded subcommand of manage-status.

The verb is the read-only post-dispatch guard the phase-6-finalize dispatcher
calls after every dispatched-step return to detect the silent gap where a step
returns ``status: success`` but skips its mandated ``mark-step-done``
side-effect. A record counts as *recorded* iff a dict entry with a terminal
``outcome`` in ``{done, skipped, loop_back, failed}`` exists under
``status.metadata.phase_steps[phase][step]``. The verb performs zero writes.
"""

from argparse import Namespace

import pytest

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_assert_step_lifecycle')
_assert_step = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_assert_step_recorded.py', '_assert_step_cmd'
)
_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_assert_step_mark_step')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_assert_step_core')

cmd_create = _lifecycle.cmd_create
cmd_assert_step_recorded = _assert_step.cmd_assert_step_recorded
cmd_mark_step_done = _mark_step.cmd_mark_step_done
read_status = _status_core.read_status
write_status = _status_core.write_status


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Assert Step Recorded Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _mark_args(plan_id: str, phase: str, step: str, outcome: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=False,
        display_detail=None,
        head_at_completion=None,
        loop_back_target=None,
    )


def _assert_args(plan_id: str, phase: str, step: str, require_terminal: bool = False) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        require_terminal=require_terminal,
    )


def _seed_step(plan_id: str, phase: str, step: str, outcome: str) -> None:
    """Mark a step done via the production verb (clean-worktree stubbed for may-mutate steps)."""
    cmd_mark_step_done(_mark_args(plan_id, phase, step, outcome))


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


def test_phase_absent_returns_not_recorded(plan_context):
    """A phase with no recorded steps reports recorded=false."""
    plan_id = 'assert-absent-phase'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'push'))

    assert result['status'] == 'success'
    assert result['recorded'] is False
    assert result['outcome'] is None


def test_phase_absent_with_require_terminal_returns_error(plan_context):
    """--require-terminal on a phase with no steps escalates to step_record_missing."""
    plan_id = 'assert-absent-phase-require'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'push', require_terminal=True))

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_missing'
    assert result['recorded'] is False


# =============================================================================
# No steps recorded at all (no phase_steps metadata) -> not recorded
# =============================================================================


def test_no_phase_steps_metadata_returns_not_recorded(plan_context):
    """A freshly created plan with no phase_steps metadata reports recorded=false."""
    plan_id = 'assert-no-steps'
    _make_plan(plan_id)

    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-a'))

    assert result['status'] == 'success'
    assert result['recorded'] is False
    assert result['outcome'] is None


def test_no_phase_steps_metadata_with_require_terminal_returns_error(plan_context):
    """--require-terminal with no phase_steps metadata escalates to step_record_missing."""
    plan_id = 'assert-no-steps-require'
    _make_plan(plan_id)

    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-a', require_terminal=True))

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_missing'
    assert result['recorded'] is False
    assert result['outcome'] is None


def test_assert_does_not_mutate_status(plan_context):
    """The verb is read-only: the persisted status.json is byte-identical after a call."""
    plan_id = 'assert-no-mutation'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    before = read_status(plan_id)
    cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-a', require_terminal=True))
    cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-missing'))
    after = read_status(plan_id)

    assert before == after


# =============================================================================
# Near-miss orphan key -> step_record_mismatched_key
# =============================================================================


def test_canonical_key_present_is_recorded_terminal(plan_context):
    """(1) When the queried (canonical) key carries a terminal record, the verb
    reports recorded/terminal even if other orphan keys also exist — the
    near-miss scan never fires when the canonical record is present."""
    plan_id = 'assert-mismatch-canonical'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {
            'plan-marshall:plan-retrospective': {'outcome': 'done', 'display_detail': None},
            'plan-retrospective': {'outcome': 'done', 'display_detail': None},
        }
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'


def test_only_bare_orphan_present_returns_mismatched_key(plan_context):
    """(2) When only a bare/mis-keyed orphan terminal record is present under a
    different key, --require-terminal returns step_record_mismatched_key carrying
    the orphan key and its outcome."""
    plan_id = 'assert-mismatch-orphan'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospective': {'outcome': 'done', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_mismatched_key'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert result['orphan_key'] == 'plan-retrospective'
    assert result['orphan_outcome'] == 'done'
    assert result['phase'] == '6-finalize'
    assert result['step'] == 'plan-marshall:plan-retrospective'


def test_no_record_at_all_returns_missing_not_mismatched(plan_context):
    """(3) Regression guard: when no terminal record exists under ANY key in the
    phase, --require-terminal returns the original step_record_missing — the
    near-miss branch must not fire for a truly-absent record."""
    plan_id = 'assert-mismatch-none'
    _make_plan(plan_id)
    status = read_status(plan_id)
    # A non-terminal orphan must NOT trigger the mismatched-key branch.
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'some-other-step': {'outcome': 'in_progress', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_missing'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert 'orphan_key' not in result


def test_orphan_present_without_require_terminal_does_not_flip_recorded(plan_context):
    """(4) Without --require-terminal, a present orphan under a different key does
    not flip recorded for the queried key — the default path reports the queried
    key absent without escalation."""
    plan_id = 'assert-mismatch-default'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospective': {'outcome': 'done', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=False)
    )

    assert result['status'] == 'success'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert 'orphan_key' not in result


# =============================================================================
# Near-miss token hardening: tokens close to a valid step_id but not an exact
# match must escalate to step_record_mismatched_key under --require-terminal.
# =============================================================================


def test_typo_near_miss_token_returns_mismatched_key(plan_context):
    """A typo'd orphan key (one character off the queried step_id) carries a
    terminal record; the queried exact step_id has none. --require-terminal must
    surface the typo'd key via step_record_mismatched_key rather than silently
    passing or reporting a truly-absent record."""
    plan_id = 'assert-near-miss-typo'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospectiv': {'outcome': 'done', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_mismatched_key'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert result['orphan_key'] == 'plan-retrospectiv'
    assert result['orphan_outcome'] == 'done'
    assert result['phase'] == '6-finalize'
    assert result['step'] == 'plan-retrospective'


@pytest.mark.parametrize('orphan_outcome', ['done', 'skipped', 'loop_back', 'failed'])
def test_near_miss_orphan_outcome_preserved(plan_context, orphan_outcome):
    """The mismatched-key verdict surfaces the orphan's actual terminal outcome,
    not a hard-coded 'done'. Every member of VALID_OUTCOMES under a near-miss key
    must round-trip through orphan_outcome."""
    plan_id = f'assert-near-miss-{orphan_outcome.replace("_", "-")}'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospective': {'outcome': orphan_outcome, 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_mismatched_key'
    assert result['orphan_key'] == 'plan-retrospective'
    assert result['orphan_outcome'] == orphan_outcome


def test_near_miss_message_names_both_keys(plan_context):
    """The mismatched-key message must name both the queried step_id and the
    near-miss orphan key so the dispatcher can report the mis-keying."""
    plan_id = 'assert-near-miss-message'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospective': {'outcome': 'done', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'error'
    assert 'plan-marshall:plan-retrospective' in result['message']
    assert 'plan-retrospective' in result['message']


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


# =============================================================================
# Error paths
# =============================================================================


def test_missing_plan_returns_none(plan_context):
    """Missing plan: require_status emits TOON and returns None."""
    result = cmd_assert_step_recorded(_assert_args('nonexistent-plan', '1-init', 'step-a'))
    assert result is None


def test_empty_phase_returns_invalid_argument(plan_context):
    """Empty phase is rejected with invalid_argument before reading metadata."""
    plan_id = 'assert-empty-phase'
    _make_plan(plan_id)
    result = cmd_assert_step_recorded(_assert_args(plan_id, '', 'step-a'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_empty_step_returns_invalid_argument(plan_context):
    """Empty step is rejected with invalid_argument before reading metadata."""
    plan_id = 'assert-empty-step'
    _make_plan(plan_id)
    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', ''))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_invalid_plan_id_raises_system_exit(plan_context):
    """Invalid plan_id format triggers require_valid_plan_id exit."""
    with pytest.raises(SystemExit):
        cmd_assert_step_recorded(_assert_args('Invalid_Plan', '1-init', 'step-a'))
