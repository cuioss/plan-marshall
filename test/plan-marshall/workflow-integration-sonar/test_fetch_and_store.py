"""Tests for workflow-integration-sonar sonar.py — producer-side surface.

The triage / triage-batch subcommands have been retired. The remaining
callable surface is ``fetch-and-store`` which fetches gate-blocking issues,
applies the suppressable-rules pre-filter, and persists one ``sonar-issue``
finding per surviving issue via ``manage-findings add``.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from conftest import PlanContext, get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-sonar', 'sonar.py')

_path = Path(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('sonar_mod', _path)
assert _spec is not None and _spec.loader is not None
sonar_mod = importlib.util.module_from_spec(_spec)
sys.modules['sonar_mod'] = sonar_mod
_spec.loader.exec_module(sonar_mod)

_is_suppressable = sonar_mod._is_suppressable
_map_severity = sonar_mod._map_severity
cmd_fetch_and_store = sonar_mod.cmd_fetch_and_store


# =============================================================================
# Pre-filter helpers
# =============================================================================


class TestIsSuppressable(unittest.TestCase):
    """The pre-filter drops issues already documented as suppressable."""

    def test_always_fix_type_never_suppressed(self):
        # VULNERABILITY is in always_fix_types — it must NEVER be suppressed
        # even if the rule appears in suppressable_rules.
        self.assertFalse(_is_suppressable('java:S2076', 'src/X.java', 'VULNERABILITY'))

    def test_unknown_rule_passes_through(self):
        self.assertFalse(_is_suppressable('java:S99999', 'src/X.java', 'CODE_SMELL'))


class TestMapSeverity(unittest.TestCase):
    def test_blocker_maps_to_error(self):
        self.assertEqual(_map_severity('BLOCKER'), 'error')

    def test_critical_maps_to_error(self):
        self.assertEqual(_map_severity('CRITICAL'), 'error')

    def test_major_maps_to_error(self):
        self.assertEqual(_map_severity('MAJOR'), 'error')

    def test_minor_maps_to_warning(self):
        self.assertEqual(_map_severity('MINOR'), 'warning')

    def test_info_maps_to_info(self):
        self.assertEqual(_map_severity('INFO'), 'info')

    def test_unknown_maps_to_none(self):
        self.assertIsNone(_map_severity('OTHER'))


# =============================================================================
# fetch-and-store flow
# =============================================================================


class TestFetchAndStore(unittest.TestCase):
    """fetch-and-store writes one sonar-issue finding per surviving issue."""

    def _make_args(self, plan_id, project='com.example:proj', pr=None, severities=None, types=None):
        class _Args:
            pass

        a = _Args()
        a.plan_id = plan_id
        a.project = project
        a.pr = pr
        a.severities = severities
        a.types = types
        return a

    def test_fetch_and_store_persists_findings(self):
        issues_payload = [
            {
                'key': 'ISSUE-1',
                'type': 'BUG',
                'severity': 'MAJOR',
                'file': 'src/Main.java',
                'line': 42,
                'rule': 'java:S99999',
                'message': 'Possible null dereference',
                'component': 'com.example:proj:src/Main.java',
            },
        ]
        with PlanContext(plan_id='sonar-stage-1') as ctx:
            with patch('sonar_mod._fetch_issues') as mock_fetch:
                mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
                result = cmd_fetch_and_store(self._make_args(ctx.plan_id))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['count_fetched'], 1)
            self.assertEqual(result['count_skipped_suppressable'], 0)
            self.assertEqual(result['count_stored'], 1)

            from _findings_core import query_findings  # type: ignore[import-not-found]

            q = query_findings(ctx.plan_id, finding_type='sonar-issue')
            self.assertEqual(q['filtered_count'], 1)
            stored = q['findings'][0]
            self.assertEqual(stored['type'], 'sonar-issue')
            self.assertEqual(stored['rule'], 'java:S99999')
            self.assertEqual(stored['severity'], 'error')  # MAJOR → error
            self.assertEqual(stored['module'], 'com.example:proj')
            self.assertIn('Possible null dereference', stored['detail'])

    def test_fetch_and_store_skips_suppressable(self):
        # First find a rule from the live SUPPRESSABLE_RULES dict to ensure
        # the test exercises real configuration. If the dict is empty the
        # test trivially passes; that is acceptable because the assertion
        # is on observable counter behaviour, not config presence.
        from sonar_mod import SUPPRESSABLE_RULES  # type: ignore[import-not-found]

        if not SUPPRESSABLE_RULES:
            self.skipTest('No suppressable rules configured in sonar-rules.json')
        rule = next(iter(SUPPRESSABLE_RULES.keys()))

        issues_payload = [
            {
                'key': 'ISSUE-1',
                'type': 'CODE_SMELL',
                'severity': 'MINOR',
                'file': 'src/Main.java',
                'line': 1,
                'rule': rule,
                'message': 'm',
                'component': 'com.example:proj:src/Main.java',
            },
        ]
        with PlanContext(plan_id='sonar-stage-skip') as ctx:
            with patch('sonar_mod._fetch_issues') as mock_fetch:
                mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
                result = cmd_fetch_and_store(self._make_args(ctx.plan_id))

            self.assertEqual(result['count_fetched'], 1)
            self.assertEqual(result['count_skipped_suppressable'], 1)
            self.assertEqual(result['count_stored'], 0)

    def test_fetch_and_store_propagates_provider_error(self):
        with PlanContext(plan_id='sonar-stage-err') as ctx:
            with patch('sonar_mod._fetch_issues') as mock_fetch:
                mock_fetch.return_value = {'status': 'error', 'message': 'HTTP 401'}
                result = cmd_fetch_and_store(self._make_args(ctx.plan_id))
            self.assertEqual(result['status'], 'error')

    def test_fetch_and_store_count_mismatch_produces_qgate_finding(self):
        """When count_stored != expected_stored, a (producer-mismatch) Q-Gate
        finding must be recorded with type=sonar-issue and source=qgate."""
        issues_payload = [
            {
                'key': 'ISSUE-1',
                'type': 'BUG',
                'severity': 'MAJOR',
                'file': 'src/Main.java',
                'line': 42,
                'rule': 'java:S99999',
                'message': 'Possible null dereference',
                'component': 'com.example:proj:src/Main.java',
            },
            {
                'key': 'ISSUE-2',
                'type': 'BUG',
                'severity': 'CRITICAL',
                'file': 'src/Other.java',
                'line': 7,
                'rule': 'java:S88888',
                'message': 'Race condition',
                'component': 'com.example:proj:src/Other.java',
            },
        ]
        with PlanContext(plan_id='sonar-stage-mismatch') as ctx:
            with patch('sonar_mod._fetch_issues') as mock_fetch:
                mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
                with patch('_findings_core.add_finding') as mock_add:
                    def _side_effect(**kwargs):
                        if mock_add.call_count == 1:
                            return {'status': 'error', 'message': 'simulated store failure'}
                        return {'status': 'success', 'hash_id': 'h-' + str(mock_add.call_count)}

                    mock_add.side_effect = _side_effect
                    result = cmd_fetch_and_store(self._make_args(ctx.plan_id))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['count_fetched'], 2)
            self.assertEqual(result['count_skipped_suppressable'], 0)
            self.assertEqual(result['count_stored'], 1)

            from _findings_core import query_qgate_findings  # type: ignore[import-not-found]

            q = query_qgate_findings(ctx.plan_id, phase='5-execute')
            self.assertEqual(q['filtered_count'], 1)
            qf = q['findings'][0]
            self.assertTrue(qf['title'].startswith('(producer-mismatch)'))
            self.assertEqual(qf['source'], 'qgate')
            self.assertEqual(qf['type'], 'sonar-issue')


# =============================================================================
# CLI plumbing
# =============================================================================


class TestSonarMain(unittest.TestCase):
    def test_help_lists_only_supported_subcommand(self):
        result = run_script(SCRIPT_PATH, '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('fetch-and-store', result.stdout)
        self.assertNotIn('triage-batch', result.stdout)

    def test_retired_triage_subcommand_rejected(self):
        result = run_script(SCRIPT_PATH, 'triage', '--issue', '{}')
        self.assertNotEqual(result.returncode, 0)

    def test_retired_triage_batch_subcommand_rejected(self):
        result = run_script(SCRIPT_PATH, 'triage-batch', '--issues', '[]')
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
