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
# Step not recorded -> not recorded / error under --require-terminal
# =============================================================================

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


# =============================================================================
# Legacy-vs-canonical duplicate: the fresher canonical write must win over a
# stale legacy (``default:``-prefixed) key inserted earlier in the dict.
# =============================================================================


def test_canonical_exact_match_wins_over_stale_legacy_prefixed_key(plan_context):
    """When both a stale legacy ``default:push`` key and a fresh canonical ``push``
    key are present (legacy inserted first, per dict insertion order), the read
    side must prefer the exact canonical match and report the FRESH outcome, not
    the stale legacy one the ordered scan would hit first.

    A scan that breaks on the first canonical match lets the earlier-inserted
    ``default:push`` entry (a pre-migration write) shadow the newer ``push``
    write, so the read reports a stale outcome as the current one.
    """
    plan_id = 'assert-legacy-shadow'
    _make_plan(plan_id)
    status = read_status(plan_id)
    # Insertion order: stale legacy key first, fresh canonical key second.
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {
            'default:push': {'outcome': 'failed', 'display_detail': 'stale legacy'},
            'push': {'outcome': 'done', 'display_detail': 'fresh canonical'},
        }
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'push', require_terminal=True))

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'


# =============================================================================
# Near-miss orphan key -> step_record_mismatched_key
# =============================================================================

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


# =============================================================================
# Canonical step-key round-trip: a bare↔default: / promoted-alias variant
# recorded with one spelling resolves as a canonical MATCH when queried with the
# variant spelling (shared canonicalize_step_key on both write and read).
# =============================================================================


def test_default_prefixed_record_matches_bare_query(plan_context):
    """Record via ``default:push`` then assert via ``push`` → recorded (no mismatch).

    Both the write (mark-step-done) and the read (assert-step-recorded) route the
    step through the shared canonicalizer, so a ``default:``-prefixed record
    reconciles to a canonical MATCH under the bare query.
    """
    plan_id = 'assert-canon-default-to-bare'
    _make_plan(plan_id)
    _seed_step(plan_id, '6-finalize', 'default:push', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'push', require_terminal=True))

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'
    assert result['step'] == 'push'


def test_promoted_alias_record_matches_bare_query(plan_context):
    """Record via ``plan-marshall:automatic-review`` then assert via bare
    ``automatic-review`` → recorded (the promoted-alias map reconciles both)."""
    plan_id = 'assert-canon-promoted-alias'
    _make_plan(plan_id)
    # ``automatic-review`` declares head_dependent: true, so the seed carries an
    # anchor. What this case pins is the promoted-alias key reconciliation, not
    # the anchor — but without it the production verb refuses the seed and there
    # would be no record to query.
    _seed_step(
        plan_id,
        '6-finalize',
        'plan-marshall:automatic-review',
        'done',
        head_at_completion='d' * 40,
    )

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'automatic-review', require_terminal=True)
    )

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'


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
