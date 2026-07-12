#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for review_completeness.py — the automatic-review step-done guard predicate.

Covers the three states the D3 guard distinguishes against the pr-comment findings
store:

    complete   — every enabled bot produced a fetched finding, none pending
    pending    — an enabled bot has an unresolved (pending) finding
    unfetched  — an enabled bot produced no finding at all

The store is seeded in-process via ``_findings_core.add_finding`` /
``resolve_finding`` under the ``plan_context`` PLAN_BASE_DIR sandbox, so
``check_completeness`` reads a real per-plan store rather than a stub.
"""

from __future__ import annotations

import sys

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import review_completeness as rc  # noqa: E402
import _findings_core as fc  # noqa: E402


def _seed(plan_id: str, bot_kind: str, resolution: str = 'pending') -> str:
    """File one pr-comment finding for ``bot_kind`` and optionally resolve it.

    Returns the finding's hash_id. When ``resolution`` is not ``pending`` the
    finding is immediately resolved to that value so it counts as handled.
    """
    result = fc.add_finding(
        plan_id,
        'pr-comment',
        title=f'{bot_kind} comment',
        detail=f'thread from {bot_kind}',
        bot_kind=bot_kind,
        kind='inline',
    )
    assert result['status'] == 'success', result
    hash_id = result['hash_id']
    if resolution != 'pending':
        resolved = fc.resolve_finding(plan_id, hash_id, resolution)
        assert resolved['status'] == 'success', resolved
    return hash_id


def test_pending_bot_blocks(plan_context):
    """An enabled bot with an unresolved finding makes the store incomplete."""
    plan_id = 'rc-pending'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')

    result = rc.check_completeness(plan_id, ['coderabbit'])

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == ['coderabbit']
    assert result['unfetched_bots'] == []


def test_fully_resolved_is_complete(plan_context):
    """An enabled bot whose only finding is resolved reports complete."""
    plan_id = 'rc-resolved'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = rc.check_completeness(plan_id, ['coderabbit'])

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == []


def test_unfetched_bot_blocks(plan_context):
    """An enabled bot that produced no finding at all is unfetched → incomplete."""
    plan_id = 'rc-unfetched'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = rc.check_completeness(plan_id, ['coderabbit', 'sourcery'])

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == ['sourcery']


def test_mixed_pending_and_unfetched(plan_context):
    """Pending and unfetched bots are surfaced on their own lists in enabled order."""
    plan_id = 'rc-mixed'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')
    _seed(plan_id, 'sourcery', resolution='fixed')
    # gemini seeded with no finding at all → unfetched

    result = rc.check_completeness(plan_id, ['coderabbit', 'sourcery', 'gemini'])

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == ['coderabbit']
    assert result['unfetched_bots'] == ['gemini']


def test_empty_store_all_unfetched(plan_context):
    """A store with no findings reports every enabled bot as unfetched (fail-closed)."""
    plan_id = 'rc-empty-store'
    plan_context.plan_dir_for(plan_id)

    result = rc.check_completeness(plan_id, ['coderabbit', 'gemini'])

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == ['coderabbit', 'gemini']


def test_empty_enabled_bots_is_complete(plan_context):
    """No enabled bots means nothing to await — complete is vacuously true."""
    plan_id = 'rc-no-bots'
    plan_context.plan_dir_for(plan_id)

    result = rc.check_completeness(plan_id, [])

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == []


def test_bot_with_multiple_findings_one_pending(plan_context):
    """A bot with several findings is pending if ANY of them is unresolved."""
    plan_id = 'rc-multi'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')
    _seed(plan_id, 'coderabbit', resolution='pending')

    result = rc.check_completeness(plan_id, ['coderabbit'])

    assert result['complete'] is False
    assert result['pending_bots'] == ['coderabbit']


def test_cli_emits_toon_and_zero_exit(plan_context):
    """The check verb prints the documented TOON block and exits 0."""
    plan_id = 'rc-cli'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')

    result = run_script(
        SCRIPT_PATH, 'check', '--plan-id', plan_id, '--enabled-bots', 'coderabbit,sourcery'
    )

    assert result.success, result.stderr
    assert 'status: success' in result.stdout
    assert 'complete: false' in result.stdout
    assert 'pending_bots[1]' in result.stdout
    assert 'coderabbit' in result.stdout
    assert 'unfetched_bots[1]' in result.stdout
    assert 'sourcery' in result.stdout


def test_cli_complete_emits_true(plan_context):
    """The clean path emits complete: true with no bot lists."""
    plan_id = 'rc-cli-clean'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = run_script(SCRIPT_PATH, 'check', '--plan-id', plan_id, '--enabled-bots', 'coderabbit')

    assert result.success, result.stderr
    assert 'complete: true' in result.stdout
    assert 'pending_bots' not in result.stdout
    assert 'unfetched_bots' not in result.stdout


def test_cli_whitespace_in_enabled_bots_tolerated(plan_context):
    """Whitespace around comma-separated bot tokens is stripped."""
    plan_id = 'rc-cli-ws'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = run_script(
        SCRIPT_PATH, 'check', '--plan-id', plan_id, '--enabled-bots', ' coderabbit , '
    )

    assert result.success, result.stderr
    assert 'complete: true' in result.stdout
