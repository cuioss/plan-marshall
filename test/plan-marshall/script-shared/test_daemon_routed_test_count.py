# SPDX-License-Identifier: FSL-1.1-ALv2
"""The daemon-routed executed-test count survives the client return path.

The defect (finding 34fe2d): a routed ``module-tests`` run that executed 2750
tests reported ``tests_run: 0`` on the outer TOON and printed *"this run tested
nothing"*. The inner wrapper had measured and published the count correctly; it
was lost between the daemon job log and the outer client result, because the
outer renderer re-parses THAT log — which holds the wrapper's emitted TOON, not
the raw test-runner output — and finds no test summary in it.

Both halves are driven against a real on-disk job log written in the wrapper's
own TOON shape, so these tests bind to the format the wrapper actually emits
rather than to a hand-built stub of it. Every assertion is stated beside its
opposite: a measured count must arrive AS the count, and an unmeasured one must
arrive as UNMEASURED — a suite that only pinned one of the two could be satisfied
by a renderer that always reports the same thing.
"""

import io
from contextlib import redirect_stdout

import _build_execute_factory as factory
import _build_shared as build_shared


def _write_wrapper_toon(path, *, status='success', exit_code=0, tests_run=None):
    """Write a job log in the shape the build wrapper emits into it.

    The wrapper streams progress lines first and prints its result TOON last, so
    the fixture reproduces that ordering rather than a bare key/value block.
    """
    lines = [
        '[EXEC] ./pw module-tests plan-marshall',
        '[EXEC] green build: analyses examined: test; '
        f'{"unknown" if tests_run is None else tests_run} test(s) executed',
        f'status: {status}',
        f'exit_code: {exit_code}',
        'duration_seconds: 455',
        'log_file: /some/inner/build.log',
        'command: ./pw module-tests plan-marshall',
    ]
    if tests_run is not None:
        lines.append(f'tests_run: {tests_run}')
    path.write_text('\n'.join(lines) + '\n')
    return path


def _waited(log_path, *, job_status='success', duration=455, exit_code=0):
    """A daemon ``wait`` status-TOON for a terminal job."""
    return {
        'job_status': job_status,
        'log_file': str(log_path),
        'duration_seconds': duration,
        'exit_code': exit_code,
    }


def _noop_parser(_log_file):
    """The outer parser's real behaviour on a daemon job log: no test summary.

    This is not a convenience stub — it IS what the pyproject parser returns for
    a log containing the wrapper's TOON rather than pytest output, and it is the
    condition under which the count used to collapse to zero.
    """
    return [], None, 'success'


class TestRoutedResultCarriesTheInnerCount:
    """``_daemon_result_to_direct`` attaches the count the inner build measured."""

    def test_measured_count_is_attached_to_the_routed_result(self, tmp_path):
        log = _write_wrapper_toon(tmp_path / 'job.log', tests_run=2750)

        result = factory._daemon_result_to_direct(_waited(log), './pw module-tests plan-marshall')

        assert result['status'] == 'success'
        assert result['routed_tests_run'] == 2750

    def test_absent_count_attaches_no_key_at_all(self, tmp_path):
        # The matched negative. The key's ABSENCE is what makes the count read as
        # unknown downstream; attaching a zero here would be the original defect
        # relocated one function earlier.
        log = _write_wrapper_toon(tmp_path / 'job.log', tests_run=None)

        result = factory._daemon_result_to_direct(_waited(log), './pw module-tests plan-marshall')

        assert result['status'] == 'success'
        assert 'routed_tests_run' not in result

    def test_measured_zero_is_carried_as_a_zero(self, tmp_path):
        # A non-test gate genuinely executed none: distinct from the absent case.
        log = _write_wrapper_toon(tmp_path / 'job.log', tests_run=0)

        result = factory._daemon_result_to_direct(_waited(log), './pw quality-gate plan-marshall')

        assert result['routed_tests_run'] == 0


class TestOuterResultPublishesTheRoutedCount:
    """End-to-end through the renderer: the outer TOON reports what ran."""

    def test_routed_run_publishes_the_inner_count(self, tmp_path):
        log = _write_wrapper_toon(tmp_path / 'job.log', tests_run=2750)
        routed = factory._daemon_result_to_direct(_waited(log), './pw module-tests plan-marshall')

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = build_shared.cmd_run_common(
                result=routed,
                parser_fn=_noop_parser,
                tool_name='python',
                command_args='module-tests plan-marshall',
            )

        assert rc == 0
        out = buf.getvalue()
        assert 'tests_run: 2750' in out
        assert 'tests_population: measured' in out

    def test_routed_run_no_longer_claims_it_tested_nothing(self, tmp_path, capsys):
        log = _write_wrapper_toon(tmp_path / 'job.log', tests_run=2750)
        routed = factory._daemon_result_to_direct(_waited(log), './pw module-tests plan-marshall')

        build_shared.cmd_run_common(
            result=routed,
            parser_fn=_noop_parser,
            tool_name='python',
            command_args='module-tests plan-marshall',
        )

        captured = capsys.readouterr()
        assert 'this run tested nothing' not in captured.err
        assert '2750 test(s) executed' in captured.err

    def test_routed_run_without_a_count_reports_unmeasured_not_zero(self, tmp_path):
        # The matched negative, end-to-end: the outer result must OMIT the count
        # rather than publish a zero, so a consumer reading `tests_run` cannot
        # read "tested nothing" off a run whose population is simply unknown.
        log = _write_wrapper_toon(tmp_path / 'job.log', tests_run=None)
        routed = factory._daemon_result_to_direct(_waited(log), './pw module-tests plan-marshall')

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = build_shared.cmd_run_common(
                result=routed,
                parser_fn=_noop_parser,
                tool_name='python',
                command_args='module-tests plan-marshall',
            )

        assert rc == 0
        out = buf.getvalue()
        assert 'tests_population: unmeasured' in out
        assert 'tests_run' not in out


class TestRoutedCountGatesFindingReconciliation:
    """The count's measurability decides what the routed green may clear."""

    def test_measured_routed_count_entitles_clearing_a_test_failure(self, tmp_path, monkeypatch):
        log = _write_wrapper_toon(tmp_path / 'job.log', tests_run=2750)
        routed = factory._daemon_result_to_direct(_waited(log), './pw module-tests plan-marshall')

        captured: dict = {}

        def _spy(**kwargs):
            captured.update(kwargs)
            return 1

        monkeypatch.setattr(build_shared, '_reconcile_pending_build_findings', _spy)

        buf = io.StringIO()
        with redirect_stdout(buf):
            build_shared.cmd_run_common(
                result=routed,
                parser_fn=_noop_parser,
                tool_name='python',
                plan_id='a-real-plan',
                command_args='module-tests plan-marshall',
            )

        assert captured['tests_run'] == 2750
        assert captured['analyses'] == frozenset({'test'})

    def test_unmeasured_routed_count_entitles_nothing(self, tmp_path, monkeypatch):
        # The matched half: identical routed green, identical gate, the count
        # simply absent — and the reconciler is handed None, which clears no
        # test-failure finding (pinned in test_build_examined_population.py).
        log = _write_wrapper_toon(tmp_path / 'job.log', tests_run=None)
        routed = factory._daemon_result_to_direct(_waited(log), './pw module-tests plan-marshall')

        captured: dict = {}

        def _spy(**kwargs):
            captured.update(kwargs)
            return 0

        monkeypatch.setattr(build_shared, '_reconcile_pending_build_findings', _spy)

        buf = io.StringIO()
        with redirect_stdout(buf):
            build_shared.cmd_run_common(
                result=routed,
                parser_fn=_noop_parser,
                tool_name='python',
                plan_id='a-real-plan',
                command_args='module-tests plan-marshall',
            )

        assert captured['tests_run'] is None
