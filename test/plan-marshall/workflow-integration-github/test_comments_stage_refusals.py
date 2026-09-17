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


class TestCommentsStage:
    """comments-stage writes one pr-comment finding per surviving comment."""

    def test_stage_persists_substantive_comments_only(self, plan_context):
        comments = [
            {
                'id': 'C1',
                'kind': 'inline',
                'author': 'reviewer',
                'body': 'Please fix the null pointer here',
                'path': 'src/Main.java',
                'line': 42,
                'thread_id': 'PRRT_a',
            },
            {
                'id': 'C2',
                'kind': 'review_body',
                'author': 'reviewer',
                'body': 'lgtm',
                'path': '',
                'line': 0,
                'thread_id': 'PRRT_b',
            },
        ]

        plan_context.plan_dir_for('gh-pr-stage-1')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            result = cmd_fetch_findings(_stage_make_args(123, 'gh-pr-stage-1'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 2
        assert result['count_skipped_noise'] == 1
        assert result['count_stored'] == 1
        assert result['producer_mismatch_hash_id'] is None

        # Verify the finding made it into the per-type store.
        from _findings_core import query_findings

        q = query_findings('gh-pr-stage-1', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        assert stored['type'] == 'pr-comment'
        assert stored['file_path'] == 'src/Main.java'
        assert stored['line'] == 42
        # The detail carries the trusted structured metadata (kind, thread_id, ...).
        assert 'kind: inline' in stored['detail']
        assert 'thread_id: PRRT_a' in stored['detail']
        # The untrusted body is quarantined under raw_input.{body}, NOT in detail.
        assert 'Please fix the null pointer here' not in stored['detail']
        assert stored['raw_input']['body'] == 'Please fix the null pointer here'

    def test_stage_skips_resolved_thread_comments(self, plan_context):
        """Comments on already-resolved threads are dropped by pre-filter 1 before the noise check; each drop increments count_skipped_noise.

        The ``resolved`` field is set by the provider (github_ops) on inline
        comments whose parent thread is ``isResolved=True``. Producer-side
        pre-filter 1 drops these before the noise check so they never reach
        the finding store.
        """
        comments = [
            {
                'id': 'C1',
                'kind': 'inline',
                'author': 'reviewer',
                'body': 'This concern was already addressed',
                'path': 'src/Main.java',
                'line': 10,
                'thread_id': 'PRRT_resolved',
                'resolved': True,
            },
            {
                'id': 'C2',
                'kind': 'inline',
                'author': 'reviewer',
                'body': 'This is still an open concern that needs fixing',
                'path': 'src/Other.java',
                'line': 20,
                'thread_id': 'PRRT_open',
                'resolved': False,
            },
        ]

        plan_context.plan_dir_for('gh-pr-stage-resolved')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': 1,
            }
            result = cmd_fetch_findings(_stage_make_args(127, 'gh-pr-stage-resolved'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 2
        # Resolved thread comment is counted in skipped_noise
        assert result['count_skipped_noise'] == 1
        assert result['count_stored'] == 1
        assert result['producer_mismatch_hash_id'] is None

        from _findings_core import query_findings

        q = query_findings('gh-pr-stage-resolved', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        # Only the open-thread comment survives
        assert 'PRRT_open' in stored['detail']
        assert 'PRRT_resolved' not in stored['detail']

    def test_stage_no_comments(self, plan_context):
        plan_context.plan_dir_for('gh-pr-stage-empty')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': [],
                'total': 0,
                'unresolved': 0,
            }
            result = cmd_fetch_findings(_stage_make_args(124, 'gh-pr-stage-empty'))

        assert result['count_fetched'] == 0
        assert result['count_stored'] == 0
        assert result['producer_mismatch_hash_id'] is None

    def test_stage_provider_error_propagates(self, plan_context):
        plan_context.plan_dir_for('gh-pr-stage-err')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {'status': 'error', 'error': 'auth'}
            result = cmd_fetch_findings(_stage_make_args(125, 'gh-pr-stage-err'))

        assert result['status'] == 'error'

    def test_stage_count_mismatch_produces_qgate_finding(self, plan_context):
        """When count_stored != expected_stored, a (producer-mismatch) Q-Gate
        finding must be recorded so the LLM consumer sees the drift via
        manage-findings qgate query."""
        comments = [
            {
                'id': 'C1',
                'kind': 'inline',
                'author': 'reviewer',
                'body': 'This is a substantive review comment about a real issue.',
                'path': 'src/Main.java',
                'line': 42,
                'thread_id': 'PRRT_a',
            },
            {
                'id': 'C2',
                'kind': 'inline',
                'author': 'reviewer',
                'body': 'Another substantive comment about a different problem.',
                'path': 'src/Other.java',
                'line': 7,
                'thread_id': 'PRRT_b',
            },
        ]

        plan_context.plan_dir_for('gh-pr-stage-mismatch')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': len(comments),
                'unresolved': len(comments),
            }
            # Force one add_finding call to fail so count_stored drifts
            # below expected_stored; the second succeeds.
            with patch('_findings_core.add_finding') as mock_add:

                def _side_effect(**kwargs):
                    # First call (C1) fails; second (C2) succeeds.
                    if mock_add.call_count == 1:
                        return {'status': 'error', 'message': 'simulated store failure'}
                    return {'status': 'success', 'hash_id': 'hash-' + str(mock_add.call_count)}

                mock_add.side_effect = _side_effect
                result = cmd_fetch_findings(_stage_make_args(126, 'gh-pr-stage-mismatch'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 2
        assert result['count_skipped_noise'] == 0
        assert result['count_stored'] == 1
        assert result['producer_mismatch_hash_id'] is not None

        from _findings_core import query_qgate_findings

        q = query_qgate_findings('gh-pr-stage-mismatch', phase='5-execute')
        assert q['filtered_count'] == 1
        qf = q['findings'][0]
        assert qf['title'].startswith('(producer-mismatch)')
        assert qf['source'] == 'qgate'
        assert qf['type'] == 'pr-comment'

    def test_stage_review_body_no_thread_id_dedups_across_iterations(self, plan_context):
        """A review_body comment (no thread_id) staged once must NOT re-surface
        as a second finding on a subsequent fetch of the same comment.

        Regression for the cross-iteration phantom loop: review_body / issue
        comments carry no thread_id, so a resolution from a prior finalize
        iteration cannot be matched back on the next fetch. Without comment_id
        dedup, the same comment re-enters as a fresh pending finding every time
        HEAD advances, producing an endless finalize loop. The producer-side
        guard skips a thread_id-less comment whose comment_id is already in the
        pr-comment store, counting it as count_skipped_duplicate.
        """
        # Same review_body comment seen on both fetches: substantive (survives
        # the noise pre-filter), no thread_id, stable comment_id.
        comment = {
            'id': 'RB1',
            'kind': 'review_body',
            'author': 'reviewer',
            'body': 'The error handling here drops the original exception context.',
            'path': '',
            'line': 0,
            'thread_id': '',
        }

        plan_context.plan_dir_for('gh-pr-stage-dedup')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': [comment],
                'total': 1,
                'unresolved': 1,
            }
            # Iteration 1 — first fetch stores the comment.
            result_1 = cmd_fetch_findings(_stage_make_args(128, 'gh-pr-stage-dedup'))
            # Iteration 2 — HEAD advanced; the identical comment is fetched
            # again but must be deduped, not re-stored.
            result_2 = cmd_fetch_findings(_stage_make_args(128, 'gh-pr-stage-dedup'))

        # First pass: stored, no dedup, no producer mismatch.
        assert result_1['status'] == 'success'
        assert result_1['count_fetched'] == 1
        assert result_1['count_skipped_noise'] == 0
        assert result_1['count_skipped_duplicate'] == 0
        assert result_1['count_stored'] == 1
        assert result_1['producer_mismatch_hash_id'] is None

        # Second pass: deduped by comment_id (no thread_id), nothing stored,
        # and the dedup is accounted for in expected_stored so NO spurious
        # producer-mismatch Q-Gate finding is raised.
        assert result_2['status'] == 'success'
        assert result_2['count_fetched'] == 1
        assert result_2['count_skipped_noise'] == 0
        assert result_2['count_skipped_duplicate'] == 1
        assert result_2['count_stored'] == 0
        assert result_2['producer_mismatch_hash_id'] is None

        # The store holds exactly ONE pr-comment finding — no phantom duplicate.
        from _findings_core import query_findings

        q = query_findings('gh-pr-stage-dedup', finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        assert 'comment_id: RB1' in stored['detail']
        assert 'kind: review_body' in stored['detail']

    def test_stage_new_comment_id_still_stored_on_second_iteration(self, plan_context):
        """A genuinely new review_body comment_id IS stored on a later fetch.

        The cross-iteration dedup must not over-reach: a thread_id-less comment
        whose comment_id has NOT been staged before is a real new comment and
        must produce a fresh finding even after a prior iteration already
        stored a different comment.
        """
        first = {
            'id': 'RB1',
            'kind': 'review_body',
            'author': 'reviewer',
            'body': 'The error handling here drops the original exception context.',
            'path': '',
            'line': 0,
            'thread_id': '',
        }
        second = {
            'id': 'RB2',
            'kind': 'review_body',
            'author': 'reviewer',
            'body': 'This new comment flags a different concern about retries.',
            'path': '',
            'line': 0,
            'thread_id': '',
        }

        plan_context.plan_dir_for('gh-pr-stage-newid')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            # Iteration 1 — only the first comment exists.
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': [first],
                'total': 1,
                'unresolved': 1,
            }
            result_1 = cmd_fetch_findings(_stage_make_args(129, 'gh-pr-stage-newid'))

            # Iteration 2 — both the old comment (deduped) and a brand-new
            # comment (RB2) are fetched. RB2 must be stored.
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': [first, second],
                'total': 2,
                'unresolved': 2,
            }
            result_2 = cmd_fetch_findings(_stage_make_args(129, 'gh-pr-stage-newid'))

        assert result_1['count_stored'] == 1
        assert result_1['count_skipped_duplicate'] == 0

        # Second pass: RB1 deduped, RB2 stored — no producer mismatch.
        assert result_2['status'] == 'success'
        assert result_2['count_fetched'] == 2
        assert result_2['count_skipped_noise'] == 0
        assert result_2['count_skipped_duplicate'] == 1
        assert result_2['count_stored'] == 1
        assert result_2['producer_mismatch_hash_id'] is None

        # The store now holds exactly TWO findings — RB1 (from iter 1) and RB2.
        from _findings_core import query_findings

        q = query_findings('gh-pr-stage-newid', finding_type='pr-comment')
        assert q['filtered_count'] == 2
        stored_ids = {
            m.group('id') for m in (github_pr._COMMENT_ID_DETAIL.search(f['detail'] or '') for f in q['findings']) if m
        }
        assert stored_ids == {'RB1', 'RB2'}


class TestRefusalLayerVocabulary:
    """The layer vocabulary is ONE shared object, and its members are stable."""

    def test_definition_site_is_the_shared_refusal_module(self):
        """``_github_pr`` is where the vocabulary is DEFINED, beside the recognisers.

        Both refusal consumers import it from here rather than declaring their own
        copy. That each consumer actually reads THIS object (identity, not equality
        — a parallel vocabulary would compare equal while drifting on the next edit)
        is asserted in each consumer's own suite: the re-review path in
        ``test_re_review_strategy.py``, the producer path in ``test_github_pr.py``.
        """
        import _github_pr

        assert isinstance(_github_pr.REFUSAL_LAYERS, tuple)
        assert _github_pr.REFUSAL_LAYER_ENUMERATIVE in _github_pr.REFUSAL_LAYERS

    def test_preexisting_layer_values_keep_their_exact_spellings(self):
        """The two pre-existing values are byte-identical to their former inline literals.

        Read from the constants rather than restated, so this asserts the shipped
        value rather than re-declaring it.
        """
        import _github_pr

        assert _github_pr.REFUSAL_LAYER_REGISTRY == 'registry_refusal_patterns'
        assert _github_pr.REFUSAL_LAYER_STRUCTURAL == 'structural_fallback'

    def test_every_declared_layer_is_a_distinct_non_empty_string(self):
        """The vocabulary's population is derived from the constant and published.

        A population read from the constant cannot pass vacuously over an empty or
        shrunken vocabulary: the size is asserted against the distinct-member count
        AND against a floor naming the arms this suite knows must exist.
        """
        import _github_pr

        layers = _github_pr.REFUSAL_LAYERS
        population_size = len(layers)
        # Published so a shrunken vocabulary is visible in the failure message.
        assert population_size >= 3, f'layer vocabulary shrank to {population_size}: {layers}'
        assert all(isinstance(layer, str) and layer for layer in layers), layers
        assert len(set(layers)) == population_size, f'duplicate layer members in {layers}'
        # Each named constant is a MEMBER of the iterated population, so a constant
        # that drifted out of the tuple fails rather than being silently unused.
        for member in (
            _github_pr.REFUSAL_LAYER_REGISTRY,
            _github_pr.REFUSAL_LAYER_STRUCTURAL,
            _github_pr.REFUSAL_LAYER_ENUMERATIVE,
        ):
            assert member in layers, (member, layers)

    def test_enumerative_member_is_distinct_from_the_two_pre_existing_ones(self):
        """The third member is genuinely new — it does not alias either existing value."""
        import _github_pr

        assert _github_pr.REFUSAL_LAYER_ENUMERATIVE not in (
            _github_pr.REFUSAL_LAYER_REGISTRY,
            _github_pr.REFUSAL_LAYER_STRUCTURAL,
        )


class TestUnrecognisedRefusalPredicate:
    """``_is_unrecognised_refusal`` recognises a refusal no earlier arm matched.

    Every positive case below has a matched negative control, so no assertion can
    pass vacuously.
    """

    def test_ships_inert_because_no_threshold_was_derived(self):
        """At the SHIPPED value the arm never fires — for any input.

        This is the fail-safe the whole design rests on: D1's corpus yielded no
        genuine review comment, so no character bound is derivable, and an arm that
        errs in the merge-BLOCKING direction must not fire on a bound nobody
        measured.
        """
        import _github_pr

        assert _github_pr.UNRECOGNISED_REFUSAL_MAX_CHARS is None
        for body in (
            _REWORDED_REFUSAL,
            _SHORT_REVIEW_WITH_ANCHOR,
            _GENUINE_REVIEW_MENTIONING_A_LIMIT,
            _SOURCERY_1014_REFUSAL,
        ):
            for bot_kind in ('coderabbit', 'sourcery', 'cuioss-review-bot', None):
                assert not _github_pr._is_unrecognised_refusal(body, bot_kind), (bot_kind, body[:40])

    def test_fires_on_a_short_anchorless_body_from_a_registered_bot(self, monkeypatch):
        """The positive case — with a threshold available, the arm recognises the rewording."""
        import _github_pr

        monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 200)

        # Neither earlier arm sees it — that is what makes it "unrecognised".
        assert not _github_pr._is_refusal_notice(_REWORDED_REFUSAL, 'cuioss-review-bot')
        assert _github_pr._is_unrecognised_refusal(_REWORDED_REFUSAL, 'cuioss-review-bot')

    def test_declines_a_body_carrying_a_code_anchor_however_short(self, monkeypatch):
        """Matched negative control for the positive case above: an anchor vetoes the arm.

        The control body is SHORTER than the threshold and authored by the same
        registered bot, so length and authorship are held constant and the code
        anchor is the only difference.
        """
        import _github_pr

        monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 200)

        assert len(_SHORT_REVIEW_WITH_ANCHOR) < 200
        assert not _github_pr._is_unrecognised_refusal(_SHORT_REVIEW_WITH_ANCHOR, 'cuioss-review-bot')

    def test_declines_a_human_authored_body(self, monkeypatch):
        """An unresolvable / unregistered author is never an unrecognised refusal.

        Matched against the positive case: the SAME body that fires for a registered
        bot must not fire for a human.
        """
        import _github_pr

        monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 200)

        assert _github_pr._is_unrecognised_refusal(_REWORDED_REFUSAL, 'cuioss-review-bot')
        assert not _github_pr._is_unrecognised_refusal(_REWORDED_REFUSAL, None)
        assert not _github_pr._is_unrecognised_refusal(_REWORDED_REFUSAL, 'not-a-registered-bot')

    def test_declines_a_bots_own_declared_clean_review_text(self, monkeypatch):
        """The false-positive control the ordering decision exists to protect.

        The bodies are READ FROM the bot's own registry ``ignore_patterns`` rather
        than hand-copied, so the assertion tracks the registry rather than a literal
        that could drift out of step with it. Each such marker is short, anchor-less
        and authored by a registered bot — every other condition of the arm holds —
        so this is the case that would misclassify a clean review as a refusal.
        """
        import _github_pr
        import bot_registry

        monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 500)

        markers = bot_registry.ignore_patterns('coderabbit')
        # Population published: an empty registry list would make every assertion
        # below vacuous, so the loop must be proven non-empty first.
        assert markers, 'coderabbit declares no ignore_patterns — the control is vacuous'
        for marker in markers:
            assert not _github_pr._is_unrecognised_refusal(marker, 'coderabbit'), marker

    def test_declines_a_body_an_earlier_arm_already_recognised(self, monkeypatch):
        """This arm never overrides an arm that DID read the notice."""
        import _github_pr

        monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 500)

        # Registry arm recognised it...
        assert _github_pr._is_refusal_notice(_SOURCERY_1014_REFUSAL, 'sourcery')
        assert not _github_pr._is_unrecognised_refusal(_SOURCERY_1014_REFUSAL, 'sourcery')
        # ...and likewise for a structurally-recognised one.
        assert _github_pr._is_refusal_notice(_UNKNOWN_BOT_REFUSAL, 'coderabbit')
        assert not _github_pr._is_unrecognised_refusal(_UNKNOWN_BOT_REFUSAL, 'coderabbit')

    def test_declines_an_empty_body(self, monkeypatch):
        """An empty / unreadable body has its own non-firing branch."""
        import _github_pr

        monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 200)

        assert not _github_pr._is_unrecognised_refusal('', 'cuioss-review-bot')

    def test_declines_a_body_at_or_over_the_threshold(self, monkeypatch):
        """The bound is exclusive, and a long anchor-less body is a genuine review."""
        import _github_pr

        monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', len(_REWORDED_REFUSAL))

        # At exactly the threshold the arm does NOT fire...
        assert not _github_pr._is_unrecognised_refusal(_REWORDED_REFUSAL, 'cuioss-review-bot')
        # ...and one character of headroom is what makes it fire — the matched
        # control proving the boundary is the only thing being tested here.
        monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', len(_REWORDED_REFUSAL) + 1)
        assert _github_pr._is_unrecognised_refusal(_REWORDED_REFUSAL, 'cuioss-review-bot')

    @pytest.mark.parametrize(
        'body',
        [
            pytest.param(_REWORDED_REFUSAL, id='reworded-refusal'),
            pytest.param(_SHORT_REVIEW_WITH_ANCHOR, id='short-review-with-anchor'),
            pytest.param(_GENUINE_REVIEW_MENTIONING_A_LIMIT, id='genuine-review'),
            pytest.param(_SOURCERY_1014_REFUSAL, id='registry-recognised-refusal'),
            pytest.param(_UNKNOWN_BOT_REFUSAL, id='structurally-recognised-refusal'),
            pytest.param('', id='empty'),
        ],
    )
    def test_is_refusal_notice_return_is_unchanged_by_the_new_arm(self, body, monkeypatch):
        """``_is_refusal_notice``'s boolean contract is untouched.

        Asserted with a threshold SET, so the new arm is live while this runs: the
        point is that making the enumerative arm fireable changes nothing about the
        seam its four existing consumers read.
        """
        import _github_pr

        for bot_kind in ('coderabbit', 'sourcery', 'cuioss-review-bot', None):
            monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', None)
            inert = _github_pr._is_refusal_notice(body, bot_kind)
            monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 500)
            live = _github_pr._is_refusal_notice(body, bot_kind)
            assert inert == live, (bot_kind, body[:40])


def test_post_responses_refuses_a_plan_absent_from_the_resolved_root(plan_context):
    """Positive control: an unreached store is a refusal, not "nothing to transmit"."""
    plan_id = 'gh-store-absent-respond'
    root = plan_context.fixture_dir
    assert not (plan_context.plans_dir / plan_id).exists()

    result = cmd_post_responses(_StoreArgs(703, plan_id))

    _assert_store_refusal(result, root)
    # The pre-guard answer, excluded explicitly: a confident all-clear transmission
    # report over a store that was never opened.
    assert 'count_responded' not in result
    assert 'count_untransmitted' not in result
