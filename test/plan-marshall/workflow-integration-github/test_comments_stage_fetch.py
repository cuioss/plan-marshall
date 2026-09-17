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


def _assert_store_refusal(payload, root):
    """Assert ``payload`` is the store's own refusal, naming the root it looked under."""
    assert payload.get('status') == 'error', payload
    assert payload.get('error') == 'findings_store_unresolved', (
        "the provider must re-publish the store's own error code rather than mint a "
        f'second vocabulary for the same fact: {payload}'
    )
    assert payload.get('findings_store_state') == 'plan_absent'
    assert payload.get('unresolved_store') is True
    assert str(root) in str(payload.get('message', '')), (
        "the refusal must carry the store's provenance naming the resolved root"
    )


class TestFetchCommentsWrapper:
    """fetch_comments() forwards the provider envelope verbatim."""

    def test_fetch_comments_success(self):
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': [
                    {
                        'id': 'C1',
                        'kind': 'inline',
                        'author': 'reviewer',
                        'body': 'fix this',
                        'path': 'src/Main.java',
                        'line': 42,
                        'thread_id': 'PRRT_abc',
                    }
                ],
                'total': 1,
                'unresolved': 1,
            }
            result = fetch_comments(123, unresolved_only=False)

        assert result['status'] == 'success'
        assert result['pr_number'] == 123
        assert result['comments'][0]['kind'] == 'inline'

    def test_fetch_comments_provider_error(self):
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {'status': 'error', 'error': 'Auth failed'}
            result = fetch_comments(123)

        assert result['status'] == 'error'


class TestPerBotIgnoreFilter:
    """The producer noise pre-filter layers shared regexes with per-bot registry markers.

    The shared ``ignore`` regexes from comment-patterns.json apply to every
    comment; each bot's ``ignore_patterns`` from its registry doc are literal
    whole-comment markers that apply ONLY to that bot's own comments. A marker
    for one bot must never drop another bot's (or a human's) comment.
    """

    def test_shared_noise_drops_regardless_of_bot_kind(self):
        """A shared acknowledgment (``lgtm``) is noise for every author."""
        assert _is_obvious_noise('lgtm', 'coderabbit')
        assert _is_obvious_noise('lgtm', None)

    def test_per_bot_marker_drops_only_its_own_bot(self):
        """CodeRabbit's ``## Walkthrough`` marker drops a coderabbit comment only."""
        body = '## Walkthrough\n\nThis PR changes a few files.'
        # Dropped for the owning bot.
        assert _is_obvious_noise(body, 'coderabbit')
        # NOT dropped for a different bot or a human — the marker is bot-scoped.
        assert not _is_obvious_noise(body, 'cuioss-review-bot')
        assert not _is_obvious_noise(body, None)

    def test_pr_agent_walkthrough_marker_drops_only_pr_agent(self):
        """PR-Agent's ``## PR Agent Walkthrough`` marker drops a cuioss-review-bot comment only.

        The two bots' markers are deliberately near-identical in shape
        (``## Walkthrough`` vs ``## PR Agent Walkthrough``), which makes this the
        sharpest available test of bot-scoping: a substring-based or unscoped
        filter would cross-drop.
        """
        body = '## PR Agent Walkthrough\n\nAvailable commands: /review, /ask, /help.'
        assert _is_obvious_noise(body, 'cuioss-review-bot')
        assert not _is_obvious_noise(body, 'coderabbit')
        assert not _is_obvious_noise(body, None)

    def test_marker_of_a_retired_bot_drops_nothing(self):
        """A marker sourced from a DELETED registry doc drops no comment at all.

        With the record gone the pre-filter has no per-bot layer to apply for that
        kind, so a body carrying its former marker is treated as ordinary content.
        This is the correct failure mode for retirement: comments stop being
        filtered, never start being silently dropped by a phantom rule.
        """
        body = 'This reviewer is being sunset on 2026-07-17.'
        assert not _is_obvious_noise(body, 'retired-bot')
        assert not _is_obvious_noise(body, 'coderabbit')
        assert not _is_obvious_noise(body, None)

    def test_substantive_bot_comment_is_not_noise(self):
        """A real finding from a bot survives the pre-filter."""
        body = 'This null dereference needs a guard before the call on line 42.'
        assert not _is_obvious_noise(body, 'coderabbit')

    def test_fetch_findings_drops_per_bot_walkthrough_keeps_substantive(self, plan_context):
        """End-to-end: a coderabbit walkthrough is dropped; a substantive one is stored."""
        comments = [
            {
                'id': 'W1',
                'kind': 'issue_comment',
                'author': 'coderabbitai',
                'body': '## Walkthrough\n\nThis PR touches three files and adds a helper.',
                'path': '',
                'line': 0,
                'thread_id': '',
            },
            {
                'id': 'W2',
                'kind': 'inline',
                'author': 'coderabbitai',
                'body': 'This off-by-one indexes past the end of the array; guard the bound.',
                'path': 'src/Idx.java',
                'line': 12,
                'thread_id': 'PRRT_w2',
            },
        ]

        plan_context.plan_dir_for('gh-pr-perbot-walkthrough')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(150, 'gh-pr-perbot-walkthrough'))

        assert result['status'] == 'success'
        # The walkthrough is dropped as noise; only the substantive finding is stored.
        assert result['count_stored'] == 1
        assert result['count_skipped_noise'] == 1
        # count_stored == expected_stored, so no producer-mismatch Q-Gate fires.
        assert result['producer_mismatch_hash_id'] is None

        from _findings_core import query_findings

        q = query_findings('gh-pr-perbot-walkthrough', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        # The surviving finding is the substantive comment (W2), not the walkthrough (W1).
        assert 'comment_id: W2' in q['findings'][0]['detail']

    def test_fetch_findings_does_not_apply_one_bots_marker_to_another(self, plan_context):
        """A cuioss-review-bot comment carrying CodeRabbit's ``## Walkthrough`` text is NOT dropped.

        Proves the per-bot layer is scoped to the authoring bot: the walkthrough
        marker belongs to coderabbit's registry entry, so a cuioss-review-bot-authored
        comment with the same heading survives and becomes a finding.
        """
        comments = [
            {
                'id': 'G1',
                'kind': 'issue_comment',
                'author': 'cuioss-review-bot',
                'body': '## Walkthrough\n\nPR-Agent would not normally emit this, but it must not be cross-dropped.',
                'path': '',
                'line': 0,
                'thread_id': '',
            },
        ]

        plan_context.plan_dir_for('gh-pr-perbot-crossbot')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(151, 'gh-pr-perbot-crossbot'))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1
        assert result['count_skipped_noise'] == 0


class TestRefusalNoticeProducerFilter:
    """Every reviewer bot's refusal is RECOGNIZED as a refusal by some arm of the stack.

    The arms consulted at THIS position are the registry-data and structural ones;
    the enumerative arm runs later in the pipeline and is exercised separately in
    ``TestUnrecognisedRefusalPredicate``.

    The recognizer under test is ``_is_refusal_notice``, never ``_is_obvious_noise``.
    That separation is the contract: ``_is_obvious_noise`` must NOT recognize a
    refusal, because a refusal it swallows is a declined review the quorum layer
    never sees.
    """

    def test_sourcery_1014_refusal_recognized_via_registry_data_layer(self):
        """The Sourcery size-limit refusal is seen ONLY because it is filed as data.

        This is the case that regressed. The structural recognizer does not match
        this phrasing (no limit-EXCEEDED statement — "larger than the review limit
        of" is a comparison, not an "exceeded/reached/hit" statement), which is
        asserted explicitly below. So recognition can only come from the registry
        marker resolved through ``bot_kind='sourcery'`` — which is exactly what
        makes this a proof that the data layer fired, not the fallback.
        """
        from _github_pr import _is_rate_limit_notice, _is_refusal_notice

        # The structural last-resort layer is BLIND to this phrasing...
        assert not _is_rate_limit_notice(_SOURCERY_1014_REFUSAL)
        # ...so the registry data layer is what recognizes it, bot-scoped.
        assert _is_refusal_notice(_SOURCERY_1014_REFUSAL, 'sourcery')
        # And it stays bot-scoped: the same text from another bot or a human is
        # not cross-matched by Sourcery's marker.
        assert not _is_refusal_notice(_SOURCERY_1014_REFUSAL, 'coderabbit')
        assert not _is_refusal_notice(_SOURCERY_1014_REFUSAL, None)

    def test_coderabbit_review_limit_refusal_recognized(self):
        """CodeRabbit's review-summary ``Review limit reached`` notice is a refusal."""
        from _github_pr import _is_refusal_notice

        assert _is_refusal_notice(_CODERABBIT_REVIEW_LIMIT_REFUSAL, 'coderabbit')

    def test_coderabbit_command_reply_refusal_recognized_via_registry_data_layer(self):
        """The COMMAND-INVOCATION reply refusal is seen, and only as data.

        Every other arm is asserted BLIND to this body first, so a pass here cannot be
        borrowed from a fallback: the structural recognizer sees no limit-EXCEEDED
        statement (the body says "Review rate limited", which carries no
        exceeded/reached/hit verb), and the enumerative arm is vetoed by the
        ``<details>`` code anchor even once a threshold is measured. Recognition can
        therefore only come from the registry marker resolved through
        ``bot_kind='coderabbit'``.
        """
        from _github_pr import (
            REFUSAL_LAYER_REGISTRY,
            _has_code_anchor,
            _is_rate_limit_notice,
            _is_refusal_notice,
            refusal_layers,
        )

        # The structural last-resort arm is BLIND to this phrasing...
        assert not _is_rate_limit_notice(_CODERABBIT_COMMAND_REPLY_REFUSAL)
        # ...and the enumerative arm is vetoed by the <details> anchor regardless of
        # whether a threshold is ever measured, so it can never rescue this body.
        assert _has_code_anchor(_CODERABBIT_COMMAND_REPLY_REFUSAL)
        # ...leaving the registry data arm as the only thing that recognizes it.
        assert refusal_layers(_CODERABBIT_COMMAND_REPLY_REFUSAL, 'coderabbit') == [REFUSAL_LAYER_REGISTRY]
        assert _is_refusal_notice(_CODERABBIT_COMMAND_REPLY_REFUSAL, 'coderabbit')
        # And it stays bot-scoped: no other bot's record, and no human, cross-matches.
        assert not _is_refusal_notice(_CODERABBIT_COMMAND_REPLY_REFUSAL, 'sourcery')
        assert not _is_refusal_notice(_CODERABBIT_COMMAND_REPLY_REFUSAL, None)

    def test_coderabbits_two_refusal_surfaces_are_separately_registered(self):
        """Neither CodeRabbit marker spans the other, so registering one covers neither.

        The discriminator for the wording above. "Review limit reached" (the review
        SUMMARY notice) and "Review rate limited" (the COMMAND reply) differ by more
        than presentation, and matching is case-sensitive substring containment — so a
        registry holding only the first leaves the second invisible, which is exactly
        how a refusal was credited as a completion signal.
        """
        import bot_registry

        markers = bot_registry.refusal_patterns('coderabbit')
        matched_by_summary = [m for m in markers if m in _CODERABBIT_REVIEW_LIMIT_REFUSAL]
        matched_by_command_reply = [m for m in markers if m in _CODERABBIT_COMMAND_REPLY_REFUSAL]
        assert matched_by_summary, 'the review-summary refusal must stay registered'
        assert matched_by_command_reply, 'the command-reply refusal must be registered too'
        assert not set(matched_by_summary) & set(matched_by_command_reply)

    def test_an_ordinary_coderabbit_finding_is_not_read_as_a_refusal(self):
        """⛔ NEGATIVE CONTROL for the added wording — real feedback stays a finding.

        The added marker is narrow on purpose. Widening it to the reply's
        ``Action not completed`` wrapper, or to the auto-generated-reply HTML marker
        this body also carries, would start matching genuine review feedback — and the
        failure would be silent, because a finding read as a refusal is dropped from
        the store rather than erroring.
        """
        from _github_pr import _is_rate_limit_notice, _is_refusal_notice, refusal_layers

        assert refusal_layers(_CODERABBIT_GENUINE_INLINE, 'coderabbit') == []
        assert not _is_refusal_notice(_CODERABBIT_GENUINE_INLINE, 'coderabbit')
        assert not _is_rate_limit_notice(_CODERABBIT_GENUINE_INLINE)
        assert not _is_obvious_noise(_CODERABBIT_GENUINE_INLINE, 'coderabbit')

    def test_sourcery_has_two_distinct_registered_refusal_modes(self):
        """Both observed Sourcery refusal phrasings are filed as registry data.

        Observation refutes the assumption that one recogniser covers this bot:
        the weekly diff-character QUOTA is a different mode from the per-PR SIZE
        ceiling, and neither marker matches the other's text. Each observed
        mode must therefore have its own ``refusal_patterns`` entry — filing only one
        leaves the other invisible, which is how a refused review reached the merge
        gate as a clean one.
        """
        import bot_registry
        from _github_pr import _is_refusal_notice

        assert _is_refusal_notice(_SOURCERY_WEEKLY_QUOTA_REFUSAL, 'sourcery')
        # The two modes are genuinely distinct: neither registry marker spans both.
        markers = bot_registry.refusal_patterns('sourcery')
        matched_by_size_ceiling = [m for m in markers if m in _SOURCERY_1014_REFUSAL]
        matched_by_weekly_quota = [m for m in markers if m in _SOURCERY_WEEKLY_QUOTA_REFUSAL]
        assert matched_by_size_ceiling, 'the #1014 size-ceiling refusal must stay registered'
        assert matched_by_weekly_quota, 'the weekly-quota refusal must be registered too'
        assert not set(matched_by_size_ceiling) & set(matched_by_weekly_quota)

    @pytest.mark.parametrize(
        'bot_kind', [None, 'coderabbit', 'sourcery', 'cuioss-review-bot'], ids=['human', 'cr', 'sr', 'pra']
    )
    def test_a_refusal_is_never_classified_as_noise(self, bot_kind):
        """``_is_obvious_noise`` must not recognize ANY refusal, for ANY bot.

        The pre-filter defect this pins: unioning ``refusal_patterns`` into the noise
        drop set — and short-circuiting on the structural rate-limit recognizer —
        made ``_is_obvious_noise`` discard the very evidence the dedicated
        ``refusal_patterns`` field exists to identify. Against that behaviour the
        registry-recognized bodies below returned True here.
        """
        for body in (
            _SOURCERY_1014_REFUSAL,
            _SOURCERY_WEEKLY_QUOTA_REFUSAL,
            _CODERABBIT_REVIEW_LIMIT_REFUSAL,
            _CODERABBIT_COMMAND_REPLY_REFUSAL,
            _SOURCERY_SHAPED_REFUSAL,
            _UNKNOWN_BOT_REFUSAL,
        ):
            assert not _is_obvious_noise(body, bot_kind), (bot_kind, body[:40])

    def test_genuine_review_mentioning_a_limit_is_neither_refusal_nor_noise(self):
        """A substantive review that merely mentions a limit survives both predicates.

        Precision guard for every arm of the stack: no registry marker matches, the
        structural recognizer sees a review-voiced "exceeds" with no notice shape,
        and the enumerative arm declines it too (asserted in
        ``TestUnrecognisedRefusalPredicate``), so the comment survives the
        pre-filter and becomes a finding.
        """
        from _github_pr import _is_rate_limit_notice, _is_refusal_notice

        assert not _is_rate_limit_notice(_GENUINE_REVIEW_MENTIONING_A_LIMIT)
        for bot_kind in ('sourcery', 'coderabbit', None):
            assert not _is_refusal_notice(_GENUINE_REVIEW_MENTIONING_A_LIMIT, bot_kind)
            assert not _is_obvious_noise(_GENUINE_REVIEW_MENTIONING_A_LIMIT, bot_kind)

    def test_unknown_bot_refusal_recognized_by_structural_fallback(self):
        """An unregistered bot's refusal is still recognized — via the structural layer.

        The author resolves to no ``bot_kind``, so no registry marker can apply.
        The notice is recognized by shape alone (limit-exceeded statement + alert
        callout), which is precisely the last-resort layer's job.
        """
        from _github_pr import _is_rate_limit_notice, _is_refusal_notice

        assert _is_rate_limit_notice(_UNKNOWN_BOT_REFUSAL)
        assert _is_refusal_notice(_UNKNOWN_BOT_REFUSAL, None)

    def test_fetch_findings_surfaces_sourcery_refusal_and_keeps_genuine_review(self, plan_context):
        """End-to-end producer path: the refusal is surfaced, files no finding, is not noise.

        Against the pre-fix drop-as-noise behaviour the refusal landed in
        ``count_skipped_noise``, ``count_skipped_refusal`` and ``refused_bots`` did
        not exist, and the quorum layer had no way to tell a declined review from a
        bot that simply had not answered yet.
        """
        comments = [
            {
                'id': 'R1',
                'kind': 'issue_comment',
                'author': 'sourcery-ai',
                'body': _SOURCERY_1014_REFUSAL,
                'path': '',
                'line': 0,
                'thread_id': '',
            },
            {
                'id': 'R2',
                'kind': 'inline',
                'author': 'sourcery-ai',
                'body': _GENUINE_REVIEW_MENTIONING_A_LIMIT,
                'path': 'src/Retry.java',
                'line': 31,
                'thread_id': 'PRRT_r2',
            },
        ]

        plan_context.plan_dir_for('gh-pr-refusal-sourcery')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(160, 'gh-pr-refusal-sourcery'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 2
        # The refusal is the ONLY non-store, and it is accounted for as a REFUSAL...
        assert result['count_skipped_refusal'] == 1
        assert result['refused_bots'] == ['sourcery']
        # ...never as noise.
        assert result['count_skipped_noise'] == 0
        assert result['count_stored'] == 1
        assert result['producer_mismatch_hash_id'] is None

        from _findings_core import query_findings

        q = query_findings('gh-pr-refusal-sourcery', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        # The surviving finding is the genuine review (R2), never the refusal (R1) —
        # a refusal is a signal about the review, not something to triage.
        assert 'comment_id: R2' in q['findings'][0]['detail']

    def test_fetch_findings_counts_the_command_reply_refusal_and_keeps_the_real_finding(self, plan_context):
        """End-to-end: the command reply is a REFUSAL, not an actionable finding.

        This is the observed producer half of the defect. Unrecognized, the reply
        survived the pre-filter and was stored as a ``pr-comment`` finding — so triage
        was handed CodeRabbit's apology to dispose of, while ``count_skipped_refusal``
        stayed at zero and the quorum layer saw no refusal at all.

        The genuine inline finding in the same batch is the negative control: it must
        still reach the store, or the fix would have bought refusal accounting at the
        price of dropping real feedback.
        """
        comments = [
            {
                'id': 'C1',
                'kind': 'issue_comment',
                'author': 'coderabbitai',
                'body': _CODERABBIT_COMMAND_REPLY_REFUSAL,
                'path': '',
                'line': 0,
                'thread_id': '',
            },
            {
                'id': 'C2',
                'kind': 'inline',
                'author': 'coderabbitai',
                'body': _CODERABBIT_GENUINE_INLINE,
                'path': 'src/Retry.java',
                'line': 31,
                'thread_id': 'PRRT_c2',
            },
        ]

        plan_context.plan_dir_for('gh-pr-refusal-cr-command-reply')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(1368, 'gh-pr-refusal-cr-command-reply'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 2
        # Accounted for as a REFUSAL, with the bot named for the quorum layer...
        assert result['count_skipped_refusal'] == 1
        assert result['refused_bots'] == ['coderabbit']
        # ...never as noise, and never as something for triage to dispose of.
        assert result['count_skipped_noise'] == 0
        assert result['count_stored'] == 1

        from _findings_core import query_findings

        q = query_findings('gh-pr-refusal-cr-command-reply', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        assert 'comment_id: C2' in q['findings'][0]['detail']

    def test_detect_rate_limited_bots_answers_per_registered_bot(self):
        """The wait-return discriminator answers per REGISTERED bot, not per one bot.

        The retired discriminator selected CodeRabbit-authored comments only, so a
        refusing Sourcery scored negative whenever CodeRabbit's own newest comment
        was a genuine review — the two bots' states were collapsed into one answer.
        The registry-driven detector reports each bot independently: CodeRabbit is
        absent because its newest comment is real feedback, while Sourcery appears
        with the class its own registry record declares.
        """
        import github_re_review
        from _github_pr import REFUSAL_LAYER_STRUCTURAL, _detect_rate_limited_bots

        comments = [
            {
                'author': 'coderabbitai[bot]',
                'body': 'Actionable comments posted: 1. Guard the array bound here.',
                'created_at': '2026-01-02T00:00:00Z',
            },
            {
                'author': 'sourcery-ai[bot]',
                'body': _SOURCERY_SHAPED_REFUSAL,
                'created_at': '2026-01-09T00:00:00Z',
            },
        ]

        # The record carries BOTH axes: the declared awaitability class and the
        # per-refusal cause. This body is structurally shaped rather than a declared
        # size marker, so its cause is the ``quota`` default and it states no cap.
        # It also discloses the observation itself: the arm that read the notice
        # (the structural one — no Sourcery registry marker matches this phrasing)
        # and the notice as the producer excerpts it, derived through the same
        # ``_body_excerpt`` the producer calls rather than restated as a literal.
        assert _detect_rate_limited_bots(comments) == [
            {
                'bot_kind': 'sourcery',
                'rate_limit_class': 'hard_quota',
                'eta': '',
                'cause': 'quota',
                'cap': '',
                'layer': REFUSAL_LAYER_STRUCTURAL,
                'body': github_re_review._body_excerpt(_SOURCERY_SHAPED_REFUSAL),
            }
        ]

    def test_detect_rate_limited_bots_ignores_human_quoting_refusal(self):
        """A human quoting a full refusal notice never trips the discriminator.

        Authorship is resolved through the registry login map, so a human author
        belongs to no ``bot_kind`` and contributes no record no matter what their
        comment quotes.
        """
        from _github_pr import _detect_rate_limited_bots

        comments = [
            {
                'author': 'octocat',
                'body': _CODERABBIT_REVIEW_LIMIT_REFUSAL,
                'created_at': '2026-01-09T00:00:00Z',
            },
        ]

        assert _detect_rate_limited_bots(comments) == []


class TestFailLoudUnconfigured:
    """Both verbs return a typed ``unconfigured`` status when GitHub is not authed."""

    def test_fetch_findings_unconfigured_is_not_silent_success(self, plan_context):
        plan_context.plan_dir_for('gh-unconfigured-fetch')
        with patch('github_pr._github.check_auth', return_value=(False, 'Not authenticated. Run gh auth login.')):
            result = cmd_fetch_findings(_stage_make_args(200, 'gh-unconfigured-fetch'))

        assert result['status'] == 'unconfigured'
        assert result['operation'] == 'fetch_findings'
        assert result['provider'] == 'github'
        # No findings were filed on the unconfigured path.
        from _findings_core import query_findings

        assert query_findings('gh-unconfigured-fetch', finding_type='pr-comment')['filtered_count'] == 0

    def test_post_responses_unconfigured_is_not_silent_success(self, plan_context):
        plan_context.plan_dir_for('gh-unconfigured-respond')
        with patch('github_pr._github.check_auth', return_value=(False, 'Not authenticated.')):
            result = cmd_post_responses(_stage_make_args(200, 'gh-unconfigured-respond'))

        assert result['status'] == 'unconfigured'
        assert result['operation'] == 'post_responses'


def test_fetch_findings_refuses_a_plan_absent_from_the_resolved_root(plan_context):
    """Positive control: the dedup read refuses instead of reading an empty key set.

    An empty key set is not a harmless default here — it says "none of these comments
    has ever been filed", so the producer would re-file the PR's entire comment
    history against a store it never reached.
    """
    plan_id = 'gh-store-absent-fetch'
    root = plan_context.fixture_dir
    assert not (plan_context.plans_dir / plan_id).exists(), (
        'the plan directory must be ABSENT for this to be the unreached-store case'
    )

    result = _fetch_over([_SUBSTANTIVE_COMMENT], _StoreArgs(700, plan_id))

    _assert_store_refusal(result, root)
    # The pre-guard answer, excluded explicitly: a success carrying a stored count.
    assert 'count_stored' not in result, (
        'a refused fetch must publish no count — a count computed against a store '
        'nobody reached is exactly the defect under test'
    )


def test_fetch_findings_against_a_resolved_empty_store_is_a_genuine_success(plan_context):
    """Matched negative control: a resolved store that has filed nothing still fetches.

    Without this direction the refusal above is equally consistent with a fix that
    turned EVERY empty finding list into an error, which would break the first fetch
    of every plan — nothing has been filed yet at that point, by construction.
    """
    plan_id = 'gh-store-empty-fetch'
    plan_context.plan_dir_for(plan_id)

    result = _fetch_over([_SUBSTANTIVE_COMMENT], _StoreArgs(701, plan_id))

    assert result['status'] == 'success', result
    assert result['count_fetched'] == 1
    assert result['count_stored'] == 1, (
        'the comment must still be filed — the guard keys on the unreached store, never on an empty finding list'
    )
    assert result['count_skipped_duplicate'] == 0


def test_fetch_findings_still_dedupes_on_a_resolved_populated_store(plan_context):
    """Matched positive control on the happy path: the read still feeds the dedup.

    A guard that refused the read outright — or a refactor that dropped it — would
    pass both tests above while silently disabling the cross-iteration dedup, so the
    second fetch of an unchanged comment must still skip it.
    """
    plan_id = 'gh-store-dedupe-fetch'
    plan_context.plan_dir_for(plan_id)

    first = _fetch_over([_SUBSTANTIVE_COMMENT], _StoreArgs(702, plan_id))
    second = _fetch_over([_SUBSTANTIVE_COMMENT], _StoreArgs(702, plan_id))

    assert first['count_stored'] == 1, first
    assert second['count_stored'] == 0, second
    assert second['count_skipped_duplicate'] == 1, second
