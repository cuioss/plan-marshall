"""Tests for workflow-integration-gitlab gitlab_pr.py — producer-side surface.

Mirrors test_github_pr.py for the GitLab provider. The script's LLM-callable
triage / triage-batch flow has been retired. The remaining callable surface is:

- ``fetch-comments`` — raw glab fetch (no filtering, no storage)
- ``comments-stage`` — fetch + pre-filter + persist one ``pr-comment`` finding
  per surviving comment via ``manage-findings add``
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from conftest import PlanContext, get_script_path, run_script

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
cmd_comments_stage = gitlab_pr.cmd_comments_stage


# =============================================================================
# Pre-filter
# =============================================================================


class TestIsObviousNoise(unittest.TestCase):
    def test_empty_body_is_noise(self):
        self.assertTrue(_is_obvious_noise(''))

    def test_lgtm_is_noise(self):
        self.assertTrue(_is_obvious_noise('lgtm'))

    def test_substantive_is_kept(self):
        self.assertFalse(_is_obvious_noise('Please add validation for empty input'))


# =============================================================================
# Provider integration
# =============================================================================


class TestFetchCommentsWrapper(unittest.TestCase):
    def test_fetch_comments_success(self):
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
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['comments'][0]['kind'], 'inline')

    def test_fetch_comments_provider_error(self):
        with patch('gitlab_pr._gitlab.fetch_pr_comments_data') as mock_fetch:
            mock_fetch.return_value = {'status': 'error', 'error': 'auth'}
            self.assertEqual(fetch_comments(123)['status'], 'error')


# =============================================================================
# comments-stage
# =============================================================================


class TestCommentsStage(unittest.TestCase):
    def _make_args(self, pr_number, plan_id):
        class _Args:
            pass

        a = _Args()
        a.pr_number = pr_number
        a.plan_id = plan_id
        return a

    def test_stage_persists_substantive_comments_only(self):
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
        with PlanContext(plan_id='gl-pr-stage-1') as ctx:
            with patch('gitlab_pr._gitlab.fetch_pr_comments_data') as mock_fetch:
                mock_fetch.return_value = {
                    'status': 'success',
                    'provider': 'gitlab',
                    'comments': comments,
                    'total': len(comments),
                    'unresolved': len(comments),
                }
                result = cmd_comments_stage(self._make_args(123, ctx.plan_id))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['count_fetched'], 2)
            self.assertEqual(result['count_skipped_noise'], 1)
            self.assertEqual(result['count_stored'], 1)

            from _findings_core import query_findings  # type: ignore[import-not-found]

            q = query_findings(ctx.plan_id, finding_type='pr-comment')
            self.assertEqual(q['filtered_count'], 1)
            stored = q['findings'][0]
            self.assertIn('thread_id: mr-1', stored['detail'])
            self.assertIn('Please fix the off-by-one error', stored['detail'])


# =============================================================================
# CLI plumbing
# =============================================================================


class TestPRMain(unittest.TestCase):
    def test_help_lists_only_supported_subcommands(self):
        result = run_script(SCRIPT_PATH, '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('fetch-comments', result.stdout)
        self.assertIn('comments-stage', result.stdout)
        self.assertNotIn('triage-batch', result.stdout)

    def test_retired_triage_subcommand_rejected(self):
        result = run_script(SCRIPT_PATH, 'triage', '--comment', '{}')
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
