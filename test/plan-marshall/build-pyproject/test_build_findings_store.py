# SPDX-License-Identifier: FSL-1.1-ALv2
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
        from _build_parse import Issue
        from _build_shared import _classify_issue_finding_type

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
        from _build_parse import Issue
        from _build_shared import _store_build_findings
        from _findings_core import query_findings

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
        from _build_shared import _store_build_findings

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
        from _build_shared import _record_producer_mismatch
        from _findings_core import query_qgate_findings

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
        from _build_parse import Issue

        issue = Issue(
            file='src/Main.py',
            line=10,
            message='boom',
            severity='error',
            category='compilation',
        )
        return [issue], None, 'failed'

    def test_cmd_run_common_without_plan_id_writes_no_findings(self, plan_context):
        from _build_shared import cmd_run_common

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
        from _build_shared import cmd_run_common

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
    """A green build clears only the pending findings it was ENTITLED to clear.

    Entitlement has two independent conditions, and the reproduced defect
    (findings 5a4412 / f9ff9d) violated both: a green ``./pw compile`` cleared a
    ``lint-issue`` record that no compile can evaluate, from a run whose own
    resolution detail recorded ``0 test(s) executed``.

    * A type is cleared only when the run performed an analysis that can REACH it
      (``build-error`` ← compile, ``lint-issue`` ← lint, ``test-failure`` ← test).
    * ``test-failure`` additionally requires a MEASURED non-zero executed count.

    Each negative below is stated beside the positive that must disagree with it,
    so a refusal cannot pass because the reconciler refuses everything.
    """

    def _seed_pending_build_findings(self, plan_id):
        from _findings_core import add_finding

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

    _ALL_ANALYSES = frozenset({'compile', 'lint', 'test'})
    _COMPILE_ONLY = frozenset({'compile'})

    def test_reconcile_resolves_all_pending_build_findings_when_tests_ran(self, plan_context):
        from _build_shared import _reconcile_pending_build_findings
        from _findings_core import query_findings

        self._seed_pending_build_findings(plan_context.plan_id)

        # A `verify`-class run performs every analysis AND measured 7 tests, so
        # all three types are within its entitlement.
        resolved = _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='verify plan-marshall',
            analyses=self._ALL_ANALYSES,
            tests_run=7,
        )

        assert resolved == 3
        for ftype in ('build-error', 'test-failure', 'lint-issue'):
            q = query_findings(plan_context.plan_id, finding_type=ftype)
            for record in q['findings']:
                assert record['resolution'] == 'fixed'
                detail = record.get('resolution_detail') or ''
                assert 'auto-resolved by green build' in detail
                # BOTH population facts are published in the detail.
                assert '7 test(s) executed' in detail
                assert 'analyses examined: compile, lint, test' in detail

    def test_reconcile_retains_test_failure_when_no_tests_ran(self, plan_context):
        from _build_shared import _reconcile_pending_build_findings
        from _findings_core import query_findings

        self._seed_pending_build_findings(plan_context.plan_id)

        # A green quality-gate proves the code compiles and lints but tested
        # nothing, so build-error / lint-issue clear while the stale
        # test-failure finding MUST survive.
        resolved = _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='quality-gate plan-marshall',
            analyses=frozenset({'compile', 'lint'}),
            tests_run=0,
        )

        assert resolved == 2  # build-error + lint-issue only

        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        assert tf['filtered_count'] == 1
        assert tf['findings'][0]['resolution'] == 'pending'  # survived

        for ftype in ('build-error', 'lint-issue'):
            q = query_findings(plan_context.plan_id, finding_type=ftype)
            assert q['findings'][0]['resolution'] == 'fixed'
            # The zero population is published, not left implicit.
            assert '0 test(s) executed' in (q['findings'][0].get('resolution_detail') or '')

    def test_reconcile_retains_lint_issue_on_a_compile_only_run(self, plan_context):
        """The reproduced defect (5a4412 / f9ff9d), at the reconciler.

        A green ``compile`` cannot evaluate the lint dimension at any scope, so
        its green is an un-asked question about ``lint-issue`` — not a clean
        answer. Only ``build-error`` is within its entitlement.
        """
        from _build_shared import _reconcile_pending_build_findings
        from _findings_core import query_findings

        self._seed_pending_build_findings(plan_context.plan_id)

        resolved = _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='compile pm-plugin-development',
            analyses=self._COMPILE_ONLY,
            tests_run=0,
        )

        assert resolved == 1  # build-error only

        li = query_findings(plan_context.plan_id, finding_type='lint-issue')
        assert li['findings'][0]['resolution'] == 'pending'  # survived the compile
        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        assert tf['findings'][0]['resolution'] == 'pending'
        be = query_findings(plan_context.plan_id, finding_type='build-error')
        assert be['findings'][0]['resolution'] == 'fixed'

    def test_reconcile_clears_lint_issue_on_a_lint_bearing_run(self, plan_context):
        """The matched positive for the row above.

        Same seeded ``lint-issue``, same reconciler, a build class that DOES
        evaluate the lint dimension: it clears. Without this half, the refusal
        above is satisfied by a reconciler that clears nothing at all.
        """
        from _build_shared import _reconcile_pending_build_findings
        from _findings_core import query_findings

        self._seed_pending_build_findings(plan_context.plan_id)

        _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='quality-gate pm-plugin-development',
            analyses=frozenset({'compile', 'lint'}),
            tests_run=0,
        )

        li = query_findings(plan_context.plan_id, finding_type='lint-issue')
        assert li['findings'][0]['resolution'] == 'fixed'

    def test_reconcile_clears_nothing_when_the_population_is_unknown(self, plan_context):
        """An undetermined population is no basis for clearing anything."""
        from _build_shared import _reconcile_pending_build_findings
        from _findings_core import query_findings

        self._seed_pending_build_findings(plan_context.plan_id)

        resolved = _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='./pw publish-artifacts',
            analyses=None,
            tests_run=None,
        )

        assert resolved == 0
        for ftype in ('build-error', 'test-failure', 'lint-issue'):
            q = query_findings(plan_context.plan_id, finding_type=ftype)
            assert q['findings'][0]['resolution'] == 'pending'

    def test_reconcile_retains_test_failure_when_the_count_is_unmeasured(self, plan_context):
        """Unknown is not zero, and neither clears — the daemon-routed case."""
        from _build_shared import _reconcile_pending_build_findings
        from _findings_core import query_findings

        self._seed_pending_build_findings(plan_context.plan_id)

        _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='module-tests plan-marshall',
            analyses=frozenset({'test'}),
            tests_run=None,
        )

        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        assert tf['findings'][0]['resolution'] == 'pending'

    def test_reconcile_clears_test_failure_when_the_count_is_measured(self, plan_context):
        """The matched positive: same gate, same seed, a measured count."""
        from _build_shared import _reconcile_pending_build_findings
        from _findings_core import query_findings

        self._seed_pending_build_findings(plan_context.plan_id)

        _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='module-tests plan-marshall',
            analyses=frozenset({'test'}),
            tests_run=2750,
        )

        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        assert tf['findings'][0]['resolution'] == 'fixed'

    def test_reconcile_with_no_pending_findings_returns_zero(self, plan_context):
        from _build_shared import _reconcile_pending_build_findings

        resolved = _reconcile_pending_build_findings(
            plan_id=plan_context.plan_id,
            command_str='verify',
            analyses=self._ALL_ANALYSES,
            tests_run=42,
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
        from _build_shared import cmd_run_common

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
                    command_args='verify',
                )

        assert rc == 0
        # `verify` performs all three analyses; the zero-test parser
        # (_fake_parser returns test_summary=None) leaves the count of a
        # test-bearing gate UNMEASURED, so cmd_run_common passes None — never 0.
        mock_reconcile.assert_called_once_with(
            plan_id=plan_context.plan_id,
            command_str='verify',
            analyses=frozenset({'compile', 'lint', 'test'}),
            tests_run=None,
        )

    def test_green_build_without_plan_id_skips_reconciliation(self, plan_context):
        from _build_shared import cmd_run_common

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
        from _build_shared import cmd_run_common
        from _findings_core import add_finding, query_findings

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
                command_args='compile',
            )

        assert rc == 0
        q = query_findings(plan_context.plan_id, finding_type='build-error')
        assert q['filtered_count'] == 1
        assert q['findings'][0]['resolution'] == 'fixed'

    def test_green_build_without_command_args_clears_nothing_end_to_end(self, plan_context):
        """The fail-closed default, end-to-end against the real store.

        The matched negative for the row above: an identical seeded
        ``build-error`` and an identical green run, differing ONLY in that the
        caller supplied no canonical args. The population is unknown, so the
        finding survives.
        """
        from _build_shared import cmd_run_common
        from _findings_core import add_finding, query_findings

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
        assert q['findings'][0]['resolution'] == 'pending'

    def _fake_parser_with_tests(self, _log_file):
        # A green run that actually executed tests: a non-None UnitTestSummary
        # with total > 0 and zero failures.
        from _build_parse import UnitTestSummary

        return [], UnitTestSummary(passed=5, failed=0, skipped=0, total=5), 'success'

    def test_green_build_zero_tests_retains_seeded_test_failure_end_to_end(self, plan_context):
        # D2 end-to-end: a green build that executed ZERO tests (the parser
        # returns test_summary=None) must NOT clear a seeded test-failure
        # finding. Verifying against a normal build would prove nothing — a
        # normal build runs tests — so this drives the zero-test path explicitly.
        from _build_shared import cmd_run_common
        from _findings_core import add_finding, query_findings

        add_finding(
            plan_id=plan_context.plan_id,
            finding_type='test-failure',
            title='Test failure: stale assertion',
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
                command_args='quality-gate plan-marshall',
            )

        assert rc == 0
        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        assert tf['filtered_count'] == 1
        assert tf['findings'][0]['resolution'] == 'pending'  # survived a zero-test green build
        # The run published the population it counted — a MEASURED zero, because
        # a quality-gate is a non-test gate that genuinely executed none.
        assert 'tests_population: measured' in buf.getvalue()
        assert 'tests_run: 0' in buf.getvalue()

    def test_green_build_that_ran_tests_clears_test_failure_and_publishes_population(self, plan_context):
        # The positive half: a green build that DID execute tests clears the
        # stale test-failure finding, and the executed-test population it counted
        # is published — non-empty on a healthy test run.
        from _build_shared import cmd_run_common
        from _findings_core import add_finding, query_findings

        add_finding(
            plan_id=plan_context.plan_id,
            finding_type='test-failure',
            title='Test failure: stale assertion',
            detail='from a prior red run',
        )

        log_file = plan_context.fixture_dir / 'green.log'
        log_file.write_text('5 passed\n')

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_run_common(
                result=self._make_success_result(log_file),
                parser_fn=self._fake_parser_with_tests,
                tool_name='python',
                plan_id=plan_context.plan_id,
                command_args='module-tests plan-marshall',
            )

        assert rc == 0
        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        assert tf['filtered_count'] == 1
        record = tf['findings'][0]
        assert record['resolution'] == 'fixed'  # cleared by a build that ran tests
        # Published population is non-empty on a normal (test-running) build.
        assert '5 test(s) executed' in (record.get('resolution_detail') or '')
        assert 'tests_run: 5' in buf.getvalue()


def _tests_run_from_toon(text: str) -> int:
    """Extract the published ``tests_run`` scalar from an emitted build TOON."""
    from toon_parser import parse_toon

    return int(parse_toon(text)['tests_run'])


class TestPublishedCountIsTheExecutedCount:
    """``tests_run`` publishes EXECUTED tests, at both emission sites.

    ``UnitTestSummary.total`` counts skips; ``executed`` does not. The
    distinction only shows up in a summary that HAS skips, so every case here
    carries them — a 5-passed/0-skipped summary reads the same either way and
    would pin nothing.

    The stakes are not cosmetic. ``tests_run`` is the population the green-build
    reconciliation clears a ``test-failure`` finding on, so publishing the
    collected total would let a run that executed nothing destroy a true,
    already-recorded test failure.
    """

    def _make_success_result(self, log_file_path, **extra):
        return {
            'status': 'success',
            'exit_code': 0,
            'duration_seconds': 0.1,
            'log_file': str(log_file_path),
            'command': 'verify',
            **extra,
        }

    @staticmethod
    def _parser_for(summary):
        def _parse(_log_file):
            return [], summary, 'success'

        return _parse

    def test_a_skips_only_green_build_publishes_zero_and_keeps_the_finding(self, plan_context):
        """All-skips: ``total`` is 9, the published count is 0, the finding survives.

        The false-green in full — nine tests collected, none executed, a green
        build. Publishing 9 here would clear a stale test failure on the
        strength of a run that tested nothing.
        """
        from _build_parse import UnitTestSummary
        from _build_shared import cmd_run_common
        from _findings_core import add_finding, query_findings

        add_finding(
            plan_id=plan_context.plan_id,
            finding_type='test-failure',
            title='Test failure: stale assertion',
            detail='from a prior red run',
        )
        log_file = plan_context.fixture_dir / 'skips.log'
        log_file.write_text('9 skipped\n')
        summary = UnitTestSummary(passed=0, failed=0, skipped=9, total=9)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_run_common(
                result=self._make_success_result(log_file),
                parser_fn=self._parser_for(summary),
                tool_name='python',
                plan_id=plan_context.plan_id,
            )

        assert rc == 0
        assert summary.total == 9, 'precondition: the summary must carry a non-zero total'
        assert _tests_run_from_toon(buf.getvalue()) == 0
        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        assert tf['findings'][0]['resolution'] == 'pending'

    def test_a_partially_skipped_green_build_publishes_only_what_ran(self, plan_context):
        """``2 passed, 9 skipped`` publishes 2, not 11."""
        from _build_parse import UnitTestSummary
        from _build_shared import cmd_run_common

        log_file = plan_context.fixture_dir / 'partial.log'
        log_file.write_text('2 passed, 9 skipped\n')
        summary = UnitTestSummary(passed=2, failed=0, skipped=9, total=11)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_run_common(
                result=self._make_success_result(log_file),
                parser_fn=self._parser_for(summary),
                tool_name='python',
                plan_id=plan_context.plan_id,
            )

        assert rc == 0
        assert _tests_run_from_toon(buf.getvalue()) == 2

    def test_run_and_parse_publish_the_same_count_for_one_summary(self, plan_context):
        """The two emission sites agree about one log.

        They are separate code paths reading the same property, so they can
        drift; a consumer comparing a ``run`` result against a later ``parse`` of
        the same log would then see two different populations for one build.
        """
        from types import SimpleNamespace

        from _build_parse import UnitTestSummary
        from _build_shared import cmd_parse_common, cmd_run_common

        log_file = plan_context.fixture_dir / 'both.log'
        log_file.write_text('2 passed, 9 skipped\n')
        summary = UnitTestSummary(passed=2, failed=0, skipped=9, total=11)

        run_buf = io.StringIO()
        with redirect_stdout(run_buf):
            cmd_run_common(
                result=self._make_success_result(log_file),
                parser_fn=self._parser_for(summary),
                tool_name='python',
                plan_id=plan_context.plan_id,
            )

        parse_buf = io.StringIO()
        with redirect_stdout(parse_buf):
            cmd_parse_common(
                SimpleNamespace(log=str(log_file), mode='structured', format='json'),
                self._parser_for(summary),
            )

        import json as _json

        parsed = _json.loads(parse_buf.getvalue())
        assert parsed['metrics']['tests_run'] == 2
        assert _tests_run_from_toon(run_buf.getvalue()) == parsed['metrics']['tests_run']

    def test_a_propagated_count_wins_over_the_local_reparse(self, plan_context):
        """A count the PRODUCER measured beats one this renderer could re-derive.

        The daemon-routed arm stamps the routed job's ``tests_run`` onto the
        result, because on that arm the log this renderer would parse is the
        daemon's JOB log — the inner wrapper's result TOON with none of the test
        runner's output. Re-deriving from it publishes 0 for a run that executed
        the whole suite, which is the boundary defect this pins closed.
        """
        from _build_shared import cmd_run_common

        log_file = plan_context.fixture_dir / 'routed.log'
        log_file.write_text('status: success\ntests_run: 1082\n')

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_run_common(
                # The routed job measured 1082; a parse of this log finds none.
                result=self._make_success_result(log_file, tests_run=1082),
                parser_fn=self._parser_for(None),
                tool_name='python',
                plan_id=plan_context.plan_id,
            )

        assert rc == 0
        assert _tests_run_from_toon(buf.getvalue()) == 1082

    def test_control_no_propagated_count_falls_back_to_the_local_parse(self, plan_context):
        """CONTROL: the in-process arm is unaffected — it still parses its own log.

        Without this the propagation could be satisfied by a change that ignored
        the parse entirely, which would zero out every non-routed build.
        """
        from _build_parse import UnitTestSummary
        from _build_shared import cmd_run_common

        log_file = plan_context.fixture_dir / 'inprocess.log'
        log_file.write_text('2 passed, 9 skipped\n')

        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_run_common(
                result=self._make_success_result(log_file),
                parser_fn=self._parser_for(
                    UnitTestSummary(passed=2, failed=0, skipped=9, total=11)
                ),
                tool_name='python',
                plan_id=plan_context.plan_id,
            )

        assert _tests_run_from_toon(buf.getvalue()) == 2


class TestFailureDetailRoundTrip:
    """The per-signature failure-detail block (deliverable 9) round-trips into
    the ``manage-findings --type test-failure`` store via ``_store_build_findings``."""

    def test_detail_round_trips_into_test_failure_finding(self, plan_context):
        from _build_parse import Issue
        from _build_shared import _store_build_findings
        from _findings_core import query_findings

        block = 'src/calc.py:42: AssertionError\nE  AssertionError: bad state'
        issues = [
            Issue(
                file='test/test_a.py',
                line=10,
                message='AssertionError: bad state',
                severity='error',
                category='test_failure',
                detail=block,
            )
        ]
        _store_build_findings(
            plan_id=plan_context.plan_id,
            tool_name='python',
            issues=issues,
            command_str='module-tests plan-marshall',
        )

        tf = query_findings(plan_context.plan_id, finding_type='test-failure')
        assert tf['filtered_count'] == 1
        detail_text = tf['findings'][0]['detail']
        assert '--- failure detail ---' in detail_text
        assert 'src/calc.py:42' in detail_text
        assert 'AssertionError: bad state' in detail_text

    def test_finding_detail_omits_block_when_issue_carries_none(self, plan_context):
        from _build_parse import Issue
        from _build_shared import _store_build_findings
        from _findings_core import query_findings

        issues = [
            Issue(
                file='src/Main.py',
                line=5,
                message='Compile failed',
                severity='error',
                category='compilation',
            )
        ]
        _store_build_findings(
            plan_id=plan_context.plan_id,
            tool_name='python',
            issues=issues,
            command_str='compile',
        )

        be = query_findings(plan_context.plan_id, finding_type='build-error')
        assert be['filtered_count'] == 1
        assert '--- failure detail ---' not in be['findings'][0]['detail']


class TestErrorsCapTruncation:
    """The shared ``errors`` emission cap is deduped by failure signature and
    reconciled with an explicit ``truncated: N`` marker so count-vs-shown can
    never silently disagree. Because the cap lives in the shared helper the
    reconciliation is correct for Maven/Gradle/npm as well as pyproject."""

    def _make_test_failures(self, count, root_causes):
        from _build_parse import Issue

        issues = []
        for i in range(count):
            rc = i % root_causes
            issues.append(
                Issue(
                    file=f'test/test_{i}.py',
                    line=i + 1,
                    message=f'AssertionError: cause {rc}',
                    severity='error',
                    category='test_failure',
                    # `detail` is presentation-only; `signature` is the dedup
                    # identity. Two failures share a root cause iff they share a
                    # signature — so N failures collapse to `root_causes` groups.
                    detail=f'root-cause-block-{rc}',
                    signature=f'sig-{rc}',
                )
            )
        return issues

    def test_dedup_collapses_shared_signatures_under_cap(self):
        from _build_shared import _cap_errors_with_truncation

        # 30 failures across 5 root causes -> 5 shown, truncated 25.
        errors = self._make_test_failures(30, 5)
        shown, truncated = _cap_errors_with_truncation(errors)

        assert len(shown) == 5
        assert truncated == 25
        assert len(shown) + truncated == len(errors)
        # The shown set covers ALL root causes, deduped by signature.
        assert {i.detail for i in shown} == {f'root-cause-block-{n}' for n in range(5)}

    def test_distinct_root_causes_over_cap_are_capped_and_truncated(self):
        from _build_shared import _cap_errors_with_truncation

        # 25 distinct root causes -> 20 shown (cap), truncated 5.
        errors = self._make_test_failures(25, 25)
        shown, truncated = _cap_errors_with_truncation(errors)

        assert len(shown) == 20
        assert truncated == 5
        assert len(shown) + truncated == 25

    def test_no_truncation_when_within_cap(self):
        from _build_shared import _cap_errors_with_truncation

        errors = self._make_test_failures(3, 3)
        shown, truncated = _cap_errors_with_truncation(errors)

        assert len(shown) == 3
        assert truncated == 0

    def test_non_test_errors_are_not_deduped(self):
        from _build_parse import Issue
        from _build_shared import _cap_errors_with_truncation

        # Only test-failures are collapsed by signature; identical-detail build
        # errors must both survive.
        errors = [
            Issue(file='a.py', line=1, message='same', severity='error', category='compilation', detail='blk'),
            Issue(file='b.py', line=2, message='same', severity='error', category='compilation', detail='blk'),
        ]
        shown, truncated = _cap_errors_with_truncation(errors)

        assert len(shown) == 2
        assert truncated == 0

    def test_distinct_signatures_sharing_truncated_detail_prefix_not_collapsed(self):
        from _build_parse import Issue
        from _build_shared import _cap_errors_with_truncation

        # Two DISTINCT root causes whose (truncated) detail presentation blocks
        # share a long common prefix but whose full signatures differ MUST both
        # survive — keying dedup on the truncated `detail` would wrongly collapse
        # them to one row (CodeRabbit finding 284265). Keying on `signature`
        # keeps them distinct.
        shared_prefix = 'X' * 2000
        errors = [
            Issue(
                file='test/test_a.py',
                line=1,
                message='AssertionError: alpha',
                severity='error',
                category='test_failure',
                detail=shared_prefix,
                signature='sig-alpha',
            ),
            Issue(
                file='test/test_b.py',
                line=2,
                message='AssertionError: beta',
                severity='error',
                category='test_failure',
                detail=shared_prefix,
                signature='sig-beta',
            ),
        ]
        shown, truncated = _cap_errors_with_truncation(errors)

        assert len(shown) == 2
        assert truncated == 0

    def test_missing_signature_falls_back_to_message_key(self):
        from _build_parse import Issue
        from _build_shared import _cap_errors_with_truncation

        # Parsers that do not populate `signature` (Maven/Gradle/npm) fall back to
        # a per-failure category:file:line:message key — distinct terse failures
        # are never over-deduped, and identical ones collapse.
        errors = [
            Issue(file='t.py', line=1, message='boom', severity='error', category='test_failure'),
            Issue(file='t.py', line=1, message='boom', severity='error', category='test_failure'),
            Issue(file='t.py', line=2, message='boom', severity='error', category='test_failure'),
        ]
        shown, truncated = _cap_errors_with_truncation(errors)

        # First two collapse (same key), third is distinct -> 2 shown.
        assert len(shown) == 2
        assert truncated == 1

    def test_cmd_run_common_emits_truncated_marker(self, plan_context):
        from _build_shared import cmd_run_common

        errors = self._make_test_failures(30, 5)

        def parser(_log):
            return errors, None, 'failed'

        log_file = plan_context.fixture_dir / 'fail.log'
        log_file.write_text('failed\n')
        result = {
            'status': 'error',
            'exit_code': 1,
            'duration_seconds': 0.1,
            'log_file': str(log_file),
            'command': 'module-tests plan-marshall',
        }

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_run_common(
                result=result,
                parser_fn=parser,
                tool_name='python',
                plan_id=None,
            )

        assert rc == 0
        # 30 failures collapse to 5 shown root causes -> truncated 25.
        assert 'truncated: 25' in buf.getvalue()


class TestToonErrorRowDetailProjection:
    """`format_toon` must surface `Issue.detail` on error rows (CodeRabbit
    finding c06bb0). `Issue.to_dict()` exposes detail to JSON, but the tabular
    TOON error rows previously dropped it, silently losing the failure detail on
    default output. Multi-line detail is collapsed to a single physical line so
    the row-per-line table stays round-trippable."""

    def test_toon_error_row_includes_detail_when_present(self):
        from _build_format import format_toon
        from _build_parse import Issue

        result = {
            'status': 'error',
            'exit_code': 1,
            'log_file': 'x.log',
            'command': 'module-tests',
            'errors': [
                Issue(
                    file='test/test_a.py',
                    line=10,
                    message='AssertionError: bad state',
                    severity='error',
                    category='test_failure',
                    detail='src/calc.py:42: AssertionError\nE  AssertionError: bad state',
                ),
            ],
        }
        out = format_toon(result)

        # The error-row header declares a `detail` column ...
        assert 'errors[1]{file,line,message,category,detail}' in out
        # ... and the detail content is present, collapsed to one physical line
        # (no raw newline splits the row).
        assert 'src/calc.py:42: AssertionError | E  AssertionError: bad state' in out

    def test_toon_error_rows_round_trip_with_multiline_detail(self):
        from _build_format import format_toon
        from _build_parse import Issue
        from toon_parser import parse_toon

        result = {
            'status': 'error',
            'exit_code': 1,
            'log_file': 'x.log',
            'command': 'module-tests',
            'errors': [
                Issue(
                    file='test/test_a.py',
                    line=10,
                    message='AssertionError: bad state',
                    severity='error',
                    category='test_failure',
                    detail='line one\nline two\nline three',
                ),
            ],
        }
        out = format_toon(result)
        parsed = parse_toon(out)

        # The multi-line detail did not break the one-row-per-line table.
        assert isinstance(parsed.get('errors'), list)
        assert len(parsed['errors']) == 1
        assert parsed['errors'][0]['file'] == 'test/test_a.py'

    def test_toon_error_rows_omit_detail_column_when_absent(self):
        from _build_format import format_toon
        from _build_parse import Issue

        result = {
            'status': 'error',
            'exit_code': 1,
            'log_file': 'x.log',
            'command': 'compile',
            'errors': [
                Issue(
                    file='src/Main.py',
                    line=5,
                    message='Compile failed',
                    severity='error',
                    category='compilation',
                ),
            ],
        }
        out = format_toon(result)

        # Backward-compatible 4-field shape when no error carries a detail.
        assert 'errors[1]{file,line,message,category}' in out
