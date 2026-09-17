#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_pr provider — post-responses core."""

from __future__ import annotations

from unittest.mock import patch
import pytest
from conftest import get_script_path, load_script_module, run_script


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
# post_responses — hash_id-keyed respond loop (GitLab note-reply + resolve shape)
# =============================================================================
class TestPostResponses:
    """post_responses transmits each finding's disposition to its own MR discussion, keyed by hash_id."""

    def _stage_one_finding(
        self, plan_id, thread_id, body='A substantive concern about null handling.', comment_id='C1'
    ):
        """File one pr-comment finding via fetch_findings and return its hash_id.

        ``comment_id`` keys the finding's identity, so staging several findings in
        one plan (an idempotency-across-rounds test) passes a distinct id per call.
        """
        comments = [
            {
                'id': comment_id,
                'kind': 'inline',
                'author': 'reviewer',
                'body': body,
                'path': f'src/{comment_id}.java',
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

    def test_second_round_transmits_only_newly_resolved_dispositions(self, plan_context):
        """Round 2 must re-transmit NOTHING already sent — the idempotency residue.

        Round 1 transmits two dispositions; round 2 adds one new disposition on the
        SAME plan-scoped store. Only the new one transmits and ``count_responded`` is
        1 — never a re-count of the two already-sent replies. The pre-fix verb had
        no prior-transmission term, so it re-transmitted all three and reported 3.
        """
        plan_context.plan_dir_for('gl-respond-round2')
        from _findings_core import resolve_finding

        r1 = [self._stage_one_finding('gl-respond-round2', f'thread-{i}', comment_id=f'r1-{i}') for i in range(2)]
        for i, hash_id in enumerate(r1):
            resolve_finding('gl-respond-round2', hash_id, 'fixed', detail=f'Fixed round-1 {i}.')

        with (
            patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
            patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')),
        ):
            first = cmd_post_responses(_make_args(300, 'gl-respond-round2'))
        assert first['count_responded'] == 2

        new_hash = self._stage_one_finding('gl-respond-round2', 'thread-new', comment_id='r2-0')
        resolve_finding('gl-respond-round2', new_hash, 'fixed', detail='Fixed the new one.')

        calls = []

        def _fake_run_glab(argv):
            calls.append(argv)
            return 0, '', ''

        with (
            patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
            patch('gitlab_pr._gitlab.run_glab', side_effect=_fake_run_glab),
        ):
            second = cmd_post_responses(_make_args(300, 'gl-respond-round2'))

        assert second['count_responded'] == 1
        assert [entry['hash_id'] for entry in second['responded']] == [new_hash]
        already = [entry for entry in second['skipped'] if entry['reason'] == 'already responded']
        assert {entry['hash_id'] for entry in already} == set(r1)
        # Only the new disposition drove glab traffic: one note-reply + one resolve.
        assert len(calls) == 2
        assert calls[0][3].endswith('/discussions/thread-new/notes')

    def test_retransmits_a_changed_disposition(self, plan_context):
        """A disposition CHANGED between rounds transmits again — the fix is a KEY.

        An unchanged re-run skips (the marker holds); re-resolving the finding to a
        different disposition clears the marker so the corrected reply goes out.
        """
        plan_context.plan_dir_for('gl-respond-changed')
        from _findings_core import resolve_finding

        hash_id = self._stage_one_finding('gl-respond-changed', 'thread-c')
        resolve_finding('gl-respond-changed', hash_id, 'fixed', detail='Fixed originally.')

        with (
            patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
            patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')),
        ):
            first = cmd_post_responses(_make_args(300, 'gl-respond-changed'))
        assert first['count_responded'] == 1

        # Unchanged re-run: the marker holds, nothing transmits.
        with (
            patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
            patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')) as mock_glab,
        ):
            unchanged = cmd_post_responses(_make_args(300, 'gl-respond-changed'))
        assert unchanged['count_responded'] == 0
        assert [entry for entry in unchanged['skipped'] if entry['reason'] == 'already responded']
        mock_glab.assert_not_called()

        # The disposition CHANGES: resolve_finding clears the marker so it re-qualifies.
        resolve_finding('gl-respond-changed', hash_id, 'rejected', detail='On reflection, rejected.')

        calls = []

        def _fake_run_glab(argv):
            calls.append(argv)
            return 0, '', ''

        with (
            patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
            patch('gitlab_pr._gitlab.run_glab', side_effect=_fake_run_glab),
        ):
            changed = cmd_post_responses(_make_args(300, 'gl-respond-changed'))
        assert changed['count_responded'] == 1
        assert changed['responded'][0]['hash_id'] == hash_id
        assert calls[0][-1] == 'body=On reflection, rejected.'


# =============================================================================
# The unreached findings store — ``post_responses`` reads it back
# =============================================================================
#
# ``post_responses`` is this provider's only verb that READS the plan's stored
# ``pr-comment`` findings. ``manage-findings`` answers a plan whose directory is
# absent from the resolved root with ``error: findings_store_unresolved`` and NO
# ``findings`` key, so a ``.get('findings') or []`` read turned an unreached store
# into an EMPTY LIST and reported a confident "every disposition transmitted,
# nothing failed" over a store that was never opened.
#
# ⛔ BOTH directions are pinned. A fix that turned every empty finding list into an
# error would satisfy the refusal test and break every plan whose store legitimately
# holds no pr-comment finding — the documented inverse defect. The matched control
# is what excludes it.
def test_post_responses_refuses_a_plan_absent_from_the_resolved_root(plan_context):
    """Positive control: an unreached store is a refusal, not "nothing to transmit"."""
    plan_id = 'gl-store-absent-respond'
    root = plan_context.fixture_dir
    assert not (plan_context.plans_dir / plan_id).exists(), (
        'the plan directory must be ABSENT for this to be the unreached-store case'
    )

    with (
        patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
        patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')) as mock_glab,
    ):
        result = cmd_post_responses(_make_args(500, plan_id))

    assert result.get('status') == 'error', result
    assert result.get('error') == 'findings_store_unresolved', (
        "the provider must re-publish the store's own error code rather than mint a "
        f'second vocabulary for the same fact: {result}'
    )
    assert result.get('findings_store_state') == 'plan_absent'
    assert result.get('unresolved_store') is True
    assert str(root) in str(result.get('message', '')), (
        "the refusal must carry the store's provenance naming the resolved root"
    )
    # The pre-guard answer, excluded explicitly: a confident all-clear report.
    assert 'count_responded' not in result
    assert 'count_failed' not in result
    mock_glab.assert_not_called()


def test_post_responses_against_a_resolved_empty_store_is_a_genuine_success(plan_context):
    """Matched negative control: a resolved store with nothing to send still succeeds."""
    plan_id = 'gl-store-empty-respond'
    plan_context.plan_dir_for(plan_id)

    with (
        patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
        patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')),
    ):
        result = cmd_post_responses(_make_args(501, plan_id))

    assert result['status'] == 'success', result
    assert result['count_responded'] == 0
    assert result['count_skipped'] == 0
    assert result['count_failed'] == 0


def test_post_responses_still_transmits_against_a_resolved_populated_store(plan_context):
    """Matched positive control on the happy path: the guard blocks nothing real."""
    plan_id = 'gl-store-populated-respond'
    plan_context.plan_dir_for(plan_id)
    hash_id = _fetch_with_comment(plan_id, 503)['stored_hash_ids'][0]

    from _findings_core import resolve_finding

    resolve_finding(plan_id, hash_id, 'fixed', detail='Fixed in the follow-up commit.')

    with (
        patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
        patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')),
    ):
        result = cmd_post_responses(_make_args(503, plan_id))

    assert result['status'] == 'success', result
    assert result['count_responded'] == 1
    assert result['responded'][0]['hash_id'] == hash_id


def test_the_two_zeros_are_distinguishable_in_one_comparison(plan_context):
    """The property the scenario turns on, stated as a single comparison.

    Asserting the refusal and the benign zero in separate tests leaves open that they
    still agree on the field a caller branches on. Before the guard both cases
    answered with the SAME ``status: success`` envelope and the same zero counts.
    """
    resolved_id = 'gl-store-pair-resolved'
    plan_context.plan_dir_for(resolved_id)

    with (
        patch('gitlab_pr._gitlab.get_project_path', return_value='group/proj'),
        patch('gitlab_pr._gitlab.run_glab', return_value=(0, '', '')),
    ):
        benign = cmd_post_responses(_make_args(502, resolved_id))
        absent = cmd_post_responses(_make_args(502, 'gl-store-pair-missing'))

    assert benign['status'] != absent['status']
    assert absent['findings_store_state'] == 'plan_absent'
    assert 'findings_store_state' not in benign
