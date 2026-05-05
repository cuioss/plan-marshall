"""Tests for the producer-side findings-store helpers in _build_shared.py.

When ``build-*:run`` is invoked with ``--plan-id <P>``, every parsed
build-error / test-failure / lint-issue is auto-stored as a finding via
``manage-findings add``. When ``--plan-id`` is omitted the historical
silent behaviour is preserved: no findings are written and no Q-Gate
finding is produced. This test exercises the underlying helpers
(``_classify_issue_finding_type``, ``_store_build_findings``,
``_record_producer_mismatch``) directly so the routing contract is locked
down independently of any specific build tool, and exercises
``cmd_run_common`` to pin the ``plan_id=None`` silent-skip contract.
"""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from conftest import PlanContext


class TestClassifyIssueFindingType(unittest.TestCase):
    """Issue.category → finding type routing."""

    def setUp(self):
        from _build_parse import Issue  # type: ignore[import-not-found]
        from _build_shared import _classify_issue_finding_type  # type: ignore[import-not-found]

        self.Issue = Issue
        self.classify = _classify_issue_finding_type

    def test_test_failure_category(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='error', category='test_failure')
        self.assertEqual(self.classify(issue), 'test-failure')

    def test_lint_error_category(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='warning', category='lint_error')
        self.assertEqual(self.classify(issue), 'lint-issue')

    def test_style_category(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='warning', category='style_violation')
        self.assertEqual(self.classify(issue), 'lint-issue')

    def test_compilation_falls_through_to_build_error(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='error', category='compilation')
        self.assertEqual(self.classify(issue), 'build-error')

    def test_type_error_falls_through_to_build_error(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='error', category='type_error')
        self.assertEqual(self.classify(issue), 'build-error')

    def test_no_category_falls_through_to_build_error(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='error', category=None)
        self.assertEqual(self.classify(issue), 'build-error')


class TestStoreBuildFindings(unittest.TestCase):
    """Every parsed Issue must be persisted as a finding."""

    def test_store_three_issue_kinds(self):
        from _build_parse import Issue  # type: ignore[import-not-found]
        from _build_shared import _store_build_findings  # type: ignore[import-not-found]
        from _findings_core import query_findings  # type: ignore[import-not-found]

        issues = [
            Issue(
                file='src/Main.py',
                line=10,
                message='Compile failed: missing import',
                severity='error',
                category='compilation',
            ),
            Issue(
                file='test/test_x.py',
                line=20,
                message='AssertionError: expected 1 got 2',
                severity='error',
                category='test_failure',
            ),
            Issue(
                file='src/Main.py',
                line=30,
                message='Style: line too long',
                severity='warning',
                category='lint_error',
            ),
        ]

        with PlanContext(plan_id='build-store-1') as ctx:
            count_seen, count_stored, failures = _store_build_findings(
                plan_id=ctx.plan_id,
                tool_name='python',
                issues=issues,
                command_str='verify',
            )

            self.assertEqual(count_seen, 3)
            self.assertEqual(count_stored, 3)
            self.assertEqual(failures, [])

            be = query_findings(ctx.plan_id, finding_type='build-error')
            tf = query_findings(ctx.plan_id, finding_type='test-failure')
            li = query_findings(ctx.plan_id, finding_type='lint-issue')

            self.assertEqual(be['filtered_count'], 1)
            self.assertEqual(tf['filtered_count'], 1)
            self.assertEqual(li['filtered_count'], 1)

            be_record = be['findings'][0]
            self.assertEqual(be_record['module'], 'python')
            self.assertEqual(be_record['rule'], 'compilation')
            self.assertEqual(be_record['severity'], 'error')
            self.assertEqual(be_record['file_path'], 'src/Main.py')
            self.assertEqual(be_record['line'], 10)

            li_record = li['findings'][0]
            self.assertEqual(li_record['severity'], 'warning')

    def test_store_zero_issues(self):
        from _build_shared import _store_build_findings  # type: ignore[import-not-found]

        with PlanContext(plan_id='build-store-empty') as ctx:
            count_seen, count_stored, failures = _store_build_findings(
                plan_id=ctx.plan_id,
                tool_name='maven',
                issues=[],
                command_str='verify',
            )
            self.assertEqual((count_seen, count_stored, failures), (0, 0, []))


class TestRecordProducerMismatch(unittest.TestCase):
    """Producer mismatches must be recorded as a Q-Gate finding."""

    def test_record_producer_mismatch_writes_qgate(self):
        from _build_shared import _record_producer_mismatch  # type: ignore[import-not-found]
        from _findings_core import query_qgate_findings  # type: ignore[import-not-found]

        with PlanContext(plan_id='build-store-mismatch') as ctx:
            _record_producer_mismatch(
                plan_id=ctx.plan_id,
                tool_name='gradle',
                command_str='build',
                count_seen=5,
                count_stored=3,
                store_failures=['x', 'y'],
            )
            q = query_qgate_findings(ctx.plan_id, phase='5-execute')
            self.assertEqual(q['filtered_count'], 1)
            qf = q['findings'][0]
            self.assertTrue(qf['title'].startswith('(producer-mismatch)'))
            self.assertEqual(qf['source'], 'qgate')
            self.assertEqual(qf['type'], 'build-error')


class TestCmdRunCommonPlanIdGuard(unittest.TestCase):
    """When plan_id is None, cmd_run_common MUST NOT call the finding-store
    helpers — preserving the historical silent behaviour for non-plan
    invocations."""

    def _make_failure_result(self, log_file_path):
        return {
            'status': 'error',
            'exit_code': 1,
            'duration_seconds': 0.1,
            'log_file': str(log_file_path),
            'command': 'verify',
        }

    def _fake_parser(self, _log_file):
        from _build_parse import Issue  # type: ignore[import-not-found]

        issue = Issue(
            file='src/Main.py',
            line=10,
            message='boom',
            severity='error',
            category='compilation',
        )
        return [issue], None, 'failed'

    def test_cmd_run_common_without_plan_id_writes_no_findings(self):
        from _build_shared import cmd_run_common  # type: ignore[import-not-found]

        with PlanContext(plan_id='build-noplan') as ctx:
            log_file = ctx.fixture_dir / 'fake.log'
            log_file.write_text('failed\n')

            with patch('_build_shared._store_build_findings') as mock_store, \
                    patch('_build_shared._record_producer_mismatch') as mock_qgate:
                # Suppress noisy stdout/stderr
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_run_common(
                        result=self._make_failure_result(log_file),
                        parser_fn=self._fake_parser,
                        tool_name='python',
                        plan_id=None,
                    )

            # cmd_run_common returns 0 even on build failure — status is
            # modeled in the printed output, not in the exit code. The
            # behaviour under test is the silent skip, not the rc value.
            self.assertEqual(rc, 0)
            mock_store.assert_not_called()
            mock_qgate.assert_not_called()

    def test_cmd_run_common_with_plan_id_invokes_store(self):
        from _build_shared import cmd_run_common  # type: ignore[import-not-found]

        with PlanContext(plan_id='build-withplan') as ctx:
            log_file = ctx.fixture_dir / 'fake.log'
            log_file.write_text('failed\n')

            with patch('_build_shared._store_build_findings') as mock_store, \
                    patch('_build_shared._record_producer_mismatch') as mock_qgate:
                mock_store.return_value = (1, 1, [])
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_run_common(
                        result=self._make_failure_result(log_file),
                        parser_fn=self._fake_parser,
                        tool_name='python',
                        plan_id=ctx.plan_id,
                    )

            # cmd_run_common returns 0 even on build failure — see the
            # silent-skip variant above for rationale.
            self.assertEqual(rc, 0)
            mock_store.assert_called_once()
            # No mismatch (1 seen / 1 stored) → qgate not called.
            mock_qgate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
