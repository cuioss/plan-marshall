#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_pr provider — comment parsing and findings persistence.
"""

from __future__ import annotations

from unittest.mock import patch
import pytest
from conftest import get_script_path, load_script_module, run_script


# Resolved by (bundle, skill, file), which is what keeps this distinct from the
# github sibling despite the two scripts sharing a role.
gitlab_pr = load_script_module('plan-marshall', 'workflow-integration-gitlab', 'gitlab_pr.py')


fetch_comments = gitlab_pr.fetch_comments


_is_obvious_noise = gitlab_pr._is_obvious_noise


cmd_fetch_findings = gitlab_pr.cmd_fetch_findings


@pytest.fixture(autouse=True)
def _stub_gitlab_auth():
    """Stub the auth check so fetch_findings / post_responses never hit ``glab``.

    Both verbs fail loud when GitLab is unauthenticated, so they call
    ``gitlab_ops.check_auth`` first; the default stub returns authenticated so the
    happy-path tests proceed. Tests that need an unauthenticated provider re-patch
    the same target inside a ``with`` block, which takes precedence.
    """
    with patch('gitlab_pr._gitlab.check_auth', return_value=(True, '')):
        yield


def _make_args(pr_number, plan_id):
    class _Args:
        pass

    a = _Args()
    a.pr_number = pr_number
    a.plan_id = plan_id
    return a


# =============================================================================
# Pre-filter (_is_obvious_noise)
# =============================================================================
def test_empty_body_is_noise():
    assert _is_obvious_noise('')


def test_lgtm_is_noise():
    assert _is_obvious_noise('lgtm')


def test_substantive_is_kept():
    assert not _is_obvious_noise('Please add validation for empty input')


# =============================================================================
# Provider integration (fetch_comments wrapper)
# =============================================================================
def test_fetch_comments_success():
    with patch('gitlab_pr._gitlab.fetch_pr_comments_data') as mock_fetch:
        mock_fetch.return_value = {
            'status': 'success',
            'provider': 'gitlab',
            'comments': [
                {
                    'id': 'C1',
                    'kind': 'inline',
                    'author': 'reviewer',
                    'body': 'fix this',
                    'path': 'src/Main.java',
                    'line': 42,
                    'thread_id': 'mr-thread-1',
                }
            ],
            'total': 1,
            'unresolved': 1,
        }
        result = fetch_comments(123)

    assert result['status'] == 'success'
    assert result['comments'][0]['kind'] == 'inline'


def test_fetch_comments_provider_error():
    with patch('gitlab_pr._gitlab.fetch_pr_comments_data') as mock_fetch:
        mock_fetch.return_value = {'status': 'error', 'error': 'auth'}
        result = fetch_comments(123)

    assert result['status'] == 'error'


# =============================================================================
# fetch_findings (producer-side fetch + filter + file to ledger)
# =============================================================================
def test_fetch_findings_persists_substantive_comments_only(plan_context):
    plan_id = 'gl-pr-stage-1'
    plan_context.plan_dir_for(plan_id)
    comments = [
        {
            'id': 'C1',
            'kind': 'inline',
            'author': 'reviewer',
            'body': 'Please fix the off-by-one error',
            'path': 'src/Loop.java',
            'line': 12,
            'thread_id': 'mr-1',
        },
        {
            'id': 'C2',
            'kind': 'review_body',
            'author': 'reviewer',
            'body': 'lgtm',
            'path': '',
            'line': 0,
            'thread_id': 'mr-2',
        },
    ]
    with patch('gitlab_pr._gitlab.fetch_pr_comments_data') as mock_fetch:
        mock_fetch.return_value = {
            'status': 'success',
            'provider': 'gitlab',
            'comments': comments,
            'total': len(comments),
            'unresolved': len(comments),
        }
        result = cmd_fetch_findings(_make_args(123, plan_id))

    assert result['status'] == 'success'
    assert result['operation'] == 'fetch_findings'
    assert result['provider'] == 'gitlab'
    assert result['count_fetched'] == 2
    assert result['count_skipped_noise'] == 1
    assert result['count_stored'] == 1
    assert result['producer_mismatch_hash_id'] is None

    from _findings_core import query_findings

    q = query_findings(plan_id, finding_type='pr-comment')
    assert q['filtered_count'] == 1
    stored = q['findings'][0]
    assert stored['type'] == 'pr-comment'
    assert stored['file_path'] == 'src/Loop.java'
    assert stored['line'] == 12
    # The detail carries the trusted structured metadata (kind, thread_id, ...).
    assert 'kind: inline' in stored['detail']
    assert 'thread_id: mr-1' in stored['detail']
    # The untrusted body is quarantined under raw_input.{body}, NOT in detail.
    assert 'Please fix the off-by-one error' not in stored['detail']
    assert stored['raw_input']['body'] == 'Please fix the off-by-one error'


def test_fetch_findings_provider_error_propagates(plan_context):
    plan_id = 'gl-pr-stage-err'
    plan_context.plan_dir_for(plan_id)
    with patch('gitlab_pr._gitlab.fetch_pr_comments_data') as mock_fetch:
        mock_fetch.return_value = {'status': 'error', 'error': 'auth'}
        result = cmd_fetch_findings(_make_args(125, plan_id))

    assert result['status'] == 'error'

