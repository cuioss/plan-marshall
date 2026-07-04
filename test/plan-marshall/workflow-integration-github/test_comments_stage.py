# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for workflow-integration-github github_pr.py — producer-side surface.

The script's LLM-callable triage / triage-batch flow has been retired. The
remaining callable surface is:

- ``fetch-comments`` — raw GraphQL fetch (no filtering, no storage)
- ``comments-stage`` — fetch + pre-filter + persist one ``pr-comment`` finding
  per surviving comment via ``manage-findings add``

These tests cover the producer-side classification helper, the comments-stage
flow with mocked provider data, the ``--project-dir`` plumbing, and the CLI
surface contract (``triage`` and ``triage-batch`` subcommands MUST be gone).
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
cmd_comments_stage = github_pr.cmd_comments_stage


@pytest.fixture(autouse=True)
def _stub_pr_head_sha():
    """Stub the PR HEAD-SHA fetch so comments-stage tests never hit ``gh``.

    ``cmd_comments_stage`` resolves the PR HEAD SHA (for ``reviewed_commit_sha``)
    via ``github_ops.fetch_pr_head_sha`` once per batch. Without this stub the
    helper would spawn a real ``gh pr view`` subprocess in every comments-stage
    test. Tests that assert on a specific SHA re-patch the same target inside a
    ``with`` block, which takes precedence over this default for its duration.
    """
    with patch('github_pr._github.fetch_pr_head_sha', return_value='stub-head-sha'):
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
        pass

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
            result = cmd_comments_stage(_stage_make_args(123, 'gh-pr-stage-1'))

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
        # The detail must carry kind, author, thread_id, comment_id, full body
        assert 'kind: inline' in stored['detail']
        assert 'thread_id: PRRT_a' in stored['detail']
        assert 'Please fix the null pointer here' in stored['detail']

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
            result = cmd_comments_stage(_stage_make_args(127, 'gh-pr-stage-resolved'))

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
            result = cmd_comments_stage(_stage_make_args(124, 'gh-pr-stage-empty'))

        assert result['count_fetched'] == 0
        assert result['count_stored'] == 0
        assert result['producer_mismatch_hash_id'] is None

    def test_stage_provider_error_propagates(self, plan_context):
        plan_context.plan_dir_for('gh-pr-stage-err')
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {'status': 'error', 'error': 'auth'}
            result = cmd_comments_stage(_stage_make_args(125, 'gh-pr-stage-err'))

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
                result = cmd_comments_stage(_stage_make_args(126, 'gh-pr-stage-mismatch'))

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
            result_1 = cmd_comments_stage(_stage_make_args(128, 'gh-pr-stage-dedup'))
            # Iteration 2 — HEAD advanced; the identical comment is fetched
            # again but must be deduped, not re-stored.
            result_2 = cmd_comments_stage(_stage_make_args(128, 'gh-pr-stage-dedup'))

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
            result_1 = cmd_comments_stage(_stage_make_args(129, 'gh-pr-stage-newid'))

            # Iteration 2 — both the old comment (deduped) and a brand-new
            # comment (RB2) are fetched. RB2 must be stored.
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': [first, second],
                'total': 2,
                'unresolved': 2,
            }
            result_2 = cmd_comments_stage(_stage_make_args(129, 'gh-pr-stage-newid'))

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
            result = cmd_comments_stage(_stage_make_args(130, 'gh-pr-author-field'))

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
                'author': 'gemini-code-assist',
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
            result = cmd_comments_stage(_stage_make_args(131, plan_id))

        assert result['status'] == 'success'
        assert result['count_stored'] == 1

        from _findings_core import query_findings

        q = query_findings(plan_id, finding_type='pr-comment')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        # First-class queryable field — equals the provider structure discriminator.
        assert stored['kind'] == kind
        # author is likewise first-class for the same finding.
        assert stored['author'] == 'gemini-code-assist'

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
            result = cmd_comments_stage(_stage_make_args(132, 'gh-pr-kind-query'))

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
            result = cmd_comments_stage(_stage_make_args(133, 'gh-pr-author-query'))

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
            result = cmd_comments_stage(_stage_make_args(134, 'gh-pr-author-unknown'))

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
    gemini-code-assist -> gemini; a human author leaves ``bot_kind`` unset).
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
            result = cmd_comments_stage(_stage_make_args(140, 'gh-pr-reviewed-sha'))

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
            pytest.param('gemini-code-assist', 'gemini', id='gemini'),
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
            result = cmd_comments_stage(_stage_make_args(141, plan_id))

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
            result = cmd_comments_stage(_stage_make_args(142, 'gh-pr-botkind-human'))

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
        assert 'comments-stage' in result.stdout
        # Retired surfaces MUST be absent from the CLI
        assert 'triage-batch' not in result.stdout
        assert '--comments ' not in result.stdout

    @pytest.mark.parametrize(
        'argv',
        [
            pytest.param(['triage', '--comment', '{}'], id='triage-rejected'),
            pytest.param(['triage-batch', '--comments', '[]'], id='triage-batch-rejected'),
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
        import ci_base
        import resolve_project_dir as _routing

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
                patch.object(_routing, '_query_worktree_path', return_value=(True, '/tmp/wt-pr-resolved')),
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
