# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for workflow-integration-github github_pr.py — two-verb provider contract.

The provider surface is exactly two pure verbs (plus the raw ``fetch-comments``):

- ``fetch-comments`` — raw GraphQL fetch (no filtering, no storage)
- ``fetch_findings`` — fetch + pre-filter + file one ``pr-comment`` finding per
  surviving comment; the untrusted body is quarantined under ``raw_input.{body}``
- ``post_responses`` — apply already-decided triage dispositions (thread-reply +
  resolve-thread) back to the PR, keyed by each finding's own ``hash_id``

These tests cover the producer-side pre-filter helper, the fetch_findings flow
(with the body quarantined in raw_input and structured metadata in detail), the
classification of reviewer-bot REFUSAL notices across the arms of the
recognition stack (``_github_pr.REFUSAL_LAYERS`` names them), the fail-loud
unconfigured signal,
the hash_id-keyed post_responses respond loop, the ``--project-dir`` plumbing,
and the CLI surface contract (the retired ``triage`` / ``triage-batch`` /
``comments-stage`` subcommands MUST be gone).
"""

import io
import sys
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest
from _resolve_project_dir_fixtures import worktree_query_result

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py')
github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py')
fetch_comments = github_pr.fetch_comments
get_current_pr_number = github_pr.get_current_pr_number
_is_obvious_noise = github_pr._is_obvious_noise
cmd_fetch_findings = github_pr.cmd_fetch_findings
cmd_post_responses = github_pr.cmd_post_responses


@pytest.fixture(autouse=True)
def _stub_provider_calls():
    """Stub the auth check and PR HEAD-SHA fetch so fetch_findings tests never hit ``gh``.

    ``cmd_fetch_findings`` fails loud when GitHub is unauthenticated, so it calls
    ``github_ops.check_auth`` first; the default stub returns authenticated so the
    happy-path tests proceed. It also resolves the PR HEAD SHA (for
    ``reviewed_commit_sha``) via ``github_ops.fetch_pr_head_sha`` once per batch.
    Tests that need a specific value (an unauthenticated provider, a specific SHA)
    re-patch the same target inside a ``with`` block, which takes precedence.
    """
    with (
        patch('github_pr._github.check_auth', return_value=(True, '')),
        patch('github_pr._github.fetch_pr_head_sha', return_value='stub-head-sha'),
    ):
        yield


def _stage_make_args(pr_number: int, plan_id: str):
    class _Args:
        pr_number: int
        plan_id: str

    a = _Args()
    a.pr_number = pr_number
    a.plan_id = plan_id
    return a


_SOURCERY_SIZE_LIMIT_REFUSAL = (
    'Sourcery was unable to review this pull request because '
    'your pull request is larger than the review limit of 150000 characters. '
    'Reduce the size of the pull request and request another review.'
)
_CODERABBIT_REVIEW_LIMIT_REFUSAL = (
    '> [!WARNING] > ## Review limit reached > '
    'You have reached your review limit for the current billing cycle. '
    'Reviews will resume once the limit resets.'
)
_CODERABBIT_COMMAND_REPLY_REFUSAL = (
    '<!-- This is an auto-generated reply by CodeRabbit --> '
    '<!-- CodeRabbit review command invocation: v2:abc --> '
    '<details> <summary>(warning) Action not completed</summary> '
    'Review rate limited. '
    '> Note: CodeRabbit is an incremental review system and does not re-review '
    'already reviewed commits. This command is applicable only when automatic '
    'reviews are paused. </details>'
)
_CODERABBIT_GENUINE_INLINE = (
    '<!-- cr-indicator-types:potential_issue --> '
    'Major: the retry loop can spin forever when the backoff cap is zero. '
    'Guard the cap before entering the loop.'
)
_SOURCERY_SHAPED_REFUSAL = (
    '> [!WARNING] Sourcery has reached your review limit for this pull request. '
    'Reviews will resume once the limit resets.'
)
_SOURCERY_WEEKLY_QUOTA_REFUSAL = (
    'Sourcery has not reviewed this pull request because '
    'you have reached your weekly rate limit of 500000 diff characters.'
)
_UNKNOWN_BOT_REFUSAL = (
    '> [!WARNING] > ## Usage limit reached > '
    'This reviewer has reached its monthly usage limit. '
    'Reviews will resume after the limit resets.'
)
_GENUINE_REVIEW_MENTIONING_A_LIMIT = (
    'This retry loop exceeds the review limit we agreed on for batch size; '
    'consider lowering it to 50 before this merges.'
)
_REWORDED_REFUSAL = 'Skipping this one for now.'
_SHORT_REVIEW_WITH_ANCHOR = 'Guard the bound at `src/Idx.java:12`.'


class _StoreArgs:
    """The two attributes both verbs read off their namespace."""

    def __init__(self, pr_number, plan_id):
        self.pr_number = pr_number
        self.plan_id = plan_id


#: The commit a fix is stamped with in these tests, and the short form the
#: transmitted reply carries.
_FIX_COMMIT = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'
_FIX_COMMIT_SHORT = _FIX_COMMIT[:7]


def _stamp_fix_commit(plan_id, hash_id, commit_sha=_FIX_COMMIT):
    """Stamp ``commit_sha`` on one finding through the store's own writer."""
    from _findings_core import stamp_fix_commit

    result = stamp_fix_commit(plan_id, commit_sha, hash_id=hash_id)
    assert result['status'] == 'success', result
    assert result['hash_ids'] == [hash_id]


def _compare_reports(state, *, returncode=0):
    """Make the provider's compare read answer ``state`` for every commit pair.

    This is the seam the hold-back reads: ``post_responses`` asks the provider
    whether the stamped commit reaches the pull request head through one
    ``gh api …/compare/…`` call. ``ahead`` and ``identical`` say it does.
    """
    return patch('github_pr._github.run_gh', return_value=(returncode, f'{state}\n', ''))


def _stage_comments(plan_id, comments, pr_number=300):
    """File ``comments`` as pr-comment findings and return their hash ids in order."""
    with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
        mock_fetch.return_value = {
            'status': 'success',
            'provider': 'github',
            'comments': comments,
            'total': len(comments),
            'unresolved': len(comments),
        }
        result = cmd_fetch_findings(_stage_make_args(pr_number, plan_id))
    assert result['count_stored'] == len(comments), result
    return result['stored_hash_ids']


def _inline_comment(comment_id, thread_id, body):
    """An inline review comment on its own thread."""
    return {
        'id': comment_id,
        'kind': 'inline',
        'author': 'reviewer',
        'body': body,
        'path': 'src/Main.java',
        'line': 42,
        'thread_id': thread_id,
    }


_SUBSTANTIVE_COMMENT = {
    'id': 'C-store-1',
    'kind': 'inline',
    'author': 'reviewer',
    'body': 'Please guard the empty-input branch before indexing.',
    'path': 'src/Loop.java',
    'line': 12,
    'thread_id': 'gh-thread-store-1',
}


class TestCommentsStageAuthorKindFields:
    """Every stored pr-comment finding carries first-class, queryable ``author``
    and ``kind`` fields.

    Reviewer identity (``author``) and comment structure
    (``kind``) are indexed top-level finding fields (see manage-findings
    ``standards/jsonl-format.md``), distinct from the human-readable
    ``author:`` / ``kind:`` lines inside the ``detail`` blob. The producer
    sources ``author`` from the GitHub comment author login and ``kind`` from
    the provider-supplied structure discriminator — one of the three values
    ``inline`` / ``review_body`` / ``issue_comment``.
    """

    def test_stored_finding_author_equals_comment_author_login(self, plan_context):
        """The stored finding's first-class ``author`` equals the comment author login."""
        comments = [
            {
                'id': 'C1',
                'kind': 'inline',
                'author': 'coderabbitai',
                'body': 'This null dereference needs a guard before the call.',
                'path': 'src/Main.java',
                'line': 42,
                'thread_id': 'PRRT_a',
            },
        ]

        plan_context.plan_dir_for('gh-pr-author-field')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(130, 'gh-pr-author-field'))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1

        from _findings_core import query_findings

        q = query_findings('gh-pr-author-field', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        # First-class queryable field — not merely a line inside detail.
        assert stored['author'] == 'coderabbitai'

    @pytest.mark.parametrize(
        'kind',
        [
            pytest.param('inline', id='inline'),
            pytest.param('review_body', id='review_body'),
            pytest.param('issue_comment', id='issue_comment'),
        ],
    )
    def test_stored_finding_kind_equals_structure_discriminator(self, kind, plan_context):
        """The stored finding's first-class ``kind`` equals the provider structure discriminator.

        Covers the three discriminator values the producer emits: ``inline``,
        ``review_body``, and ``issue_comment``.
        """
        # review_body / issue_comment kinds carry no thread_id and (per the
        # provider) no path/line, mirroring the real GraphQL fallback shape.
        is_inline = kind == 'inline'
        comments = [
            {
                'id': 'K1',
                'kind': kind,
                'author': 'cuioss-review-bot',
                'body': 'A substantive review point about error propagation here.',
                'path': 'src/Worker.java' if is_inline else '',
                'line': 17 if is_inline else 0,
                'thread_id': 'PRRT_k' if is_inline else '',
            },
        ]

        # plan_id must match ^[a-z][a-z0-9-]*$ — slugify the kind (no underscores).
        plan_id = f'gh-pr-kind-{kind.replace("_", "-")}'
        plan_context.plan_dir_for(plan_id)
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(131, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1

        from _findings_core import query_findings

        q = query_findings(plan_id, finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        # First-class queryable field — equals the provider structure discriminator.
        assert stored['kind'] == kind
        # author is likewise first-class for the same finding.
        assert stored['author'] == 'cuioss-review-bot'

    def test_stored_finding_is_queryable_by_first_class_kind(self, plan_context):
        """The first-class ``kind`` field is an indexed query filter, not just stored.

        A ``query_findings(..., kind=...)`` call must return only the findings
        whose stored ``kind`` matches — proving the field is queryable, the
        property that distinguishes it from the detail-blob line.
        """
        comments = [
            {
                'id': 'Q1',
                'kind': 'inline',
                'author': 'reviewer',
                'body': 'Inline comment about a concrete code line.',
                'path': 'src/A.java',
                'line': 5,
                'thread_id': 'PRRT_q1',
            },
            {
                'id': 'Q2',
                'kind': 'review_body',
                'author': 'reviewer',
                'body': 'Overall review summary raising a design concern.',
                'path': '',
                'line': 0,
                'thread_id': '',
            },
        ]

        plan_context.plan_dir_for('gh-pr-kind-query')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(132, 'gh-pr-kind-query'))

        assert result['status'] == 'success'
        assert result['count_stored'] == 2

        from _findings_core import query_findings

        inline_only = query_findings('gh-pr-kind-query', finding_type='pr-comment', kind='inline')
        assert inline_only['filtered_count'] == 1
        assert inline_only['findings'][0]['kind'] == 'inline'

        review_only = query_findings('gh-pr-kind-query', finding_type='pr-comment', kind='review_body')
        assert review_only['filtered_count'] == 1
        assert review_only['findings'][0]['kind'] == 'review_body'

    def test_stored_finding_is_queryable_by_first_class_author(self, plan_context):
        """The first-class ``author`` field is an indexed query filter.

        Distinct authors on the same PR must be separable via
        ``query_findings(..., author=...)`` — the attribution use case the
        review retrospective relies on.
        """
        comments = [
            {
                'id': 'A1',
                'kind': 'inline',
                'author': 'coderabbitai',
                'body': 'Bot-flagged: potential resource leak on this path.',
                'path': 'src/A.java',
                'line': 5,
                'thread_id': 'PRRT_a1',
            },
            {
                'id': 'A2',
                'kind': 'inline',
                'author': 'human-reviewer',
                'body': 'Please rename this variable for clarity.',
                'path': 'src/B.java',
                'line': 9,
                'thread_id': 'PRRT_a2',
            },
        ]

        plan_context.plan_dir_for('gh-pr-author-query')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(133, 'gh-pr-author-query'))

        assert result['status'] == 'success'
        assert result['count_stored'] == 2

        from _findings_core import query_findings

        bot_only = query_findings('gh-pr-author-query', finding_type='pr-comment', author='coderabbitai')
        assert bot_only['filtered_count'] == 1
        assert bot_only['findings'][0]['author'] == 'coderabbitai'

        human_only = query_findings('gh-pr-author-query', finding_type='pr-comment', author='human-reviewer')
        assert human_only['filtered_count'] == 1
        assert human_only['findings'][0]['author'] == 'human-reviewer'

    def test_missing_author_defaults_to_unknown(self, plan_context):
        """A comment with no author login stores ``author='unknown'`` (producer fallback)."""
        comments = [
            {
                'id': 'U1',
                'kind': 'inline',
                'author': '',
                'body': 'Substantive comment from an unattributed source.',
                'path': 'src/A.java',
                'line': 5,
                'thread_id': 'PRRT_u1',
            },
        ]

        plan_context.plan_dir_for('gh-pr-author-unknown')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(134, 'gh-pr-author-unknown'))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1

        from _findings_core import query_findings

        q = query_findings('gh-pr-author-unknown', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        assert q['findings'][0]['author'] == 'unknown'


class TestPostResponses:
    """post_responses transmits each finding's disposition to its own thread, keyed by hash_id.

    Routing contract (``workflow-integration-github`` SKILL.md § Workflow 2 step 4):
    the disposition path is chosen by the finding's ``kind`` — its thread-BEARING-ness
    — never by whether a ``thread_id`` happened to be extractable. Only the genuinely
    threadless kinds (``review_body``, ``issue_comment``) enter the batched PR-level
    comment; a thread-bearing (``inline``) finding whose thread is missing or unusable
    is UNDELIVERABLE and lands in ``untransmitted[]`` with ``status: partial``, never
    silently downgraded into the batch.
    """

    def _stage_one_finding(self, plan_id, thread_id, body='A substantive concern about null handling.', kind='inline'):
        """File one pr-comment finding via fetch_findings and return its hash_id."""
        comments = [
            {
                'id': 'C1',
                'kind': kind,
                'author': 'reviewer',
                'body': body,
                'path': 'src/Main.java',
                'line': 42,
                'thread_id': thread_id,
            },
        ]
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': 1,
                'unresolved': 1,
            }
            result = cmd_fetch_findings(_stage_make_args(300, plan_id))
        return result['stored_hash_ids'][0]

    def test_respond_replies_and_resolves_keyed_by_finding_thread(self, plan_context):
        """A resolved finding drives a thread-reply + resolve-thread on ITS OWN thread_id."""
        plan_context.plan_dir_for('gh-respond-basic')
        hash_id = self._stage_one_finding('gh-respond-basic', 'PRRT_x')

        from _findings_core import resolve_finding

        resolve_finding('gh-respond-basic', hash_id, 'fixed', detail='Fixed the null guard.')
        _stamp_fix_commit('gh-respond-basic', hash_id)

        calls = []

        def _fake_graphql(mutation, variables):
            calls.append((mutation, variables))
            return 0, {}, ''

        with patch('github_pr._github.run_graphql', side_effect=_fake_graphql), _compare_reports('ahead'):
            result = cmd_post_responses(_stage_make_args(300, 'gh-respond-basic'))

        assert result['status'] == 'success'
        assert result['count_responded'] == 1
        assert result['count_untransmitted'] == 0
        assert result['responded'][0]['hash_id'] == hash_id
        assert result['responded'][0]['thread_id'] == 'PRRT_x'
        assert result['responded'][0]['transmit_mode'] == 'thread_reply'
        assert result['responded'][0]['resolved_on_provider'] is True
        # Two mutations fired: a thread-reply carrying the resolution_detail, then a resolve.
        assert len(calls) == 2
        reply_vars = calls[0][1]
        assert reply_vars['threadId'] == 'PRRT_x'
        assert reply_vars['body'] == f'Fixed the null guard.\n\nFix commit: {_FIX_COMMIT_SHORT}'
        assert calls[1][1]['threadId'] == 'PRRT_x'

    def test_pending_finding_is_not_responded_to(self, plan_context):
        """A still-pending (un-triaged) finding gets no provider response."""
        plan_context.plan_dir_for('gh-respond-pending')
        self._stage_one_finding('gh-respond-pending', 'PRRT_p')  # left pending

        with patch('github_pr._github.run_graphql', return_value=(0, {}, '')) as mock_graphql:
            result = cmd_post_responses(_stage_make_args(300, 'gh-respond-pending'))

        assert result['status'] == 'success'
        assert result['count_responded'] == 0
        mock_graphql.assert_not_called()

    @pytest.mark.parametrize('kind', ['review_body', 'issue_comment'])
    def test_genuinely_threadless_kind_is_transmitted_as_a_batched_pr_comment(self, kind, plan_context):
        """A genuinely threadless kind is transmitted as a PR comment, NOT skipped.

        GitHub gives ``review_body`` / ``issue_comment`` no review thread to reply
        into, but the disposition still has something to say — dropping it would
        lose a recorded decision. It goes out as a batched PR-level comment and is
        reported with ``resolved_on_provider: false``, because no thread exists to
        resolve.
        """
        plan_id = f'gh-respond-threadless-{kind.replace("_", "-")}'
        plan_context.plan_dir_for(plan_id)
        hash_id = self._stage_one_finding(plan_id, '', kind=kind)

        from _findings_core import resolve_finding

        resolve_finding(plan_id, hash_id, 'suppressed', detail='Suppressed with rationale.')

        posted = []

        def _fake_post(pr_number, body):
            posted.append((pr_number, body))
            return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')) as mock_graphql,
            patch('github_pr._github.post_pr_comment', side_effect=_fake_post),
        ):
            result = cmd_post_responses(_stage_make_args(300, plan_id))

        assert result['status'] == 'success'
        assert result['count_responded'] == 1
        assert result['count_skipped'] == 0
        assert result['count_untransmitted'] == 0
        assert result['responded'][0]['hash_id'] == hash_id
        assert result['responded'][0]['transmit_mode'] == 'batched_issue_comment'
        assert result['responded'][0]['resolved_on_provider'] is False
        # One PR-level comment carrying the disposition, anchored on the source comment.
        assert len(posted) == 1
        assert 'Suppressed with rationale.' in posted[0][1]
        assert 'C1' in posted[0][1]
        # No thread mutation fired — there is no thread.
        mock_graphql.assert_not_called()

    def test_inline_finding_without_thread_id_is_untransmitted_never_batched(self, plan_context):
        """A thread-BEARING finding with no thread_id is undeliverable, NOT threadless.

        This is the routing predicate under test: an ``inline`` comment always has a
        review thread on the provider, so an empty ``thread_id`` means the thread is
        unrecoverable HERE — not that the disposition belongs on the PR-level batch.
        Batching it would report the decision as delivered while the reviewer's own
        thread stays unanswered and unresolved, so it lands in ``untransmitted[]``
        and drives ``status: partial``.
        """
        plan_context.plan_dir_for('gh-respond-inline-nothread')
        hash_id = self._stage_one_finding('gh-respond-inline-nothread', '')  # inline, empty thread_id

        from _findings_core import resolve_finding

        resolve_finding('gh-respond-inline-nothread', hash_id, 'suppressed', detail='Suppressed with rationale.')

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')) as mock_graphql,
            patch('github_pr._github.post_pr_comment') as mock_post,
        ):
            result = cmd_post_responses(_stage_make_args(300, 'gh-respond-inline-nothread'))

        assert result['status'] == 'partial'
        assert result['count_responded'] == 0
        assert result['count_skipped'] == 0
        assert result['count_untransmitted'] == 1
        assert result['untransmitted'][0]['hash_id'] == hash_id
        # The reason names the missing thread, so the failure is diagnosable.
        reason = result['untransmitted'][0]['reason']
        assert 'thread_id' in reason
        assert 'inline' in reason
        # NEVER re-routed into the batch — no PR-level comment was posted at all.
        mock_post.assert_not_called()
        # And no thread mutation was attempted against a non-existent thread.
        mock_graphql.assert_not_called()

    def test_inline_finding_whose_thread_reply_fails_is_untransmitted_never_batched(self, plan_context):
        """A failed in-thread reply is untransmitted — it does not fall back to the batch.

        The batch is not a fallback channel for a thread-bearing disposition. When the
        reply mutation fails, the disposition is reported undelivered with the provider
        error, and no PR-level comment is posted in its place.
        """
        plan_context.plan_dir_for('gh-respond-inline-replyfail')
        hash_id = self._stage_one_finding('gh-respond-inline-replyfail', 'PRRT_boom')

        from _findings_core import resolve_finding

        resolve_finding('gh-respond-inline-replyfail', hash_id, 'fixed', detail='Fixed the guard.')
        _stamp_fix_commit('gh-respond-inline-replyfail', hash_id)

        with (
            patch('github_pr._github.run_graphql', return_value=(1, {}, 'thread not found')),
            patch('github_pr._github.post_pr_comment') as mock_post,
            _compare_reports('ahead'),
        ):
            result = cmd_post_responses(_stage_make_args(300, 'gh-respond-inline-replyfail'))

        assert result['status'] == 'partial'
        assert result['count_responded'] == 0
        assert result['count_untransmitted'] == 1
        assert result['untransmitted'][0]['hash_id'] == hash_id
        assert 'thread-reply failed' in result['untransmitted'][0]['reason']
        assert 'thread not found' in result['untransmitted'][0]['reason']
        # NEVER re-routed into the batch.
        mock_post.assert_not_called()


class TestFixedReplyHeldUntilCommit:
    """A ``fixed`` reply is held until its fix commit is stamped and on the pull request.

    Triage records ``fixed`` before the fix is a commit. ``post_responses`` sends
    nothing for such a finding until it carries a ``fix_commit_sha`` and the provider
    reports that commit as reaching the pull request head.
    """

    def _post(self, plan_id, *, compare='ahead', compare_returncode=0):
        """Run one respond pass and return ``(result, graphql_calls, compare_mock)``."""
        calls = []

        def _fake_graphql(mutation, variables):
            calls.append((mutation, variables))
            return 0, {}, ''

        with (
            patch('github_pr._github.run_graphql', side_effect=_fake_graphql),
            _compare_reports(compare, returncode=compare_returncode) as compare_mock,
        ):
            result = cmd_post_responses(_stage_make_args(300, plan_id))
        return result, calls, compare_mock

    def test_an_unstamped_fixed_finding_gets_no_reply_and_one_deferred_row(self, plan_context):
        """No thread reply, no resolve call, one ``deferred_until_commit`` row."""
        from _findings_core import query_findings, resolve_finding

        plan_id = 'gh-held-unstamped'
        plan_context.plan_dir_for(plan_id)
        (hash_id,) = _stage_comments(plan_id, [_inline_comment('C1', 'PRRT_held', 'Guard the null case.')])
        resolve_finding(plan_id, hash_id, 'fixed', detail='Will be addressed by TASK-7.', fix_task_number=7)

        with patch('github_pr._github.post_pr_comment') as mock_post:
            result, calls, compare_mock = self._post(plan_id)

        assert calls == []
        mock_post.assert_not_called()
        # No commit is stamped, so the provider is not even asked about one.
        compare_mock.assert_not_called()
        assert result['status'] == 'success'
        assert result['count_responded'] == 0
        assert result['count_untransmitted'] == 0
        assert result['count_deferred_until_commit'] == 1
        assert result['deferred_until_commit'] == [
            {'hash_id': hash_id, 'reason': 'no_fix_commit', 'fix_commit_sha': '', 'fix_task_number': '7'}
        ]
        # A held finding carries no responded marker, so a later pass looks at it again.
        stored = query_findings(plan_id, finding_type='pr-comment')['findings'][0]
        assert not stored.get('responded')

    def test_the_second_pass_after_the_stamp_replies_with_the_commit_and_resolves(self, plan_context):
        """Held on the first pass, released on the second by the stamp alone."""
        from _findings_core import resolve_finding, stamp_fix_commit

        plan_id = 'gh-held-then-released'
        plan_context.plan_dir_for(plan_id)
        (hash_id,) = _stage_comments(plan_id, [_inline_comment('C1', 'PRRT_fix', 'Guard the null case.')])
        resolve_finding(plan_id, hash_id, 'fixed', detail='Will be addressed by TASK-7.', fix_task_number=7)

        first, first_calls, _ = self._post(plan_id)
        assert first['count_deferred_until_commit'] == 1
        assert first_calls == []

        stamped = stamp_fix_commit(plan_id, _FIX_COMMIT, fix_task_number=7)
        assert stamped['hash_ids'] == [hash_id]

        second, second_calls, _ = self._post(plan_id)

        assert second['status'] == 'success'
        assert second['count_deferred_until_commit'] == 0
        assert second['deferred_until_commit'] == []
        assert second['responded'] == [
            {'hash_id': hash_id, 'thread_id': 'PRRT_fix', 'transmit_mode': 'thread_reply', 'resolved_on_provider': True}
        ]
        # A reply carrying the stored detail and the short commit id, then the resolve.
        assert len(second_calls) == 2
        assert second_calls[0][1] == {
            'threadId': 'PRRT_fix',
            'body': f'Will be addressed by TASK-7.\n\nFix commit: {_FIX_COMMIT_SHORT}',
        }
        assert second_calls[1][1] == {'threadId': 'PRRT_fix'}

    def test_a_rejected_finding_in_the_same_store_is_transmitted_on_the_first_pass(self, plan_context):
        """The hold reaches ``fixed`` only: a ``rejected`` neighbour goes out at once."""
        from _findings_core import resolve_finding

        plan_id = 'gh-held-beside-rejected'
        plan_context.plan_dir_for(plan_id)
        fixed_hash, rejected_hash = _stage_comments(
            plan_id,
            [
                _inline_comment('C1', 'PRRT_fixed', 'Guard the null case.'),
                _inline_comment('C2', 'PRRT_rejected', 'Rename this to match the other module.'),
            ],
        )
        resolve_finding(plan_id, fixed_hash, 'fixed', detail='Will be addressed by TASK-7.', fix_task_number=7)
        resolve_finding(plan_id, rejected_hash, 'rejected', detail='Not a defect: the name is the public API.')

        result, calls, _ = self._post(plan_id)

        assert [row['hash_id'] for row in result['responded']] == [rejected_hash]
        assert [row['hash_id'] for row in result['deferred_until_commit']] == [fixed_hash]
        assert [variables['threadId'] for _mutation, variables in calls] == ['PRRT_rejected', 'PRRT_rejected']
        assert calls[0][1]['body'] == 'Not a defect: the name is the public API.'

    def test_an_inline_fix_is_held_and_released_by_the_same_two_steps(self, plan_context):
        """A ``fixed`` finding with no fix-task number is held exactly like a task fix.

        The predicate reads the stamp alone. The by-finding stamp is the form an
        inline fix uses, since it has no task to select on.
        """
        from _findings_core import resolve_finding

        plan_id = 'gh-held-inline-fix'
        plan_context.plan_dir_for(plan_id)
        (hash_id,) = _stage_comments(plan_id, [_inline_comment('C1', 'PRRT_inline', 'Fix the typo.')])
        detail = 'Addressed by an edit to src/Main.java.'
        resolve_finding(plan_id, hash_id, 'fixed', detail=detail)

        first, first_calls, _ = self._post(plan_id)
        assert first_calls == []
        assert first['deferred_until_commit'] == [
            {'hash_id': hash_id, 'reason': 'no_fix_commit', 'fix_commit_sha': '', 'fix_task_number': ''}
        ]

        _stamp_fix_commit(plan_id, hash_id)
        second, second_calls, _ = self._post(plan_id)

        assert second['count_deferred_until_commit'] == 0
        assert [row['hash_id'] for row in second['responded']] == [hash_id]
        assert second_calls[0][1]['body'] == f'{detail}\n\nFix commit: {_FIX_COMMIT_SHORT}'
        assert second_calls[1][1] == {'threadId': 'PRRT_inline'}

    @pytest.mark.parametrize(
        ('compare', 'returncode', 'head_sha', 'reason'),
        [
            pytest.param('diverged', 0, 'stub-head-sha', 'fix_commit_not_on_pr_head', id='diverged'),
            pytest.param('behind', 0, 'stub-head-sha', 'fix_commit_not_on_pr_head', id='behind'),
            pytest.param('', 1, 'stub-head-sha', 'fix_commit_ancestry_unreadable', id='compare-failed'),
            pytest.param('surprise', 0, 'stub-head-sha', 'fix_commit_ancestry_unreadable', id='unknown-state'),
            pytest.param('ahead', 0, '', 'pr_head_unreadable', id='head-unreadable'),
        ],
    )
    def test_a_stamp_that_is_not_shown_to_reach_the_head_still_holds(
        self, compare, returncode, head_sha, reason, plan_context
    ):
        """A stamp alone does not release the reply; the commit must reach the head.

        Each row is a state in which that is not established, and each keeps the
        finding held with its own reason.
        """
        from _findings_core import resolve_finding

        plan_id = f'gh-held-stamped-{reason.replace("_", "-")}-{compare or "none"}'
        plan_context.plan_dir_for(plan_id)
        (hash_id,) = _stage_comments(plan_id, [_inline_comment('C1', 'PRRT_wait', 'Guard the null case.')])
        resolve_finding(plan_id, hash_id, 'fixed', detail='Fixed the guard.')
        _stamp_fix_commit(plan_id, hash_id)

        with patch('github_pr._github.fetch_pr_head_sha', return_value=head_sha):
            result, calls, _ = self._post(plan_id, compare=compare, compare_returncode=returncode)

        assert calls == []
        assert result['status'] == 'success'
        assert result['deferred_until_commit'] == [
            {'hash_id': hash_id, 'reason': reason, 'fix_commit_sha': _FIX_COMMIT, 'fix_task_number': ''}
        ]

    def test_a_stamped_commit_identical_to_the_head_releases_the_reply(self, plan_context):
        """⛔ MATCHED CONTROL for the rows above — same finding, the other compare answer."""
        from _findings_core import resolve_finding

        plan_id = 'gh-held-stamped-identical'
        plan_context.plan_dir_for(plan_id)
        (hash_id,) = _stage_comments(plan_id, [_inline_comment('C1', 'PRRT_wait', 'Guard the null case.')])
        resolve_finding(plan_id, hash_id, 'fixed', detail='Fixed the guard.')
        _stamp_fix_commit(plan_id, hash_id)

        result, calls, compare_mock = self._post(plan_id, compare='identical')

        assert result['deferred_until_commit'] == []
        assert [row['hash_id'] for row in result['responded']] == [hash_id]
        assert len(calls) == 2
        # The provider was asked about this commit against this head, once.
        assert compare_mock.call_count == 1
        endpoint = compare_mock.call_args.args[0][1]
        assert endpoint.endswith(f'/compare/{_FIX_COMMIT}...stub-head-sha')

    def test_a_threadless_fixed_finding_is_held_out_of_the_batch_and_then_joins_it(self, plan_context):
        """The hold is applied before the kind routing, so it covers the batched path too."""
        from _findings_core import resolve_finding

        plan_id = 'gh-held-threadless'
        plan_context.plan_dir_for(plan_id)
        review_body = {
            'id': 'RB1',
            'kind': 'review_body',
            'author': 'reviewer',
            'body': 'The summary raises a missing guard.',
            'path': '',
            'line': 0,
            'thread_id': '',
        }
        (hash_id,) = _stage_comments(plan_id, [review_body])
        resolve_finding(plan_id, hash_id, 'fixed', detail='Fixed the guard.')

        posted = []

        def _fake_post(pr_number, body):
            posted.append(body)
            return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

        with patch('github_pr._github.post_pr_comment', side_effect=_fake_post):
            first, _, _ = self._post(plan_id)
            assert posted == []
            assert [row['hash_id'] for row in first['deferred_until_commit']] == [hash_id]

            _stamp_fix_commit(plan_id, hash_id)
            second, _, _ = self._post(plan_id)

        assert second['deferred_until_commit'] == []
        assert second['responded'][0]['transmit_mode'] == 'batched_issue_comment'
        assert len(posted) == 1
        assert f'Fixed the guard.\n\nFix commit: {_FIX_COMMIT_SHORT}' in posted[0]

    @pytest.mark.parametrize('resolution', ['suppressed', 'accepted', 'taken_into_account', 'rejected'])
    def test_the_other_dispositions_are_never_held_and_ask_the_provider_nothing(self, resolution, plan_context):
        """Only ``fixed`` is held. The others go out unchanged, with no compare read."""
        from _findings_core import resolve_finding

        plan_id = f'gh-not-held-{resolution.replace("_", "-")}'
        plan_context.plan_dir_for(plan_id)
        (hash_id,) = _stage_comments(plan_id, [_inline_comment('C1', 'PRRT_now', 'Guard the null case.')])
        resolve_finding(plan_id, hash_id, resolution, detail='The stored rationale.')

        result, calls, compare_mock = self._post(plan_id)

        compare_mock.assert_not_called()
        assert result['deferred_until_commit'] == []
        assert [row['hash_id'] for row in result['responded']] == [hash_id]
        assert calls[0][1]['body'] == 'The stored rationale.'


def test_post_responses_against_a_resolved_empty_store_is_a_genuine_success(plan_context):
    """Matched negative control: a resolved store with nothing to send still succeeds."""
    plan_id = 'gh-store-empty-respond'
    plan_context.plan_dir_for(plan_id)

    result = cmd_post_responses(_StoreArgs(704, plan_id))

    assert result['status'] == 'success', result
    assert result['count_responded'] == 0
    assert result['count_untransmitted'] == 0
