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


_SOURCERY_1014_REFUSAL = (
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
_SUBSTANTIVE_COMMENT = {
    'id': 'C-store-1',
    'kind': 'inline',
    'author': 'reviewer',
    'body': 'Please guard the empty-input branch before indexing.',
    'path': 'src/Loop.java',
    'line': 12,
    'thread_id': 'gh-thread-store-1',
}


class TestCommentsStageReviewedShaAndBotKind:
    """Every stored pr-comment finding carries the PR HEAD SHA at ingestion
    time (``reviewed_commit_sha``) and the reviewer-bot identity derived from
    the comment author login (``bot_kind``).

    The producer stamps these two re-review-matching fields at ingestion:
    ``reviewed_commit_sha`` is the PR HEAD SHA fetched once for the whole batch
    (so re-review matching can tell whether HEAD has advanced past the reviewed
    commit), and ``bot_kind`` is derived from each comment's author login via the
    registry's ``bot_kind_for_author`` (coderabbitai -> coderabbit,
    cuioss-review-bot -> cuioss-review-bot; a human author leaves ``bot_kind`` unset).
    """

    def test_reviewed_commit_sha_stamped_from_pr_head(self, plan_context):
        """Each stored finding's ``reviewed_commit_sha`` equals the fetched PR HEAD SHA."""
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

        plan_context.plan_dir_for('gh-pr-reviewed-sha')
        with (
            patch('github_pr._github.fetch_pr_comments_data') as mock_fetch,
            patch('github_pr._github.fetch_pr_head_sha', return_value='abc123def456') as mock_head,
        ):
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(140, 'gh-pr-reviewed-sha'))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1
        # HEAD SHA is fetched once for the whole batch, not per comment.
        assert mock_head.call_count == 1

        from _findings_core import query_findings

        q = query_findings('gh-pr-reviewed-sha', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        assert stored['reviewed_commit_sha'] == 'abc123def456'

    @pytest.mark.parametrize(
        ('author', 'expected_bot_kind'),
        [
            pytest.param('coderabbitai', 'coderabbit', id='coderabbit'),
            pytest.param('cuioss-review-bot', 'cuioss-review-bot', id='cuioss-review-bot'),
            pytest.param('sourcery-ai', 'sourcery', id='sourcery'),
        ],
    )
    def test_bot_kind_derived_from_author_login(self, author, expected_bot_kind, plan_context):
        """The stored finding's ``bot_kind`` is the canonical key for a known bot login."""
        comments = [
            {
                'id': 'B1',
                'kind': 'inline',
                'author': author,
                'body': 'A substantive review point about error propagation here.',
                'path': 'src/Worker.java',
                'line': 17,
                'thread_id': 'PRRT_b',
            },
        ]

        plan_id = f'gh-pr-botkind-{expected_bot_kind}'
        plan_context.plan_dir_for(plan_id)
        with (
            patch('github_pr._github.fetch_pr_comments_data') as mock_fetch,
            patch('github_pr._github.fetch_pr_head_sha', return_value='headsha00'),
        ):
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(141, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1

        from _findings_core import query_findings

        q = query_findings(plan_id, finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        assert stored['bot_kind'] == expected_bot_kind
        # The bot_kind is queryable as a first-class filter.
        by_bot = query_findings(plan_id, finding_type='pr-comment', bot_kind=expected_bot_kind)
        assert by_bot['filtered_count'] == 1

    def test_non_bot_author_leaves_bot_kind_unset_without_error(self, plan_context):
        """A comment from an unrecognised (human) login stores a finding with no
        ``bot_kind`` field — gracefully, not as an error.

        The producer derives ``bot_kind`` via the registry's
        ``bot_kind_for_author``, which returns ``None`` for any login outside
        the bot registry. ``add_finding`` then omits the field entirely (it is
        only written when present), so a human-authored comment yields a valid
        finding with ``bot_kind`` absent — never a rejection.
        """
        comments = [
            {
                'id': 'H1',
                'kind': 'inline',
                'author': 'human-reviewer',
                'body': 'Please rename this variable for clarity and consistency.',
                'path': 'src/B.java',
                'line': 9,
                'thread_id': 'PRRT_h',
            },
        ]

        plan_context.plan_dir_for('gh-pr-botkind-human')
        with (
            patch('github_pr._github.fetch_pr_comments_data') as mock_fetch,
            patch('github_pr._github.fetch_pr_head_sha', return_value='headsha01'),
        ):
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(142, 'gh-pr-botkind-human'))

        # No error: the finding is stored successfully.
        assert result['status'] == 'success'
        assert result['count_stored'] == 1
        assert result['producer_mismatch_hash_id'] is None

        from _findings_core import query_findings

        q = query_findings('gh-pr-botkind-human', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        # author is still recorded; bot_kind is simply absent (not 'unknown').
        assert stored['author'] == 'human-reviewer'
        assert 'bot_kind' not in stored


class TestPRProjectDirPlumbing:
    """Verify github_pr.main() strips --project-dir and forwards cwd."""

    def test_main_project_dir_sets_default_cwd(self):
        import ci_base

        saved_argv = sys.argv
        saved_cwd = ci_base.get_default_cwd()
        try:
            ci_base.set_default_cwd(None)
            sys.argv = [
                'github_pr.py',
                '--project-dir',
                '/tmp/worktree-pr',
                'fetch-comments',
                '--pr',
                '999',
            ]
            with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
                mock_fetch.return_value = {
                    'status': 'success',
                    'provider': 'github',
                    'comments': [],
                    'total': 0,
                    'unresolved': 0,
                }
                github_pr.main()

            assert ci_base.get_default_cwd() == '/tmp/worktree-pr'
            assert '--project-dir' not in sys.argv
        finally:
            sys.argv = saved_argv
            ci_base.set_default_cwd(saved_cwd)


class TestPRTwoStateRoutingContract:
    """Two-state ``--plan-id`` / ``--project-dir`` routing for github_pr.main().

    Mirrors the github_ops.main() contract: router-level --plan-id is
    consumed by extract_routing_args and resolved via manage-status to
    install the default cwd; --project-dir keeps working as the legacy
    escape hatch; both together → mutually_exclusive_args TOON error.
    """

    def test_main_plan_id_sets_default_cwd_via_manage_status_resolution(self):
        """Router-level --plan-id auto-routes to the persisted worktree path."""
        # file_ops holds the manage-status shell-out seam; resolve_project_dir
        # delegates the worktree face to it via resolve_plan_context.
        import ci_base
        import file_ops as _resolver_core

        saved_argv = sys.argv
        saved_cwd = ci_base.get_default_cwd()
        try:
            ci_base.set_default_cwd(None)
            sys.argv = [
                'github_pr.py',
                '--plan-id',
                'task-routing-canonical',
                'fetch-comments',
                '--pr',
                '999',
            ]
            with (
                patch.object(
                    _resolver_core,
                    '_query_worktree_path',
                    return_value=worktree_query_result(True, '/tmp/wt-pr-resolved'),
                ),
                patch('github_pr._github.fetch_pr_comments_data') as mock_fetch,
            ):
                mock_fetch.return_value = {
                    'status': 'success',
                    'provider': 'github',
                    'comments': [],
                    'total': 0,
                    'unresolved': 0,
                }
                github_pr.main()

            assert ci_base.get_default_cwd() == '/tmp/wt-pr-resolved'
        finally:
            sys.argv = saved_argv
            ci_base.set_default_cwd(saved_cwd)

    def test_main_emits_mutually_exclusive_error_on_both_flags(self):
        """Both router-level routing flags → mutually_exclusive_args + exit 2."""
        saved_argv = sys.argv
        try:
            sys.argv = [
                'github_pr.py',
                '--plan-id',
                'task-routing-canonical',
                '--project-dir',
                '/tmp/explicit',
                'fetch-comments',
                '--pr',
                '999',
            ]
            buf = io.StringIO()
            with pytest.raises(SystemExit) as exc_info:
                with redirect_stdout(buf):
                    github_pr.main()

            assert exc_info.value.code == 2
            assert 'mutually_exclusive_args' in buf.getvalue()
        finally:
            sys.argv = saved_argv
