#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_pr provider — error envelopes and CLI surface."""

from __future__ import annotations

from unittest.mock import patch
import pytest
from conftest import get_script_path, load_script_module, run_script


SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-gitlab', 'gitlab_pr.py')


# Resolved by (bundle, skill, file), which is what keeps this distinct from the
# github sibling despite the two scripts sharing a role.
gitlab_pr = load_script_module('plan-marshall', 'workflow-integration-gitlab', 'gitlab_pr.py')


cmd_fetch_findings = gitlab_pr.cmd_fetch_findings


cmd_post_responses = gitlab_pr.cmd_post_responses


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
# Rejected producer-mismatch persist (P6) — FIELD_ONLY loudness
# =============================================================================
#
# The producer-mismatch finding exists to report that findings were lost. When
# its OWN persist is rejected, the loss must surface on the returned dict — but
# the enclosing ``status`` stays truthful about the fetch, which did succeed.
_MR_COMMENT = {
    'id': 'C1',
    'kind': 'inline',
    'author': 'reviewer',
    'body': 'Please fix the off-by-one error in the loop bound',
    'path': 'src/Loop.java',
    'line': 12,
    'thread_id': 'mr-1',
}


def _fetch_with_comment(plan_id, pr_number, comment=None):
    """Run ``fetch_findings`` over a single-comment MR fixture."""
    comments = [comment or _MR_COMMENT]
    with patch('gitlab_pr._gitlab.fetch_pr_comments_data') as mock_fetch:
        mock_fetch.return_value = {
            'status': 'success',
            'provider': 'gitlab',
            'comments': comments,
            'total': len(comments),
            'unresolved': len(comments),
        }
        return cmd_fetch_findings(_make_args(pr_number, plan_id))


# =============================================================================
# Fail-loud unconfigured provider (both verbs)
# =============================================================================
class TestFailLoudUnconfigured:
    """Both verbs return a typed ``unconfigured`` status when GitLab is not authed."""

    def test_fetch_findings_unconfigured_is_not_silent_success(self, plan_context):
        plan_context.plan_dir_for('gl-unconfigured-fetch')
        with patch('gitlab_pr._gitlab.check_auth', return_value=(False, 'glab not authenticated')):
            result = cmd_fetch_findings(_make_args(200, 'gl-unconfigured-fetch'))

        assert result['status'] == 'unconfigured'
        assert result['operation'] == 'fetch_findings'
        assert result['provider'] == 'gitlab'
        # No findings were filed on the unconfigured path.
        from _findings_core import query_findings

        assert query_findings('gl-unconfigured-fetch', finding_type='pr-comment')['filtered_count'] == 0

    def test_post_responses_unconfigured_is_not_silent_success(self, plan_context):
        plan_context.plan_dir_for('gl-unconfigured-respond')
        with patch('gitlab_pr._gitlab.check_auth', return_value=(False, 'glab not authenticated')):
            result = cmd_post_responses(_make_args(200, 'gl-unconfigured-respond'))

        assert result['status'] == 'unconfigured'
        assert result['operation'] == 'post_responses'
        assert result['provider'] == 'gitlab'


# =============================================================================
# CLI plumbing
# =============================================================================
def test_help_lists_only_supported_subcommands():
    result = run_script(SCRIPT_PATH, '--help')

    assert result.returncode == 0
    assert 'fetch-comments' in result.stdout
    assert 'fetch_findings' in result.stdout
    assert 'post_responses' in result.stdout
    # Retired surfaces MUST be absent from the CLI.
    assert 'comments-stage' not in result.stdout
    assert 'triage-batch' not in result.stdout


@pytest.mark.parametrize(
    'argv',
    [
        pytest.param(['triage', '--comment', '{}'], id='triage-rejected'),
        pytest.param(['comments-stage', '--pr-number', '1', '--plan-id', 'x'], id='comments-stage-rejected'),
    ],
)
def test_retired_subcommand_rejected(argv):
    result = run_script(SCRIPT_PATH, *argv)

    assert result.returncode != 0


def test_rejected_mismatch_persist_surfaces_field_without_flipping_status(plan_context, monkeypatch):
    """A rejected mismatch persist sets qgate_persist_failed and leaves status success.

    Driven by the real validator: ``pr-comment`` is removed from the live
    ``FINDING_TYPES``, so both the comment store AND the mismatch finding are
    rejected by ``_findings_core`` itself — no synthetic persist mock.
    """
    import _findings_core

    plan_id = 'gl-pr-persist-reject'
    plan_context.plan_dir_for(plan_id)
    monkeypatch.setattr(
        _findings_core,
        'FINDING_TYPES',
        tuple(t for t in _findings_core.FINDING_TYPES if t != 'pr-comment'),
    )

    result = _fetch_with_comment(plan_id, 401)

    # FIELD_ONLY loudness: the fetch itself succeeded, so its status is unchanged.
    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert result['qgate_persist_failed'] is True
    assert result['producer_mismatch_hash_id'] is None
    failure = result['qgate_persist_failure']
    assert '(producer-mismatch)' in failure['title']
    assert 'count_stored=0' in failure['detail']
    assert 'Invalid finding type' in failure['message']


def test_deduplicated_mismatch_persist_stays_benign(plan_context, monkeypatch):
    """A ``deduplicated`` mismatch persist is benign — it never reads as a rejection.

    Only the upstream comment store is forced to fail (so a mismatch arises); the
    mismatch persist itself runs against the REAL primitive, which dedups the
    identical finding on the second run.
    """
    import _findings_core

    plan_id = 'gl-pr-persist-dedup'
    plan_context.plan_dir_for(plan_id)
    monkeypatch.setattr(
        _findings_core,
        'add_finding',
        lambda **kwargs: {'status': 'error', 'message': 'forced comment-store failure'},
    )

    first = _fetch_with_comment(plan_id, 402)
    assert first['status'] == 'success'
    assert first['count_stored'] == 0
    assert first['producer_mismatch_hash_id']
    assert 'qgate_persist_failed' not in first

    second = _fetch_with_comment(plan_id, 402)

    assert second['status'] == 'success'
    assert 'qgate_persist_failed' not in second
    # Dedup returns the SAME record — still in the store, so still a hash id.
    assert second['producer_mismatch_hash_id'] == first['producer_mismatch_hash_id']
