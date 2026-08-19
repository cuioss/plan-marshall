#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
"""


from _manage_findings_fixtures import SCRIPT_PATH

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # noqa: E402

from conftest import run_script

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
