# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    cmd_assert_step_recorded,
    read_status,
    write_status,
)

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
