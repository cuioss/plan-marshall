#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script."""


from _manage_findings_fixtures import (
    SCRIPT_PATH,
    _add_ns,
    _qgate_add_ns,
    _qgate_query_ns,
    _query_ns,
    cmd_add,
    cmd_qgate_add,
    cmd_qgate_query,
    cmd_query,
    query_findings_unified,
)
from toon_parser import parse_toon  # noqa: E402

from conftest import run_script


def test_backward_compat_list_without_include_qgate(plan_context):
    """(d) Existing list call shape (no --include-qgate) keeps its original shape."""
    pid = 'compat-list'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Plan bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='QG finding', detail='d'
        )
    )

    plain = cmd_query(_query_ns(plan_id=pid))
    assert plain['status'] == 'success'
    # No q-gate provenance keys; q-gate finding is NOT merged.
    assert 'qgate_included' not in plain
    assert 'plan_count' not in plain
    assert plain['filtered_count'] == 1
    assert plain['findings'][0]['title'] == 'Plan bug'


def test_backward_compat_qgate_list_unaffected(plan_context):
    """(d) The narrowed qgate list call shape is unchanged by the unified surface."""
    pid = 'compat-qgate-list'
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='3-outline', source='qgate', type='triage', title='QG fd', detail='d'
        )
    )

    result = cmd_qgate_query(_qgate_query_ns(plan_id=pid, phase='3-outline'))
    assert result['status'] == 'success'
    assert result['phase'] == '3-outline'
    assert result['total_count'] == 1
    assert result['filtered_count'] == 1
    # Per-phase qgate list does NOT carry the unified provenance markers.
    assert 'qgate_included' not in result


def test_unified_query_core_direct(plan_context):
    """Direct core call (bypassing CLI namespace) merges plan + pending q-gate."""
    pid = 'unified-core-direct'
    cmd_add(_add_ns(plan_id=pid, type='bug', title='Core plan bug', detail='d'))
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id=pid, phase='5-execute', source='qgate', type='triage', title='Core QG', detail='d'
        )
    )

    unified = query_findings_unified(pid)
    assert unified['qgate_included'] is True
    assert unified['plan_count'] == 1
    assert unified['qgate_count'] == 1
    titles = {f['title'] for f in unified['findings']}
    assert titles == {'Core plan bug', 'Core QG'}


def test_cli_unified_list_include_qgate_roundtrip(plan_context):
    """CLI plumbing: list --include-qgate merges plan + q-gate via subprocess."""
    pid = 'cli-unified-rt'
    add_result = run_script(
        SCRIPT_PATH, 'add', '--plan-id', pid, '--type', 'bug', '--title', 'CLI plan bug', '--detail', 'd'
    )
    assert add_result.success, f'Script failed: {add_result.stderr}'
    qgate_result = run_script(
        SCRIPT_PATH,
        'qgate',
        'add',
        '--plan-id',
        pid,
        '--phase',
        '5-execute',
        '--source',
        'qgate',
        '--type',
        'triage',
        '--title',
        'CLI QG',
        '--detail',
        'd',
    )
    assert qgate_result.success, f'Script failed: {qgate_result.stderr}'

    # Default list: only the plan finding.
    plain = run_script(SCRIPT_PATH, 'list', '--plan-id', pid)
    assert plain.success
    plain_data = parse_toon(plain.stdout)
    assert plain_data['filtered_count'] == 1

    # Unified list: plan + pending q-gate finding.
    unified = run_script(SCRIPT_PATH, 'list', '--plan-id', pid, '--include-qgate')
    assert unified.success, f'Script failed: {unified.stderr}'
    unified_data = parse_toon(unified.stdout)
    assert unified_data['qgate_included'] is True
    assert unified_data['filtered_count'] == 2


# =============================================================================
# CLI Plumbing Tests (subprocess)
# =============================================================================


def test_cli_add_and_query_roundtrip(plan_context):
    """CLI plumbing: add a finding and query it back via subprocess."""
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        'test-plan',
        '--type',
        'bug',
        '--title',
        'CLI roundtrip test',
        '--detail',
        'Testing CLI plumbing',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'

    query_result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan')
    assert query_result.success
    query_data = parse_toon(query_result.stdout)
    assert query_data['total_count'] == 1


def test_cli_add_raw_input_roundtrip(plan_context):
    """CLI plumbing: --raw-input FIELD=VALUE quarantines free-text under raw_input.{field}."""
    pid = 'cli-rawinput-rt'
    add_result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        pid,
        '--type',
        'pr-comment',
        '--title',
        'CLI raw comment',
        '--detail',
        'd',
        '--raw-input',
        'body=untrusted reviewer text',
    )
    assert add_result.success, f'Script failed: {add_result.stderr}'

    get_result = run_script(SCRIPT_PATH, 'list', '--plan-id', pid, '--type', 'pr-comment')
    assert get_result.success, f'Script failed: {get_result.stderr}'
    data = parse_toon(get_result.stdout)
    assert data['filtered_count'] == 1


def test_cli_add_raw_input_malformed_rejected(plan_context):
    """CLI plumbing: a --raw-input value with no '=' returns a structured error."""
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        'cli-rawinput-bad',
        '--type',
        'bug',
        '--title',
        'Bad raw input',
        '--detail',
        'd',
        '--raw-input',
        'no-equals-sign',
    )
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    assert data.get('status') == 'error'


def test_cli_qgate_add_and_clear_roundtrip(plan_context):
    """CLI plumbing: add Q-Gate finding and clear via subprocess."""
    add_result = run_script(
        SCRIPT_PATH,
        'qgate',
        'add',
        '--plan-id',
        'cli-qgate-rt',
        '--phase',
        '3-outline',
        '--source',
        'qgate',
        '--type',
        'triage',
        '--title',
        'CLI qgate test',
        '--detail',
        'Testing CLI plumbing',
    )
    assert add_result.success, f'Script failed: {add_result.stderr}'

    clear_result = run_script(SCRIPT_PATH, 'qgate', 'clear', '--plan-id', 'cli-qgate-rt', '--phase', '3-outline')
    assert clear_result.success
    clear_data = parse_toon(clear_result.stdout)
    assert clear_data['cleared'] == 1
