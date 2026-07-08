# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for workflow-integration-gitlab gitlab_pr.py — two-verb provider contract.

Mirrors test_comments_stage.py (github) for the GitLab provider. The provider
surface is exactly two pure, zero-LLM verbs (plus the raw ``fetch-comments``):

- ``fetch-comments`` — raw glab fetch (no filtering, no storage)
- ``fetch_findings`` — fetch + pre-filter + file one ``pr-comment`` finding per
  surviving comment; the untrusted comment body is quarantined under
  ``raw_input.{body}`` (never embedded raw in the top-level ``detail``)
- ``post_responses`` — apply already-decided triage dispositions (discussion-note
  reply + resolve-discussion) back to the MR, keyed by each finding's own
  ``hash_id``

These tests cover the producer-side pre-filter helper, the fetch_findings flow
(body quarantined in raw_input, structured metadata in detail), the fail-loud
``unconfigured`` signal for both verbs, the hash_id-keyed post_responses respond
loop and its GitLab-specific glab request shape (note-reply then resolve), and
the CLI surface contract (the retired ``comments-stage`` / ``triage`` /
``triage-batch`` subcommands MUST be gone).
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-gitlab', 'gitlab_pr.py')

_pr_path = Path(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('gitlab_pr', _pr_path)
assert _spec is not None and _spec.loader is not None
gitlab_pr = importlib.util.module_from_spec(_spec)
sys.modules['gitlab_pr'] = gitlab_pr
_spec.loader.exec_module(gitlab_pr)

fetch_comments = gitlab_pr.fetch_comments
get_current_pr_number = gitlab_pr.get_current_pr_number
_is_obvious_noise = gitlab_pr._is_obvious_noise
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
# post_responses — hash_id-keyed respond loop (GitLab note-reply + resolve shape)
# =============================================================================


class TestPostResponses:
    """post_responses transmits each finding's disposition to its own MR discussion, keyed by hash_id."""

    def _stage_one_finding(self, plan_id, thread_id, body='A substantive concern about null handling.'):
        """File one pr-comment finding via fetch_findings and return its hash_id."""
        comments = [
            {
                'id': 'C1',
                'kind': 'inline',
                'author': 'reviewer',
                'body': body,
                'path': 'src/Main.java',
                'line': 42,
                'thread_id': thread_id,
            },
        ]
        with patch('gitlab_pr._gitlab.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'gitlab',
                'comments': comments,
                'total': 1,
                'unresolved': 1,
            }
            result = cmd_fetch_findings(_make_args(300, plan_id))
        return result['stored_hash_ids'][0]

    def test_respond_replies_and_resolves_keyed_by_finding_thread(self, plan_context):
        """A resolved finding drives a discussion-note reply + resolve on ITS OWN thread_id."""
        plan_context.plan_dir_for('gl-respond-basic')
        hash_id = self._stage_one_finding('gl-respond-basic', 'mr-thread-x')

        from _findings_core import resolve_finding

        resolve_finding('gl-respond-basic', hash_id, 'fixed', detail='Fixed the off-by-one in commit abc.')

        calls = []

        def _fake_run_glab(argv):
            calls.append(argv)
            return 0, '', ''

        with (
            patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
            patch('gitlab_pr._gitlab.run_glab', side_effect=_fake_run_glab),
        ):
            result = cmd_post_responses(_make_args(300, 'gl-respond-basic'))

        assert result['status'] == 'success'
        assert result['count_responded'] == 1
        assert result['count_failed'] == 0
        assert result['responded'][0]['hash_id'] == hash_id
        assert result['responded'][0]['thread_id'] == 'mr-thread-x'

        # Two glab API calls fired: a discussion-note reply carrying the
        # resolution_detail, then a resolve of the SAME discussion thread.
        assert len(calls) == 2
        note_call, resolve_call = calls
        # Note-reply: POST to the thread's /notes with body=<resolution_detail>.
        assert note_call[1] == '-X'
        assert note_call[2] == 'POST'
        assert note_call[3].endswith('/discussions/mr-thread-x/notes')
        assert note_call[-1] == 'body=Fixed the off-by-one in commit abc.'
        # Resolve: PUT resolved=true on the SAME discussion thread.
        assert resolve_call[2] == 'PUT'
        assert resolve_call[3].endswith('/discussions/mr-thread-x')
        assert resolve_call[-1] == 'resolved=true'

    def test_pending_finding_is_not_responded_to(self, plan_context):
        """A still-pending (un-triaged) finding gets no provider response."""
        plan_context.plan_dir_for('gl-respond-pending')
        self._stage_one_finding('gl-respond-pending', 'mr-thread-p')  # left pending

        with (
            patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
            patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')) as mock_glab,
        ):
            result = cmd_post_responses(_make_args(300, 'gl-respond-pending'))

        assert result['status'] == 'success'
        assert result['count_responded'] == 0
        mock_glab.assert_not_called()

    def test_resolved_finding_without_thread_id_is_skipped(self, plan_context):
        """A terminal-disposition finding with no thread_id is skipped, never guessed at."""
        plan_context.plan_dir_for('gl-respond-nothread')
        hash_id = self._stage_one_finding('gl-respond-nothread', '')  # empty thread_id

        from _findings_core import resolve_finding

        resolve_finding('gl-respond-nothread', hash_id, 'suppressed', detail='Suppressed with rationale.')

        with (
            patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
            patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')) as mock_glab,
        ):
            result = cmd_post_responses(_make_args(300, 'gl-respond-nothread'))

        assert result['status'] == 'success'
        assert result['count_responded'] == 0
        assert result['count_skipped'] == 1
        mock_glab.assert_not_called()


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
