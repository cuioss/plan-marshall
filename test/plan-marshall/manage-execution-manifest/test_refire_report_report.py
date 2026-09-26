# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_refire_report_fixtures import (
    _compose_ns,
    _record_ns,
    _report_ns,
    cmd_compose,
    cmd_record_step,
    cmd_refire_report,
)

# =============================================================================
# The command over real plan state
# =============================================================================


def test_report_over_recorded_rows(plan_context):
    cmd_compose(_compose_ns('refire-plan'))
    for _ in range(3):
        cmd_record_step(_record_ns('refire-plan', 'pre-push-quality-gate', total_tokens=0))
    cmd_record_step(_record_ns('refire-plan', 'push'))

    result = cmd_refire_report(_report_ns('refire-plan'))

    assert result is not None
    assert result['status'] == 'success'
    assert result['phase'] == '6-finalize'
    assert result['totals']['refires'] == 2
    assert result['steps'][0]['step_id'] == 'pre-push-quality-gate'
    assert result['steps'][0]['refires'] == 2


def test_report_names_its_token_population(plan_context):
    """A bare number that merely looks comparable is worse than none."""
    cmd_compose(_compose_ns('refire-pop'))
    cmd_record_step(_record_ns('refire-pop', 'push'))

    result = cmd_refire_report(_report_ns('refire-pop'))

    assert result is not None
    assert 'FLOOR' in result['token_population']
    assert 'inline' in result['token_population']


def test_report_on_a_manifest_with_no_execution_log(plan_context):
    """A composed-but-unrun plan reports zeroes, not an error."""
    cmd_compose(_compose_ns('refire-empty'))

    result = cmd_refire_report(_report_ns('refire-empty'))

    assert result is not None
    assert result['status'] == 'success'
    assert result['execution_log_rows'] == 0
    assert result['steps'] == []
    assert result['totals']['refires'] == 0


def test_report_rejects_an_unknown_phase(plan_context):
    cmd_compose(_compose_ns('refire-badphase'))

    result = cmd_refire_report(_report_ns('refire-badphase', phase='9-nope'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'


def test_report_without_a_phase_covers_every_phase(plan_context):
    cmd_compose(_compose_ns('refire-allphase'))
    cmd_record_step(_record_ns('refire-allphase', 'quality-gate', phase='5-execute'))
    cmd_record_step(_record_ns('refire-allphase', 'push', phase='6-finalize'))

    result = cmd_refire_report(_report_ns('refire-allphase', phase=None))

    assert result is not None
    assert result['phase'] == 'all'
    assert result['totals']['steps'] == 2
