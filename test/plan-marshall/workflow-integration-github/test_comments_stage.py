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
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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


# =============================================================================
# Pre-filter (_is_obvious_noise) — drops obvious automated/acknowledgment noise
# =============================================================================


class TestIsObviousNoise(unittest.TestCase):
    """Pre-filter must drop obvious noise but keep substantive content."""

    def test_empty_body_is_noise(self):
        self.assertTrue(_is_obvious_noise(''))

    def test_lgtm_is_noise(self):
        self.assertTrue(_is_obvious_noise('lgtm'))

    def test_lgtm_uppercase_is_noise(self):
        self.assertTrue(_is_obvious_noise('LGTM'))

    def test_substantive_content_is_not_noise(self):
        body = 'This needs to be fixed because of a security issue with input validation.'
        self.assertFalse(_is_obvious_noise(body))


# =============================================================================
# Provider integration (fetch_comments wrapper)
# =============================================================================


class TestFetchCommentsWrapper(unittest.TestCase):
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
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['pr_number'], 123)
            self.assertEqual(result['comments'][0]['kind'], 'inline')

    def test_fetch_comments_provider_error(self):
        with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {'status': 'error', 'error': 'Auth failed'}
            result = fetch_comments(123)
            self.assertEqual(result['status'], 'error')


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
        from _findings_core import query_findings  # type: ignore[import-not-found]

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

        from _findings_core import query_findings  # type: ignore[import-not-found]

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

        from _findings_core import query_qgate_findings  # type: ignore[import-not-found]

        q = query_qgate_findings('gh-pr-stage-mismatch', phase='5-execute')
        assert q['filtered_count'] == 1
        qf = q['findings'][0]
        assert qf['title'].startswith('(producer-mismatch)')
        assert qf['source'] == 'qgate'
        assert qf['type'] == 'pr-comment'


# =============================================================================
# CLI plumbing — main() and --project-dir
# =============================================================================


class TestPRMain(unittest.TestCase):
    """Test github_pr.py main entry point (CLI plumbing)."""

    def test_no_subcommand(self):
        result = run_script(SCRIPT_PATH)
        self.assertNotEqual(result.returncode, 0)

    def test_help_lists_only_supported_subcommands(self):
        result = run_script(SCRIPT_PATH, '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('fetch-comments', result.stdout)
        self.assertIn('comments-stage', result.stdout)
        # Retired surfaces MUST be absent from the CLI
        self.assertNotIn('triage-batch', result.stdout)
        self.assertNotIn('--comments ', result.stdout)

    def test_retired_triage_subcommand_rejected(self):
        result = run_script(SCRIPT_PATH, 'triage', '--comment', '{}')
        self.assertNotEqual(result.returncode, 0)

    def test_retired_triage_batch_subcommand_rejected(self):
        result = run_script(SCRIPT_PATH, 'triage-batch', '--comments', '[]')
        self.assertNotEqual(result.returncode, 0)


class TestPRProjectDirPlumbing(unittest.TestCase):
    """Verify github_pr.main() strips --project-dir and forwards cwd."""

    def test_main_project_dir_sets_default_cwd(self):
        import ci_base  # type: ignore[import-not-found]

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
            self.assertEqual(ci_base.get_default_cwd(), '/tmp/worktree-pr')
            self.assertNotIn('--project-dir', sys.argv)
        finally:
            sys.argv = saved_argv
            ci_base.set_default_cwd(saved_cwd)


class TestPRTwoStateRoutingContract(unittest.TestCase):
    """Two-state ``--plan-id`` / ``--project-dir`` routing for github_pr.main().

    Mirrors the github_ops.main() contract: router-level --plan-id is
    consumed by extract_routing_args and resolved via manage-status to
    install the default cwd; --project-dir keeps working as the legacy
    escape hatch; both together → mutually_exclusive_args TOON error.
    """

    def test_main_plan_id_sets_default_cwd_via_manage_status_resolution(self):
        """Router-level --plan-id auto-routes to the persisted worktree path."""
        import ci_base  # type: ignore[import-not-found]
        import resolve_project_dir as _routing  # type: ignore[import-not-found]

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
            self.assertEqual(ci_base.get_default_cwd(), '/tmp/wt-pr-resolved')
        finally:
            sys.argv = saved_argv
            ci_base.set_default_cwd(saved_cwd)

    def test_main_emits_mutually_exclusive_error_on_both_flags(self):
        """Both router-level routing flags → mutually_exclusive_args + exit 2."""
        import io
        from contextlib import redirect_stdout

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
            with self.assertRaises(SystemExit) as ctx:
                with redirect_stdout(buf):
                    github_pr.main()
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn('mutually_exclusive_args', buf.getvalue())
        finally:
            sys.argv = saved_argv


if __name__ == '__main__':
    unittest.main()
