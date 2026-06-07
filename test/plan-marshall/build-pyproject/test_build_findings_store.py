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
from contextlib import redirect_stdout
from unittest.mock import patch


class TestClassifyIssueFindingType:
    """Issue.category → finding type routing."""

    def setup_method(self):
        from _build_parse import Issue  # type: ignore[import-not-found]
        from _build_shared import _classify_issue_finding_type  # type: ignore[import-not-found]

        self.Issue = Issue
        self.classify = _classify_issue_finding_type

    def test_test_failure_category(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='error', category='test_failure')
        assert self.classify(issue) == 'test-failure'

    def test_lint_error_category(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='warning', category='lint_error')
        assert self.classify(issue) == 'lint-issue'

    def test_style_category(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='warning', category='style_violation')
        assert self.classify(issue) == 'lint-issue'

    def test_compilation_falls_through_to_build_error(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='error', category='compilation')
        assert self.classify(issue) == 'build-error'

    def test_type_error_falls_through_to_build_error(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='error', category='type_error')
        assert self.classify(issue) == 'build-error'

    def test_no_category_falls_through_to_build_error(self):
        issue = self.Issue(file='t.py', line=1, message='m', severity='error', category=None)
        assert self.classify(issue) == 'build-error'


class TestStoreBuildFindings:
    """Every parsed Issue must be persisted as a finding."""

    def test_store_three_issue_kinds(self, plan_context):
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

        count_seen, count_stored, failures = _store_build_findings(
            plan_id=plan_context.plan_id,
            tool_name='python',
            issues=issues,
            command_str='verify',
        )

        assert count_seen == 3
        assert count_stored == 3
        assert failures == []

        be = query_findings(plan_context.plan_id, finding_type='build-error')
        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        li = query_findings(plan_context.plan_id, finding_type='lint-issue')

        assert be['filtered_count'] == 1
        assert tf['filtered_count'] == 1
        assert li['filtered_count'] == 1

        be_record = be['findings'][0]
        assert be_record['module'] == 'python'
        assert be_record['rule'] == 'compilation'
        assert be_record['severity'] == 'error'
        assert be_record['file_path'] == 'src/Main.py'
        assert be_record['line'] == 10

        li_record = li['findings'][0]
        assert li_record['severity'] == 'warning'

    def test_store_zero_issues(self, plan_context):
        from _build_shared import _store_build_findings  # type: ignore[import-not-found]

        count_seen, count_stored, failures = _store_build_findings(
            plan_id=plan_context.plan_id,
            tool_name='maven',
            issues=[],
            command_str='verify',
        )
        assert (count_seen, count_stored, failures) == (0, 0, [])


class TestRecordProducerMismatch:
    """Producer mismatches must be recorded as a Q-Gate finding."""

    def test_record_producer_mismatch_writes_qgate(self, plan_context):
        from _build_shared import _record_producer_mismatch  # type: ignore[import-not-found]
        from _findings_core import query_qgate_findings  # type: ignore[import-not-found]

        _record_producer_mismatch(
            plan_id=plan_context.plan_id,
            tool_name='gradle',
            command_str='build',
            count_seen=5,
            count_stored=3,
            store_failures=['x', 'y'],
        )
        q = query_qgate_findings(plan_context.plan_id, phase='5-execute')
        assert q['filtered_count'] == 1
        qf = q['findings'][0]
        assert qf['title'].startswith('(producer-mismatch)')
        assert qf['source'] == 'qgate'
        assert qf['type'] == 'build-error'


class TestCmdRunCommonPlanIdGuard:
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

    def test_cmd_run_common_without_plan_id_writes_no_findings(self, plan_context):
        from _build_shared import cmd_run_common  # type: ignore[import-not-found]

        log_file = plan_context.fixture_dir / 'fake.log'
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
        assert rc == 0
        mock_store.assert_not_called()
        mock_qgate.assert_not_called()

    def test_cmd_run_common_with_plan_id_invokes_store(self, plan_context):
        from _build_shared import cmd_run_common  # type: ignore[import-not-found]

        log_file = plan_context.fixture_dir / 'fake.log'
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
                    plan_id=plan_context.plan_id,
                )

        # cmd_run_common returns 0 even on build failure — see the
        # silent-skip variant above for rationale.
        assert rc == 0
        mock_store.assert_called_once()
        # No mismatch (1 seen / 1 stored) → qgate not called.
        mock_qgate.assert_not_called()


class TestReconcilePendingBuildFindings:
    """A green build run terminalizes every pending build finding from a
    prior failing run."""

    def _seed_pending_build_findings(self, plan_id):
        from _findings_core import add_finding  # type: ignore[import-not-found]

        add_finding(
            plan_id=plan_id,
            finding_type='build-error',
            title='Build error: compile failed',
            detail='boom',
        )
        add_finding(
            plan_id=plan_id,
            finding_type='test-failure',
            title='Test failure: assertion',
            detail='AssertionError',
        )
        add_finding(
            plan_id=plan_id,
            finding_type='lint-issue',
            title='Lint issue: line too long',
            detail='E501',
        )

    def test_reconcile_resolves_all_pending_build_findings(self, plan_context):
        from _build_shared import _reconcile_pending_build_findings  # type: ignore[import-not-found]
        from _findings_core import query_findings  # type: ignore[import-not-found]

        self._seed_pending_build_findings(plan_context.plan_id)

        resolved = _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='verify plan-marshall',
        )

        assert resolved == 3
        for ftype in ('build-error', 'test-failure', 'lint-issue'):
            q = query_findings(plan_context.plan_id, finding_type=ftype)
            for record in q['findings']:
                assert record['resolution'] == 'fixed'
                assert 'auto-resolved by green build' in (record.get('resolution_detail') or '')

    def test_reconcile_with_no_pending_findings_returns_zero(self, plan_context):
        from _build_shared import _reconcile_pending_build_findings  # type: ignore[import-not-found]

        resolved = _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='verify',
        )
        assert resolved == 0


class TestCmdRunCommonGreenBuildReconciliation:
    """cmd_run_common's green-build path bulk-resolves pending build findings
    when plan_id is provided, and skips reconciliation otherwise."""

    def _make_success_result(self, log_file_path):
        return {
            'status': 'success',
            'exit_code': 0,
            'duration_seconds': 0.1,
            'log_file': str(log_file_path),
            'command': 'verify',
        }

    def _fake_parser(self, _log_file):
        return [], None, 'success'

    def test_green_build_with_plan_id_invokes_reconciliation(self, plan_context):
        from _build_shared import cmd_run_common  # type: ignore[import-not-found]

        log_file = plan_context.fixture_dir / 'green.log'
        log_file.write_text('BUILD SUCCESS\n')

        with patch('_build_shared._reconcile_pending_build_findings') as mock_reconcile:
            mock_reconcile.return_value = 2
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cmd_run_common(
                    result=self._make_success_result(log_file),
                    parser_fn=self._fake_parser,
                    tool_name='python',
                    plan_id=plan_context.plan_id,
                )

        assert rc == 0
        mock_reconcile.assert_called_once_with(
            plan_id=plan_context.plan_id,
            command_str='verify',
        )

    def test_green_build_without_plan_id_skips_reconciliation(self, plan_context):
        from _build_shared import cmd_run_common  # type: ignore[import-not-found]

        log_file = plan_context.fixture_dir / 'green.log'
        log_file.write_text('BUILD SUCCESS\n')

        with patch('_build_shared._reconcile_pending_build_findings') as mock_reconcile:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cmd_run_common(
                    result=self._make_success_result(log_file),
                    parser_fn=self._fake_parser,
                    tool_name='python',
                    plan_id=None,
                )

        assert rc == 0
        mock_reconcile.assert_not_called()

    def test_green_build_with_plan_id_resolves_seeded_findings_end_to_end(self, plan_context):
        from _build_shared import cmd_run_common  # type: ignore[import-not-found]
        from _findings_core import add_finding, query_findings  # type: ignore[import-not-found]

        add_finding(
            plan_id=plan_context.plan_id,
            finding_type='build-error',
            title='Build error: stale failure',
            detail='from a prior red run',
        )

        log_file = plan_context.fixture_dir / 'green.log'
        log_file.write_text('BUILD SUCCESS\n')

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_run_common(
                result=self._make_success_result(log_file),
                parser_fn=self._fake_parser,
                tool_name='python',
                plan_id=plan_context.plan_id,
            )

        assert rc == 0
        q = query_findings(plan_context.plan_id, finding_type='build-error')
        assert q['filtered_count'] == 1
        assert q['findings'][0]['resolution'] == 'fixed'
