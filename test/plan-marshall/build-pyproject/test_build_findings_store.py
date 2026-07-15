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
    """A green build run terminalizes every pending build finding from a
    prior failing run."""

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

    def test_reconcile_resolves_all_pending_build_findings(self, plan_context):
        from _build_shared import _reconcile_pending_build_findings
        from _findings_core import query_findings

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
        from _build_shared import _reconcile_pending_build_findings

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
                )

        assert rc == 0
        mock_reconcile.assert_called_once_with(
            plan_id=plan_context.plan_id,
            command_str='verify',
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
            )

        assert rc == 0
        q = query_findings(plan_context.plan_id, finding_type='build-error')
        assert q['filtered_count'] == 1
        assert q['findings'][0]['resolution'] == 'fixed'


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
