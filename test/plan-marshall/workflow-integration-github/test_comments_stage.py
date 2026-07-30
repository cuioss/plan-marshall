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
two-layer classification of reviewer-bot REFUSAL notices (registry data layer
plus the structural last-resort recognizer), the fail-loud unconfigured signal,
the hash_id-keyed post_responses respond loop, the ``--project-dir`` plumbing,
and the CLI surface contract (the retired ``triage`` / ``triage-batch`` /
``comments-stage`` subcommands MUST be gone).
"""

import importlib.util
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import get_script_path, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py')

# Tier 2 direct imports — use explicit path to avoid module name collision
# with workflow-integration-gitlab/scripts/gitlab_pr.py
_pr_path = Path(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('github_pr', _pr_path)
assert _spec is not None and _spec.loader is not None
github_pr = importlib.util.module_from_spec(_spec)
sys.modules['github_pr'] = github_pr
_spec.loader.exec_module(github_pr)

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


# =============================================================================
# Pre-filter (_is_obvious_noise) — drops obvious automated/acknowledgment noise
# =============================================================================


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


# =============================================================================
# Provider integration (fetch_comments wrapper)
# =============================================================================


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


# =============================================================================
# comments-stage subcommand (producer-side fetch + filter + store)
# =============================================================================


def _stage_make_args(pr_number: int, plan_id: str):
    class _Args:
        pr_number: int
        plan_id: str

    a = _Args()
    a.pr_number = pr_number
    a.plan_id = plan_id
    return a


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
            m.group('id')
            for m in (
                github_pr._COMMENT_ID_DETAIL.search(f['detail'] or '')
                for f in q['findings']
            )
            if m
        }
        assert stored_ids == {'RB1', 'RB2'}


# =============================================================================
# First-class author / kind fields on stored pr-comment findings
# =============================================================================


class TestCommentsStageAuthorKindFields:
    """Every stored pr-comment finding carries first-class, queryable ``author``
    and ``kind`` fields.

    Deliverable 2 promotes reviewer identity (``author``) and comment structure
    (``kind``) to indexed top-level finding fields (see manage-findings
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


# =============================================================================
# reviewed_commit_sha + bot_kind population on stored pr-comment findings
# =============================================================================


class TestCommentsStageReviewedShaAndBotKind:
    """Every stored pr-comment finding carries the PR HEAD SHA at ingestion
    time (``reviewed_commit_sha``) and the reviewer-bot identity derived from
    the comment author login (``bot_kind``).

    Deliverable 3 stamps these two re-review-matching fields at ingestion:
    ``reviewed_commit_sha`` is the PR HEAD SHA fetched once for the whole batch
    (so re-review matching can tell whether HEAD has advanced past the reviewed
    commit), and ``bot_kind`` is derived from each comment's author login via the
    registry's ``bot_kind_for_author`` (coderabbitai -> coderabbit,
    cuioss-review-bot -> pr-agent; a human author leaves ``bot_kind`` unset).
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
            pytest.param('cuioss-review-bot', 'pr-agent', id='pr-agent'),
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


# =============================================================================
# Per-bot ignore pre-filter (registry-driven, shared-plus-per-bot)
# =============================================================================


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
        assert not _is_obvious_noise(body, 'pr-agent')
        assert not _is_obvious_noise(body, None)

    def test_pr_agent_walkthrough_marker_drops_only_pr_agent(self):
        """PR-Agent's ``## PR Agent Walkthrough`` marker drops a pr-agent comment only.

        The two bots' markers are deliberately near-identical in shape
        (``## Walkthrough`` vs ``## PR Agent Walkthrough``), which makes this the
        sharpest available test of bot-scoping: a substring-based or unscoped
        filter would cross-drop.
        """
        body = '## PR Agent Walkthrough\n\nAvailable commands: /review, /ask, /help.'
        assert _is_obvious_noise(body, 'pr-agent')
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
        """A pr-agent comment carrying CodeRabbit's ``## Walkthrough`` text is NOT dropped.

        Proves the per-bot layer is scoped to the authoring bot: the walkthrough
        marker belongs to coderabbit's registry entry, so a pr-agent-authored
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


# =============================================================================
# Reviewer-bot REFUSAL notices — producer-path classification (regression)
# =============================================================================
#
# A refusal notice is a comment a reviewer bot posts IN PLACE OF a review. It
# carries no actionable feedback — so it files no finding — but it is NOT noise:
# it is positive evidence the bot DECLINED to review, and the producer must SURFACE
# it (``count_skipped_refusal`` + ``refused_bots[]``) so the completeness / quorum
# layer classifies the bot as refused rather than inferring absence from silence.
# Treating a refusal as noise is what let a PR whose every required reviewer refused
# report a clean, complete review with zero review coverage.
#
# Recognition goes through ``_github_pr._is_refusal_notice``, where two layers
# cooperate — the split is the whole point of this section:
#
#   - DATA LAYER (primary) — a REGISTERED bot's OBSERVED refusal text is a
#     literal marker in that bot's ``automatic-review/standards/{bot_kind}.md``
#     ``refusal_patterns``, applied bot-scoped via the resolved ``bot_kind``.
#     Deliberately NOT ``ignore_patterns``, which lists the routine sections of a
#     *successful* review.
#   - STRUCTURAL LAYER (last resort) — ``_is_rate_limit_notice`` recognizes an
#     unknown/unregistered bot's notice, or a phrasing not yet captured as data,
#     by its shape (a limit-exceeded statement paired with a notice shape).
#
# Neither layer is a superset of the other. The #1014 Sourcery refusal below is
# the proof: it is invisible to the structural recognizer (asserted), so ONLY the
# registry marker recognizes it.
#
# Every fixture body uses the FLATTENED single-line shape — ``fetch_pr_comments_data``
# collapses each body's newlines to spaces before any detector runs (the same
# convention documented in test_pr_wait_for_comments_rate_limited.py).

# Sourcery's OBSERVED #1014 refusal: it declined the review because the PR
# exceeded its size budget. Handle-free and number-free in the registry, so the
# marker survives a different account handle and a different character budget.
_SOURCERY_1014_REFUSAL = (
    'Sourcery was unable to review this pull request because '
    'your pull request is larger than the review limit of 150000 characters. '
    'Reduce the size of the pull request and request another review.'
)

# CodeRabbit's CURRENT refusal phrasing (registry marker ``Review limit reached``).
_CODERABBIT_REVIEW_LIMIT_REFUSAL = (
    '> [!WARNING] > ## Review limit reached > '
    'You have reached your review limit for the current billing cycle. '
    'Reviews will resume once the limit resets.'
)

# Sourcery's size-limit refusal in a NOTICE-SHAPED phrasing. The OBSERVED #1014
# wording above is deliberately invisible to the structural recognizer (asserted
# in test_sourcery_1014_refusal_dropped_via_registry_data_layer), and the per-bot
# rate-limit detector on the wait-return classifies on shape alone — so a body
# the structural layer can actually see is what exercises that detector.
_SOURCERY_SHAPED_REFUSAL = (
    '> [!WARNING] Sourcery has reached your review limit for this pull request. '
    'Reviews will resume once the limit resets.'
)

# Sourcery's SECOND observed refusal mode (#1034 / #1037): the account-level weekly
# diff-character quota, distinct from the per-PR size ceiling of #1014. Two observed
# phrasings is the point — "the generic structural recogniser covers Sourcery" is
# REFUTED, so each observed mode must be filed as registry data.
_SOURCERY_WEEKLY_QUOTA_REFUSAL = (
    'Sourcery has not reviewed this pull request because '
    'you have reached your weekly rate limit of 500000 diff characters.'
)

# An unknown / renamed bot's refusal — no registry record exists for its author,
# so only the structural last-resort layer can recognize it.
_UNKNOWN_BOT_REFUSAL = (
    '> [!WARNING] > ## Usage limit reached > '
    'This reviewer has reached its monthly usage limit. '
    'Reviews will resume after the limit resets.'
)

# A GENUINE review that merely mentions a limit in prose: no notice shape, no
# registry marker, and review-voiced ("exceeds") rather than notice-voiced.
_GENUINE_REVIEW_MENTIONING_A_LIMIT = (
    'This retry loop exceeds the review limit we agreed on for batch size; '
    'consider lowering it to 50 before this merges.'
)


class TestRefusalNoticeProducerFilter:
    """Every reviewer bot's refusal is RECOGNIZED as a refusal — by data or by shape.

    The recognizer under test is ``_is_refusal_notice``, never ``_is_obvious_noise``.
    That separation is the contract: ``_is_obvious_noise`` must NOT recognize a
    refusal, because a refusal it swallows is a declined review the quorum layer
    never sees.
    """

    def test_sourcery_1014_refusal_recognized_via_registry_data_layer(self):
        """#1014 regression: the Sourcery refusal is seen ONLY because it is filed as data.

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
        """CodeRabbit's current ``Review limit reached`` notice is a refusal."""
        from _github_pr import _is_refusal_notice

        assert _is_refusal_notice(_CODERABBIT_REVIEW_LIMIT_REFUSAL, 'coderabbit')

    def test_sourcery_has_two_distinct_registered_refusal_modes(self):
        """Both observed Sourcery refusal phrasings are filed as registry data.

        #1034 / #1037 refuted the assumption that one recogniser covers this bot:
        the weekly diff-character QUOTA is a different mode from the per-PR SIZE
        ceiling of #1014, and neither marker matches the other's text. Each observed
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
        'bot_kind', [None, 'coderabbit', 'sourcery', 'pr-agent'], ids=['human', 'cr', 'sr', 'pra']
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
            _SOURCERY_SHAPED_REFUSAL,
            _UNKNOWN_BOT_REFUSAL,
        ):
            assert not _is_obvious_noise(body, bot_kind), (bot_kind, body[:40])

    def test_genuine_review_mentioning_a_limit_is_neither_refusal_nor_noise(self):
        """A substantive review that merely mentions a limit survives both predicates.

        Precision guard for both layers: no registry marker matches, and the
        structural recognizer sees a review-voiced "exceeds" with no notice shape,
        so the comment survives the pre-filter and becomes a finding.
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

    def test_detect_rate_limited_bots_answers_per_registered_bot(self):
        """The wait-return discriminator answers per REGISTERED bot, not per one bot.

        The retired discriminator selected CodeRabbit-authored comments only, so a
        refusing Sourcery scored negative whenever CodeRabbit's own newest comment
        was a genuine review — the two bots' states were collapsed into one answer.
        The registry-driven detector reports each bot independently: CodeRabbit is
        absent because its newest comment is real feedback, while Sourcery appears
        with the class its own registry record declares.
        """
        from _github_pr import _detect_rate_limited_bots

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

        assert _detect_rate_limited_bots(comments) == [
            {'bot_kind': 'sourcery', 'rate_limit_class': 'hard_quota', 'eta': ''}
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


# =============================================================================
# Fail-loud unconfigured provider (both verbs)
# =============================================================================


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


# =============================================================================
# post_responses — hash_id-keyed respond loop
# =============================================================================


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

    def _stage_one_finding(
        self, plan_id, thread_id, body='A substantive concern about null handling.', kind='inline'
    ):
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

        resolve_finding('gh-respond-basic', hash_id, 'fixed', detail='Fixed the null guard in commit abc.')

        calls = []

        def _fake_graphql(mutation, variables):
            calls.append((mutation, variables))
            return 0, {}, ''

        with patch('github_pr._github.run_graphql', side_effect=_fake_graphql):
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
        assert reply_vars['body'] == 'Fixed the null guard in commit abc.'
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

        resolve_finding(
            'gh-respond-inline-nothread', hash_id, 'suppressed', detail='Suppressed with rationale.'
        )

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

        resolve_finding('gh-respond-inline-replyfail', hash_id, 'fixed', detail='Fixed in commit abc.')

        with (
            patch('github_pr._github.run_graphql', return_value=(1, {}, 'thread not found')),
            patch('github_pr._github.post_pr_comment') as mock_post,
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


# =============================================================================
# CLI plumbing — main() and --project-dir
# =============================================================================


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
                    return_value=(True, '/tmp/wt-pr-resolved'),
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
