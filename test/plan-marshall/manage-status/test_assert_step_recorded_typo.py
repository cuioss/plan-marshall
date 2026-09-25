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

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'plan-retrospective', require_terminal=True))

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_mismatched_key'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert result['orphan_key'] == 'plan-retrospectiv'
    assert result['orphan_outcome'] == 'done'
    assert result['phase'] == '6-finalize'
    assert result['step'] == 'plan-retrospective'
