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

import bot_registry
import pytest
from _github_pr_fixtures import (
    ACKNOWLEDGMENT_BOT_KIND,
    ACKNOWLEDGMENT_BOT_LOGIN,
    CODERABBIT_ACKNOWLEDGMENT_COUNT,
    CODERABBIT_ACKNOWLEDGMENTS,
    CODERABBIT_FULL_REVIEW_ACKNOWLEDGMENTS,
    CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT,
    CODERABBIT_NO_UNREVIEWED_COMMIT_REPLIES,
    CODERABBIT_SUMMARY_CONCERN_SECTION,
    CODERABBIT_SUMMARY_MARKER,
    HUMAN_COMMENT_QUOTING_AN_ACKNOWLEDGMENT,
    coderabbit_in_progress_summaries,
    coderabbit_summary_bodies,
)
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
# The clean-review verdict: the bot's finished-review marker followed by the sentence that
# says its review found nothing. Built from the registry marker so a renamed marker moves
# both the fixture and the producer that gates on it.
_CODERABBIT_CLEAN_VERDICT = (
    f'{bot_registry.participation_evidence_marker("coderabbit", "issue_comment")}  '
    'No actionable comments were generated in the recent review. 🎉'
)


class _StoreArgs:
    """The two attributes both verbs read off their namespace."""

    def __init__(self, pr_number, plan_id):
        self.pr_number = pr_number
        self.plan_id = plan_id


def _fetch_over(comments, args):
    """Run ``cmd_fetch_findings`` over a fixed provider comment list."""
    with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
        mock_fetch.return_value = {
            'status': 'success',
            'provider': 'github',
            'comments': comments,
            'total': len(comments),
            'unresolved': len(comments),
        }
        return cmd_fetch_findings(args)


_SUBSTANTIVE_COMMENT = {
    'id': 'C-store-1',
    'kind': 'inline',
    'author': 'reviewer',
    'body': 'Please guard the empty-input branch before indexing.',
    'path': 'src/Loop.java',
    'line': 12,
    'thread_id': 'gh-thread-store-1',
}


class TestIsObviousNoise:
    """Pre-filter must drop obvious noise but keep substantive content."""

    @pytest.mark.parametrize(
        'body',
        [
            pytest.param('', id='empty-body'),
            pytest.param('lgtm', id='lgtm'),
            pytest.param('LGTM', id='lgtm-uppercase'),
        ],
    )
    def test_obvious_noise_is_dropped(self, body):
        assert _is_obvious_noise(body)

    def test_substantive_content_is_not_noise(self):
        body = 'This needs to be fixed because of a security issue with input validation.'

        assert not _is_obvious_noise(body)


_ACKNOWLEDGMENT_PARAMS = [pytest.param(body, id=case_id) for case_id, body, _provenance in CODERABBIT_ACKNOWLEDGMENTS]
assert _ACKNOWLEDGMENT_PARAMS, 'the declared acknowledgment population is empty'
_FULL_REVIEW_ACKNOWLEDGMENT_PARAMS = [
    pytest.param(body, id=case_id) for case_id, body, _provenance in CODERABBIT_FULL_REVIEW_ACKNOWLEDGMENTS
]
assert _FULL_REVIEW_ACKNOWLEDGMENT_PARAMS, 'the full-review acknowledgment population is empty'


def _fetch_without_provider_reads(comments, args):
    """Run ``_fetch_over`` with the two provider reads a non-empty fetch also makes stubbed.

    The autouse stub covers the auth check and the HEAD SHA. A fetch that carries
    comments additionally reads the merge candidate's commit time and may measure the
    diff through the raw ``gh`` seam; both are held here so no case shells out.
    """
    with (
        patch.object(github_pr._github, 'fetch_pr_head_committed_at', return_value=''),
        patch.object(github_pr._github, 'run_gh', return_value=(0, '{"additions": 9, "deletions": 3}', '')),
    ):
        return _fetch_over(comments, args)


def _bot_comment(comment_id, body, *, kind='issue_comment'):
    """A comment from the acknowledging bot, in the shape the provider fetch returns."""
    return {
        'id': comment_id,
        'kind': kind,
        'author': ACKNOWLEDGMENT_BOT_LOGIN,
        'body': body,
        'path': '',
        'line': 0,
        'thread_id': '',
        'resolved': False,
    }


class TestAcknowledgmentIsNoise:
    """A bot's confirmation that a command was received files no finding."""

    def test_the_population_is_the_declared_pair_and_the_full_review_replies(self):
        """Non-vacuity: the cases below run over both declared wordings and both full-review replies."""
        assert CODERABBIT_ACKNOWLEDGMENT_COUNT == len(_ACKNOWLEDGMENT_PARAMS) == 4
        assert len(CODERABBIT_FULL_REVIEW_ACKNOWLEDGMENTS) == 2

    @pytest.mark.parametrize('body', _ACKNOWLEDGMENT_PARAMS)
    def test_an_acknowledgment_from_the_declaring_bot_is_noise(self, body):
        assert _is_obvious_noise(body, ACKNOWLEDGMENT_BOT_KIND)

    @pytest.mark.parametrize('body', _FULL_REVIEW_ACKNOWLEDGMENT_PARAMS)
    def test_a_full_review_reply_is_noise_only_under_the_case_insensitive_match(self, body):
        """The reply carries the declared literal in other letter case, and is still dropped.

        The body does NOT contain the literal case-sensitively — the premise that made
        it a stored finding before the match folded case — yet it is noise now.
        """
        declared = bot_registry.acknowledgment_patterns(ACKNOWLEDGMENT_BOT_KIND)
        assert not any(literal in body for literal in declared)
        assert _is_obvious_noise(body, ACKNOWLEDGMENT_BOT_KIND)

    def test_fetch_findings_drops_the_full_review_replies_and_files_the_genuine_comment(self, plan_context):
        """Through the verb: both full-review replies are noise, the same bot's genuine comment is filed."""
        plan_id = 'gh-ack-full-review-noise'
        plan_context.plan_dir_for(plan_id)
        replies = [
            _bot_comment(f'IC-ack-{case_id}', body)
            for case_id, body, _provenance in CODERABBIT_FULL_REVIEW_ACKNOWLEDGMENTS
        ]
        genuine = _bot_comment('IC-genuine-full', CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT)

        result = _fetch_without_provider_reads([*replies, genuine], _StoreArgs(707, plan_id))

        assert result['status'] == 'success'
        assert result['count_skipped_noise'] == len(CODERABBIT_FULL_REVIEW_ACKNOWLEDGMENTS)
        assert result['count_stored'] == 1
        assert result['count_skipped_refusal'] == 0

    def test_a_genuine_short_comment_from_the_same_bot_is_not_noise(self):
        """NEGATIVE control: same bot, same length class, but feedback about the code."""
        assert not _is_obvious_noise(CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT, ACKNOWLEDGMENT_BOT_KIND)

    def test_a_human_quoting_an_acknowledgment_is_not_noise(self):
        """NEGATIVE control: the class is scoped to the bot that declared the literal."""
        assert not _is_obvious_noise(HUMAN_COMMENT_QUOTING_AN_ACKNOWLEDGMENT)

    def test_fetch_findings_skips_both_acknowledgments_and_files_the_genuine_comment(self, plan_context):
        """Through the verb: two acknowledgments are dropped as noise, one comment is filed.

        The genuine comment rides the SAME fetch from the SAME bot, so a filter that
        dropped every short comment from this bot would fail here on ``count_stored``.
        """
        plan_id = 'gh-ack-noise-filed'
        plan_context.plan_dir_for(plan_id)
        acknowledgments = [
            _bot_comment(f'IC-ack-{case_id}', body) for case_id, body, _provenance in CODERABBIT_ACKNOWLEDGMENTS
        ]
        genuine = _bot_comment('IC-genuine-1', CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT)

        result = _fetch_without_provider_reads([*acknowledgments, genuine], _StoreArgs(706, plan_id))

        assert result['status'] == 'success'
        assert result['count_fetched'] == CODERABBIT_ACKNOWLEDGMENT_COUNT + 1
        assert result['count_skipped_noise'] == CODERABBIT_ACKNOWLEDGMENT_COUNT
        assert result['count_stored'] == 1
        # Not a refusal: an acknowledgment arms no recovery and names no refusing bot.
        assert result['count_skipped_refusal'] == 0
        assert not result.get('unrecognised_refusal')

    def test_fetch_findings_files_nothing_for_acknowledgments_alone(self, plan_context):
        """MATCHED CONTROL: the same fetch without the genuine comment stores nothing."""
        plan_id = 'gh-ack-noise-only'
        plan_context.plan_dir_for(plan_id)
        acknowledgments = [
            _bot_comment(f'IC-ack-{case_id}', body) for case_id, body, _provenance in CODERABBIT_ACKNOWLEDGMENTS
        ]

        result = _fetch_without_provider_reads(acknowledgments, _StoreArgs(706, plan_id))

        assert result['status'] == 'success'
        assert result['count_skipped_noise'] == CODERABBIT_ACKNOWLEDGMENT_COUNT
        assert result['count_stored'] == 0
        assert result['count_skipped_refusal'] == 0


class TestSummaryConcernIsFiled:
    """A concern CodeRabbit raises only in its summary must reach the findings store.

    The summary marker and the ``## Walkthrough`` heading are boilerplate, not a finding;
    they became conditional drops so that a summary carrying a concern section is filed
    while a summary carrying nothing but boilerplate is not. Every case below runs the
    real producer verb, because the drop happens inside its noise pre-filter and a
    predicate-only assertion would not prove which counter moved.
    """

    def test_the_two_summary_shapes_differ_only_in_the_concern_section(self):
        """Non-vacuity: the concern body is the control body plus its concern section.

        Without this the two cases could pass while testing two unrelated bodies, and the
        control would prove nothing about the marker that dropped the concern.
        """
        bodies = {case_id: body for case_id, body, _provenance in coderabbit_summary_bodies()}
        concern = bodies['summary-with-concern']
        control = bodies['summary-plain-walkthrough']

        assert concern != control
        assert concern.replace('\n\n' + CODERABBIT_SUMMARY_CONCERN_SECTION, '') == control, (
            'the concern body is not the control body plus one section'
        )
        for case_id, _body, provenance in coderabbit_summary_bodies():
            assert provenance in {'observed', 'constructed', 'reconstructed'}, (case_id, provenance)

    def test_a_summary_that_carries_only_a_concern_files_one_finding(self, plan_context):
        """The defect: this body is dropped by the summary marker and files nothing at HEAD."""
        plan_id = 'gh-summary-concern-filed'
        plan_context.plan_dir_for(plan_id)
        bodies = {case_id: body for case_id, body, _p in coderabbit_summary_bodies()}
        comment = _bot_comment('IC-summary-concern', bodies['summary-with-concern'])

        result = _fetch_without_provider_reads([comment], _StoreArgs(712, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1, result
        assert result['count_skipped_noise'] == 0, result
        assert result['count_skipped_refusal'] == 0, result

    def test_the_matched_control_plain_walkthrough_still_files_nothing(self, plan_context):
        """MATCHED CONTROL: the same body minus the concern section stays noise."""
        plan_id = 'gh-summary-plain-walkthrough'
        plan_context.plan_dir_for(plan_id)
        bodies = {case_id: body for case_id, body, _p in coderabbit_summary_bodies()}
        comment = _bot_comment('IC-summary-plain', bodies['summary-plain-walkthrough'])

        result = _fetch_without_provider_reads([comment], _StoreArgs(713, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 0, result
        assert result['count_skipped_noise'] == 1, result

    def test_one_fetch_tells_the_two_apart(self, plan_context):
        """Both shapes in one fetch: the concern is filed, the boilerplate is dropped."""
        plan_id = 'gh-summary-concern-and-control'
        plan_context.plan_dir_for(plan_id)
        comments = [_bot_comment(f'IC-summary-{case_id}', body) for case_id, body, _p in coderabbit_summary_bodies()]

        result = _fetch_without_provider_reads(comments, _StoreArgs(714, plan_id))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 2
        assert result['count_stored'] == 1, result
        assert result['count_skipped_noise'] == 1, result

    def test_a_summary_carrying_only_an_actionable_section_is_filed(self, plan_context):
        """The actionable section is the veto's fourth member, and it fires the same way.

        A summary that names its actionable comments without rendering a nitpick,
        outside-diff or follow-up section is the highest-severity case the veto exists
        for, so it must file rather than drop.
        """
        plan_id = 'gh-summary-actionable-only'
        plan_context.plan_dir_for(plan_id)
        body = (
            f'{CODERABBIT_SUMMARY_MARKER}\n'
            '## Walkthrough\n\n'
            'The change gates participation credit on a per-shape content marker.\n\n'
            '**Actionable comments posted: 2**'
        )
        comment = _bot_comment('IC-summary-actionable', body)

        result = _fetch_without_provider_reads([comment], _StoreArgs(722, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1, result
        assert result['count_skipped_noise'] == 0, result

    def test_both_in_progress_summaries_are_still_noise(self, plan_context):
        """The in-progress states carry the marker but no concern, and stay noise.

        One of them carries ``## Walkthrough`` and one carries only the "Currently
        processing new changes" notice, so a drop keyed on either heading alone would file
        the other.
        """
        plan_id = 'gh-summary-in-progress-noise'
        plan_context.plan_dir_for(plan_id)
        summaries = coderabbit_in_progress_summaries('a' * 40, 'b' * 40)
        comments = [_bot_comment(f'IC-in-progress-{case_id}', body) for case_id, body, _p in summaries]

        result = _fetch_without_provider_reads(comments, _StoreArgs(715, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 0, result
        assert result['count_skipped_noise'] == len(summaries), result

    def test_the_clean_review_verdict_is_still_noise(self, plan_context):
        """A verdict comment that reports no actionable comments files nothing."""
        plan_id = 'gh-summary-clean-verdict-noise'
        plan_context.plan_dir_for(plan_id)
        comment = _bot_comment('IC-clean-verdict', _CODERABBIT_CLEAN_VERDICT)

        result = _fetch_without_provider_reads([comment], _StoreArgs(716, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 0, result
        assert result['count_skipped_noise'] == 1, result

    def test_the_skip_notice_summary_still_files_nothing(self, plan_context):
        """The "Review skipped / no new commits" notice is a refusal, not a finding."""
        plan_id = 'gh-summary-skip-notice'
        plan_context.plan_dir_for(plan_id)
        skip_notice = {case_id: body for case_id, body, _p in CODERABBIT_NO_UNREVIEWED_COMMIT_REPLIES}['no-new-commits']
        comment = _bot_comment('IC-skip-notice', skip_notice)

        result = _fetch_without_provider_reads([comment], _StoreArgs(717, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 0, result
        assert result['count_skipped_noise'] == 0, result
        assert result['count_skipped_refusal'] == 1, result

    def test_a_finished_summary_that_also_carries_a_rate_limit_block_is_a_refusal(self, plan_context):
        """PINNED SHAPE: a readable coverage marker does not outrank the refusal branch here.

        CodeRabbit edits its one summary comment in place, so a comment that had been a
        finished review can present, later, as a rate-limit notice carrying its
        ``final_review_risk_coverage`` marker over an earlier head. The participation loop
        reads that marker (``review_coverage_is_finished``) to keep the credit; the filing
        loop's refusal branch reads ``_is_refusal_notice`` alone, so the body is counted in
        ``count_skipped_refusal`` and files nothing. That behaviour is pinned, not changed:
        the live shape carries no concern section, so no finding is lost through it today,
        and a concern section riding this shape would need its own deliverable.
        """
        plan_id = 'gh-summary-finished-plus-refusal'
        plan_context.plan_dir_for(plan_id)
        sha = 'a' * 40
        body = (
            f'{CODERABBIT_SUMMARY_MARKER}\n'
            '## Walkthrough\n\n'
            'The change gates participation credit on a per-shape content marker.\n\n'
            f'<!-- final_review_risk_coverage:{{"sourceCommitId":"{sha}","coveredCommitId":"{sha}",'
            '"kind":"reviewed"} -->\n\n'
            '> [!WARNING]\n'
            '> ## Review limit reached\n'
            '>\n'
            '> You have used the included review currently available.\n'
        )
        # The marker IS readable — the pin is that the filing loop does not consult it.
        import _github_pr

        assert _github_pr.review_coverage_is_finished(body) is True
        comment = _bot_comment('IC-finished-plus-refusal', body)

        result = _fetch_without_provider_reads([comment], _StoreArgs(721, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 0, result
        assert result['count_skipped_refusal'] == 1, result
        assert result['refused_bots'] == ['coderabbit']
        assert result['refused_causes'] == [{'bot_kind': 'coderabbit', 'cause': 'quota'}]


class TestPRMain:
    """Test github_pr.py main entry point (CLI plumbing)."""

    def test_no_subcommand(self):
        result = run_script(SCRIPT_PATH)

        assert result.returncode != 0

    def test_help_lists_only_supported_subcommands(self):
        result = run_script(SCRIPT_PATH, '--help')

        assert result.returncode == 0
        assert 'fetch-comments' in result.stdout
        assert 'fetch_findings' in result.stdout
        assert 'post_responses' in result.stdout
        # Retired surfaces MUST be absent from the CLI
        assert 'comments-stage' not in result.stdout
        assert 'triage-batch' not in result.stdout
        assert '--comments ' not in result.stdout

    @pytest.mark.parametrize(
        'argv',
        [
            pytest.param(['triage', '--comment', '{}'], id='triage-rejected'),
            pytest.param(['triage-batch', '--comments', '[]'], id='triage-batch-rejected'),
            pytest.param(['comments-stage', '--pr-number', '1', '--plan-id', 'x'], id='comments-stage-rejected'),
        ],
    )
    def test_retired_subcommand_rejected(self, argv):
        result = run_script(SCRIPT_PATH, *argv)

        assert result.returncode != 0


@pytest.mark.parametrize(
    'verb',
    [
        pytest.param('fetch_findings', id='fetch_findings'),
        pytest.param('post_responses', id='post_responses'),
    ],
)
def test_the_two_zeros_are_distinguishable_in_one_comparison(plan_context, verb):
    """The property the whole scenario turns on, stated as a single comparison.

    Asserting the refusal and the benign zero in separate tests leaves open that they
    still agree on the field a caller branches on. Before the guard both verbs
    answered the two cases with the SAME ``status: success`` envelope.
    """
    resolved_id = f'gh-store-pair-{verb}'
    plan_context.plan_dir_for(resolved_id)
    absent_id = f'gh-store-pair-missing-{verb}'

    if verb == 'fetch_findings':
        benign = _fetch_over([], _StoreArgs(705, resolved_id))
        absent = _fetch_over([], _StoreArgs(705, absent_id))
    else:
        benign = cmd_post_responses(_StoreArgs(705, resolved_id))
        absent = cmd_post_responses(_StoreArgs(705, absent_id))

    assert benign['status'] != absent['status']
    assert absent['findings_store_state'] == 'plan_absent'
    assert 'findings_store_state' not in benign or benign['findings_store_state'] != 'plan_absent'
