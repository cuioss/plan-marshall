#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-findings.py script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
"""


from _manage_findings_fixtures import (
    SCRIPT_PATH,
    _add_ns,
    _promote_ns,
    _qgate_add_ns,
    _qgate_query_ns,
    _qgate_resolve_ns,
    _query_ns,
    _resolve_ns,
    cmd_add,
    cmd_promote,
    cmd_qgate_add,
    cmd_qgate_query,
    cmd_qgate_resolve,
    cmd_query,
    cmd_resolve,
)

from conftest import run_script


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


def test_finding_resolve_all_statuses(plan_context):
    """Test all resolution statuses."""
    resolutions = ['pending', 'fixed', 'suppressed', 'accepted', 'taken_into_account', 'rejected']
    for res in resolutions:
        add_result = cmd_add(_add_ns(type='bug', title=f'Bug for {res}', detail='d'))
        hash_id = str(add_result['hash_id'])

        result = cmd_resolve(_resolve_ns(hash_id=hash_id, resolution=res))
        assert result['status'] == 'success', f'Failed for resolution {res}'


# =============================================================================
# Test: Finding Promote Command
# =============================================================================


def test_finding_promote(plan_context):
    """Test promoting a finding."""
    add_result = cmd_add(
        _add_ns(
            plan_id='finding-promote',
            type='tip',
            title='Use constructor injection',
            detail='Prefer constructor injection over field injection for testability',
        )
    )
    hash_id = str(add_result['hash_id'])

    result = cmd_promote(
        _promote_ns(
            plan_id='finding-promote',
            hash_id=hash_id,
            promoted_to='architecture',
        )
    )
    assert result['status'] == 'success'
    assert result['promoted_to'] == 'architecture'


def test_finding_promote_to_lessons(plan_context):
    """Test promoting to lessons learned."""
    add_result = cmd_add(
        _add_ns(
            type='bug',
            title='Null pointer from missing null check',
            detail='Always check for null before calling methods on optional fields',
        )
    )
    hash_id = str(add_result['hash_id'])

    result = cmd_promote(
        _promote_ns(
            hash_id=hash_id,
            promoted_to='lessons-2025-01-22-001',
        )
    )
    assert 'lessons-' in result['promoted_to']


def test_finding_query_promoted(plan_context):
    """Test filtering by promoted status."""
    add_result = cmd_add(_add_ns(type='tip', title='Promoted tip', detail='d'))
    hash_id = str(add_result['hash_id'])
    cmd_promote(_promote_ns(hash_id=hash_id, promoted_to='architecture'))

    cmd_add(_add_ns(type='tip', title='Not promoted', detail='d'))

    result = cmd_query(_query_ns(promoted='true'))
    assert result['filtered_count'] == 1

    result = cmd_query(_query_ns(promoted='false'))
    assert result['filtered_count'] == 1


# =============================================================================
# Test: Q-Gate Add Command
# =============================================================================


def test_qgate_add_basic(plan_context):
    """Test adding a basic Q-Gate finding."""
    result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-add-basic',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='False positive: helper.py',
            detail='File is consumer-only, not a producer',
        )
    )
    assert result['status'] == 'success'
    assert 'hash_id' in result
    assert result['phase'] == '3-outline'


def test_qgate_add_with_options(plan_context):
    """Test adding Q-Gate finding with all options."""
    result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-add-opts',
            phase='3-outline',
            source='user_review',
            type='triage',
            title='User: Add module X',
            detail='User requested adding module X to scope',
            file_path='src/module-x/main.py',
            component='deliverable-3',
            severity='warning',
            iteration=2,
        )
    )
    assert result['status'] == 'success'


def test_qgate_add_invalid_phase(plan_context):
    """Test that invalid phase is rejected (CLI plumbing - subprocess).

    The canonical ``parse_args_with_toon_errors`` contract emits
    ``status: error / error: invalid_phase`` TOON on stdout with exit
    code 0 (so callers can read the structured error without parsing
    stderr). The legacy assertion checked ``not result.success``; the
    new contract requires inspecting the parsed TOON instead.
    """
    result = run_script(
        SCRIPT_PATH,
        'qgate',
        'add',
        '--plan-id',
        'qgate-inv-phase',
        '--phase',
        'invalid-phase',
        '--source',
        'qgate',
        '--type',
        'triage',
        '--title',
        'Test',
        '--detail',
        'Test detail',
    )
    # New contract: argparse-boundary validation emits TOON on stdout
    # with exit code 0. Older invalid-source/invalid-type values still
    # fall through to the command handler which exits non-zero.
    assert result.returncode == 0
    data = result.toon()
    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_phase'


def test_qgate_add_invalid_source(plan_context):
    """Test that invalid source is rejected (CLI plumbing - subprocess)."""
    result = run_script(
        SCRIPT_PATH,
        'qgate',
        'add',
        '--plan-id',
        'qgate-inv-source',
        '--phase',
        '3-outline',
        '--source',
        'invalid',
        '--type',
        'triage',
        '--title',
        'Test',
        '--detail',
        'Test detail',
    )
    assert not result.success


# =============================================================================
# Test: Q-Gate Query Command
# =============================================================================


def test_qgate_query_empty(plan_context):
    """Test querying with no Q-Gate findings."""
    result = cmd_qgate_query(_qgate_query_ns(plan_id='qgate-query-empty', phase='3-outline'))
    assert result['status'] == 'success'
    assert result['total_count'] == 0
    assert result['phase'] == '3-outline'


def test_qgate_query_by_resolution(plan_context):
    """Test filtering Q-Gate findings by resolution."""
    cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Finding 1',
            detail='d1',
        )
    )
    add_result = cmd_qgate_add(
        _qgate_add_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Finding 2',
            detail='d2',
        )
    )
    hash_id = str(add_result['hash_id'])

    cmd_qgate_resolve(
        _qgate_resolve_ns(
            plan_id='qgate-query-res',
            hash_id=hash_id,
            resolution='taken_into_account',
            phase='3-outline',
            detail='Addressed by revising deliverable 3',
        )
    )

    result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            resolution='pending',
        )
    )
    assert result['filtered_count'] == 1

    result = cmd_qgate_query(
        _qgate_query_ns(
            plan_id='qgate-query-res',
            phase='3-outline',
            resolution='taken_into_account',
        )
    )
    assert result['filtered_count'] == 1
