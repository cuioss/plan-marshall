#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script.

Its one section: CLI Plumbing Tests (subprocess).
"""


from _manage_findings_fixtures import SCRIPT_PATH
from toon_parser import parse_toon

from conftest import run_script

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = (
    'cli-prc-badbotkind',
    'cli-prc-badkind',
    'cli-prc-rcs-rt',
    'cli-prc-rt',
    'cli-qgate-rt',
    'cli-rawinput-bad',
    'cli-rawinput-rt',
    'cli-unified-rt',
    'test-plan',
)


def test_cli_pr_comment_author_kind_roundtrip(plan_context):
    """CLI plumbing: add a pr-comment with --author/--kind and read them back."""
    pid = 'cli-prc-rt'
    add_result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        pid,
        '--type',
        'pr-comment',
        '--title',
        'CLI reviewer comment',
        '--detail',
        'd',
        '--author',
        'octocat',
        '--kind',
        'inline',
    )
    assert add_result.success, f'Script failed: {add_result.stderr}'

    list_result = run_script(SCRIPT_PATH, 'list', '--plan-id', pid, '--author', 'octocat', '--kind', 'inline')
    assert list_result.success, f'Script failed: {list_result.stderr}'
    data = parse_toon(list_result.stdout)
    assert data['filtered_count'] == 1


def test_cli_pr_comment_invalid_kind_rejected(plan_context):
    """CLI plumbing: --kind outside the allowed set is rejected by argparse."""
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        'cli-prc-badkind',
        '--type',
        'pr-comment',
        '--title',
        'Bad kind',
        '--detail',
        'd',
        '--kind',
        'not-a-kind',
    )
    assert not result.success


def test_cli_pr_comment_reviewed_commit_sha_bot_kind_roundtrip(plan_context):
    """CLI plumbing: add a pr-comment with --reviewed-commit-sha/--bot-kind and read them back."""
    pid = 'cli-prc-rcs-rt'
    add_result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        pid,
        '--type',
        'pr-comment',
        '--title',
        'CLI bot comment',
        '--detail',
        'd',
        '--reviewed-commit-sha',
        'deadbeef',
        '--bot-kind',
        'coderabbit',
    )
    assert add_result.success, f'Script failed: {add_result.stderr}'

    list_result = run_script(SCRIPT_PATH, 'list', '--plan-id', pid, '--bot-kind', 'coderabbit')
    assert list_result.success, f'Script failed: {list_result.stderr}'
    data = parse_toon(list_result.stdout)
    assert data['filtered_count'] == 1


def test_cli_pr_comment_invalid_bot_kind_rejected(plan_context):
    """CLI plumbing: --bot-kind outside the allowed set is rejected by argparse."""
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        'cli-prc-badbotkind',
        '--type',
        'pr-comment',
        '--title',
        'Bad bot_kind',
        '--detail',
        'd',
        '--bot-kind',
        'sonarcloud',
    )
    assert not result.success


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
