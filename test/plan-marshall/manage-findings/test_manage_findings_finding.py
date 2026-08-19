#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script."""


from _manage_findings_fixtures import (
    SCRIPT_PATH,
    _add_ns,
    _query_ns,
    _resolve_ns,
    cmd_add,
    cmd_query,
    cmd_resolve,
)
from toon_parser import parse_toon  # noqa: E402

from conftest import run_script

# =============================================================================
# Test: Finding Add Command
# =============================================================================


def test_finding_add_basic(plan_context):
    """Test adding a basic finding."""
    result = cmd_add(
        _add_ns(
            type='bug',
            title='Test failure in CacheTest',
            detail='AssertionError: expected 5 but got 3',
        )
    )
    assert result['status'] == 'success'
    assert 'hash_id' in result
    assert result['type'] == 'bug'


def test_finding_add_with_file_info(plan_context):
    """Test adding finding with file location."""
    result = cmd_add(
        _add_ns(
            type='sonar-issue',
            title='S1192: String literals duplicated',
            detail='String "application/json" appears 5 times',
            file_path='src/main/java/Api.java',
            line=42,
            rule='java:S1192',
            severity='warning',
        )
    )
    assert result['status'] == 'success'


def test_finding_add_all_types(plan_context):
    """Test that all finding types are accepted."""
    finding_types = [
        'bug',
        'improvement',
        'anti-pattern',
        'triage',
        'tip',
        'insight',
        'best-practice',
        'build-error',
        'test-failure',
        'lint-issue',
        'sonar-issue',
        'pr-comment',
    ]
    for ftype in finding_types:
        result = cmd_add(_add_ns(type=ftype, title=f'Test {ftype}', detail=f'Testing {ftype} type'))
        assert result['status'] == 'success', f'Failed for type {ftype}'


# =============================================================================
# Test: Finding Query Command
# =============================================================================


def test_finding_query_empty(plan_context):
    """Test querying with no findings."""
    result = cmd_query(_query_ns())
    assert result['total_count'] == 0


def test_finding_query_by_type(plan_context):
    """Test filtering findings by type."""
    cmd_add(_add_ns(type='bug', title='Bug 1', detail='d'))
    cmd_add(_add_ns(type='tip', title='Tip 1', detail='d'))
    cmd_add(_add_ns(type='bug', title='Bug 2', detail='d'))

    result = cmd_query(_query_ns(type='bug'))
    assert result['filtered_count'] == 2


def test_finding_query_by_resolution(plan_context):
    """Test filtering findings by resolution."""
    add_result = cmd_add(_add_ns(type='bug', title='Bug to fix', detail='d'))
    hash_id = str(add_result['hash_id'])

    cmd_resolve(_resolve_ns(hash_id=hash_id, resolution='fixed', detail='Fixed in commit abc'))

    result = cmd_query(_query_ns(resolution='fixed'))
    assert result['filtered_count'] == 1


# =============================================================================
# Test: pr-comment author / kind first-class fields (CLI layer)
# =============================================================================


def test_finding_add_pr_comment_with_author_and_kind(plan_context):
    """cmd_add forwards author and kind onto a pr-comment finding."""
    result = cmd_add(
        _add_ns(
            type='pr-comment',
            title='Reviewer nit',
            detail='Rename for clarity',
            author='octocat',
            kind='inline',
        )
    )
    assert result['status'] == 'success'
    assert result['type'] == 'pr-comment'

    query = cmd_query(_query_ns(type='pr-comment'))
    assert query['filtered_count'] == 1
    record = query['findings'][0]
    assert record['author'] == 'octocat'
    assert record['kind'] == 'inline'


def test_finding_query_by_author(plan_context):
    """cmd_query filters pr-comment findings by author."""
    cmd_add(_add_ns(type='pr-comment', title='C1', detail='d', author='alice', kind='inline'))
    cmd_add(_add_ns(type='pr-comment', title='C2', detail='d', author='bob', kind='inline'))

    result = cmd_query(_query_ns(author='alice'))
    assert result['filtered_count'] == 1
    assert result['findings'][0]['title'] == 'C1'


def test_finding_query_by_kind(plan_context):
    """cmd_query filters pr-comment findings by kind."""
    cmd_add(_add_ns(type='pr-comment', title='C1', detail='d', author='alice', kind='inline'))
    cmd_add(_add_ns(type='pr-comment', title='C2', detail='d', author='bob', kind='review_body'))

    result = cmd_query(_query_ns(kind='review_body'))
    assert result['filtered_count'] == 1
    assert result['findings'][0]['title'] == 'C2'


def test_finding_add_without_author_kind_still_succeeds(plan_context):
    """Existing add shape (no author/kind) keeps working and omits the keys."""
    result = cmd_add(_add_ns(type='bug', title='Plain bug', detail='d'))
    assert result['status'] == 'success'

    query = cmd_query(_query_ns(type='bug'))
    record = query['findings'][0]
    assert 'author' not in record
    assert 'kind' not in record


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


def test_finding_add_pr_comment_with_reviewed_commit_sha_and_bot_kind(plan_context):
    """cmd_add forwards reviewed_commit_sha and bot_kind onto a pr-comment finding."""
    result = cmd_add(
        _add_ns(
            type='pr-comment',
            title='CodeRabbit comment',
            detail='Extract a helper',
            author='coderabbitai[bot]',
            kind='inline',
            reviewed_commit_sha='abc1234',
            bot_kind='coderabbit',
        )
    )
    assert result['status'] == 'success'

    query = cmd_query(_query_ns(type='pr-comment'))
    assert query['filtered_count'] == 1
    record = query['findings'][0]
    assert record['reviewed_commit_sha'] == 'abc1234'
    assert record['bot_kind'] == 'coderabbit'


def test_finding_query_by_bot_kind(plan_context):
    """cmd_query filters pr-comment findings by bot_kind."""
    cmd_add(_add_ns(type='pr-comment', title='C1', detail='d', bot_kind='coderabbit'))
    cmd_add(_add_ns(type='pr-comment', title='C2', detail='d', bot_kind='pr-agent'))

    result = cmd_query(_query_ns(bot_kind='pr-agent'))
    assert result['filtered_count'] == 1
    assert result['findings'][0]['title'] == 'C2'


def test_finding_add_without_new_fields_still_succeeds(plan_context):
    """Existing add shape (no reviewed_commit_sha/bot_kind) keeps working and omits the keys."""
    result = cmd_add(_add_ns(type='pr-comment', title='Old-style', detail='d', author='octocat', kind='inline'))
    assert result['status'] == 'success'

    query = cmd_query(_query_ns(type='pr-comment'))
    record = query['findings'][0]
    assert 'reviewed_commit_sha' not in record
    assert 'bot_kind' not in record


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


# =============================================================================
# Test: Finding Resolve Command
# =============================================================================


def test_finding_resolve(plan_context):
    """Test resolving a finding."""
    add_result = cmd_add(
        _add_ns(
            type='build-error',
            title='Compilation error',
            detail='Missing import',
        )
    )
    hash_id = str(add_result['hash_id'])

    result = cmd_resolve(
        _resolve_ns(
            hash_id=hash_id,
            resolution='fixed',
            detail='Added missing import statement',
        )
    )
    assert result['status'] == 'success'
    assert result['resolution'] == 'fixed'
