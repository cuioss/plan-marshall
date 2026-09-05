#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A daemon-routed failing build carries the INNER wrapper's per-test rows.

The log a routed run hands back is the daemon JOB log — the inner wrapper's
emitted TOON document, not the raw test-runner output. Re-parsing it as if it
were test-runner output finds no per-test rows at all, so the renderer fell
through to its synthetic ``build_failure`` row reading *"Build failed but no
structured errors were parsed"* — publishing that over findings the inner
wrapper had already parsed correctly one layer in.

This is the same boundary rule ``routed_tests_run`` already follows one field
over: a routed result carries what the routed job produced, and the outer wrapper
re-derives nothing it was handed.

Three seams are driven, in the order the value travels:

1. ``_build_server_protocol.read_log_verdict`` — reads the wrapper's own
   ``errors[]`` table back out of the job log.
2. ``_build_execute_factory._daemon_result_to_direct`` — attaches those rows to
   the routed result under ``routed_errors``.
3. ``_build_shared.cmd_run_common`` — prefers them over its own re-parse.

Every case that asserts the carry is matched by its opposite: the SAME input with
the carry absent must still produce the synthetic row, or this whole module would
be satisfied by a change that simply stopped synthesising anything.
"""

from __future__ import annotations

import _build_execute_factory as factory
import _build_server_protocol as proto
from _build_parse import Issue, UnitTestSummary
from _build_shared import cmd_run_common

_INNER_ROW = (
    '  test/test_thing.py,8,'
    '"Test test_thing failed, at last",'
    'test_failure,'
    '"test/test_thing.py:8: in test_thing | E   AssertionError: assert 1 == 2"'
)

#: A job log exactly as the daemon captures it: the inner wrapper's result TOON,
#: preceded by the supervisor's own `[EXEC]` progress line. The message carries a
#: comma on purpose — the serializer quotes it, and a hand-rolled comma split
#: would shred precisely the row this exists to recover.
_ROUTED_FAILURE_LOG = f"""[EXEC] ./pw module-tests plan-marshall
status: error
exit_code: 1
duration_seconds: 9
log_file: /inner/python-run.log
command: ./pw module-tests plan-marshall
error: build_failed
errors[1]{{file,line,message,category,detail}}:
{_INNER_ROW}
tests:
  passed: 398
  failed: 1
  skipped: 0
"""

_GREEN_JOB_LOG = 'status: success\nexit_code: 0\ntests_run: 398\n'


def _write(tmp_path, name, content):
    """Write ``content`` to ``tmp_path/name`` and return the path as a string."""
    path = tmp_path / name
    path.write_text(content)
    return str(path)


# ===========================================================================
# Seam 1 — the job-log reader recovers the inner table
# ===========================================================================


class TestReadLogVerdictCarriesErrors:
    """``read_log_verdict`` reads the wrapper's ``errors[]`` table, not just scalars."""

    def test_carries_the_inner_error_rows(self, tmp_path):
        verdict = proto.read_log_verdict(_write(tmp_path, 'job.log', _ROUTED_FAILURE_LOG))

        assert verdict is not None
        assert verdict.status == 'error'
        assert len(verdict.errors) == 1

    def test_each_row_keeps_its_columns(self, tmp_path):
        verdict = proto.read_log_verdict(_write(tmp_path, 'job.log', _ROUTED_FAILURE_LOG))

        row = verdict.errors[0]
        assert row['file'] == 'test/test_thing.py'
        assert row['line'] == 8
        assert row['category'] == 'test_failure'
        assert 'AssertionError: assert 1 == 2' in row['detail']

    def test_a_quoted_message_survives_its_embedded_comma(self, tmp_path):
        """The canonical TOON parser owns the split; a naive one would shred this."""
        verdict = proto.read_log_verdict(_write(tmp_path, 'job.log', _ROUTED_FAILURE_LOG))

        assert verdict.errors[0]['message'] == 'Test test_thing failed, at last'

    def test_a_green_log_carries_no_rows(self, tmp_path):
        """Matched negative: the table is genuinely absent, not defaulted in."""
        verdict = proto.read_log_verdict(_write(tmp_path, 'job.log', _GREEN_JOB_LOG))

        assert verdict is not None
        assert verdict.errors == ()

    def test_the_scalar_keys_after_the_table_are_still_read(self, tmp_path):
        """A column-0 key closes the table and is itself parsed, not swallowed."""
        content = (
            'errors[1]{file,line,message,category}:\n'
            '  test/a.py,1,boom,test_failure\n'
            'status: error\n'
            'exit_code: 3\n'
        )
        verdict = proto.read_log_verdict(_write(tmp_path, 'job.log', content))

        assert verdict is not None
        assert verdict.exit_code == 3
        assert len(verdict.errors) == 1

    def test_a_truncated_table_yields_no_rows_rather_than_invented_ones(self, tmp_path):
        """A log cut off mid-table declares more rows than it wrote.

        Reporting the partial set as if it were complete would understate the
        failure silently; no rows at all leaves the caller on its own pre-existing
        path, which is the honest outcome.
        """
        content = 'status: error\nexit_code: 1\nerrors[4]{file,line,message,category}:\n  test/a.py,1,boom,test_failure\n'
        verdict = proto.read_log_verdict(_write(tmp_path, 'job.log', content))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.errors == ()


# ===========================================================================
# Seam 2 — the routing layer attaches them to the result
# ===========================================================================


class TestDaemonResultCarriesRoutedErrors:
    """``_daemon_result_to_direct`` hands the rows on under ``routed_errors``."""

    @staticmethod
    def _routed(log_file, job_status='failure'):
        return factory._daemon_result_to_direct(
            {
                'job_status': job_status,
                'log_file': log_file,
                'duration_seconds': 9,
                'exit_code': 1,
            },
            './pw module-tests plan-marshall',
        )

    def test_a_routed_failure_attaches_the_inner_rows(self, tmp_path):
        result = self._routed(_write(tmp_path, 'job.log', _ROUTED_FAILURE_LOG))

        assert result['status'] == 'error'
        assert len(result['routed_errors']) == 1
        assert result['routed_errors'][0]['file'] == 'test/test_thing.py'

    def test_a_failure_whose_log_carries_no_table_attaches_no_key(self, tmp_path):
        """Matched negative: absence is absence, so the renderer keeps its parse."""
        content = 'status: error\nexit_code: 1\n'
        result = self._routed(_write(tmp_path, 'job.log', content))

        assert result['status'] == 'error'
        assert 'routed_errors' not in result

    def test_an_unreadable_log_attaches_no_key(self, tmp_path):
        result = self._routed(str(tmp_path / 'absent.log'))

        assert result['status'] == 'error'
        assert 'routed_errors' not in result


# ===========================================================================
# Seam 3 — the emit choke point prefers the carried rows
# ===========================================================================


def _empty_parser(log_file):
    """The routed reality: re-parsing a TOON job log finds no per-test rows."""
    return [], None, 'FAILURE'


def _in_process_parser(log_file):
    """An in-process build's own parse, which must stay authoritative."""
    issues = [
        Issue(
            file='test/test_local.py',
            line=3,
            message='assert 0',
            severity='error',
            category='test_failure',
        )
    ]
    return issues, UnitTestSummary(passed=1, failed=1, skipped=0, total=2), 'FAILURE'


def _failing_result(**extra):
    """The ``DirectCommandResult`` shape ``cmd_run_common`` consumes, on the red leg."""
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 9,
        'log_file': '/tmp/routed-errors-test.log',
        'command': './pw module-tests plan-marshall',
        'timeout_used_seconds': 330,
        'error': 'build_failed',
    }
    result.update(extra)
    return result


_CARRIED_ROWS = [
    {
        'file': 'test/test_thing.py',
        'line': 8,
        'message': 'Test test_thing failed',
        'category': 'test_failure',
        'detail': 'E   AssertionError: assert 1 == 2',
    }
]

_SYNTHETIC = 'no structured errors were parsed'


class TestRoutedErrorsWinOverTheReparse:
    """The renderer publishes the carried rows instead of synthesising one."""

    def test_the_carried_row_reaches_the_emitted_errors_table(self, capsys):
        cmd_run_common(_failing_result(routed_errors=_CARRIED_ROWS), _empty_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'test/test_thing.py' in stdout
        assert 'Test test_thing failed' in stdout

    def test_the_synthetic_row_is_not_published(self, capsys):
        cmd_run_common(_failing_result(routed_errors=_CARRIED_ROWS), _empty_parser, 'python')

        assert _SYNTHETIC not in capsys.readouterr().out

    def test_control_without_the_carry_the_synthetic_row_still_appears(self, capsys):
        """THE matched control, and the reason the rest of this class means anything.

        The identical failing result and the identical empty parse — only the
        carry removed. The synthetic row must still be there: it is the
        status/``errors[]`` contradiction guard, and this fix narrows when it
        fires without removing it.
        """
        cmd_run_common(_failing_result(), _empty_parser, 'python')

        assert _SYNTHETIC in capsys.readouterr().out

    def test_an_empty_carry_is_not_a_carry(self, capsys):
        """An empty list means the routed log held no table — keep the guard."""
        cmd_run_common(_failing_result(routed_errors=[]), _empty_parser, 'python')

        assert _SYNTHETIC in capsys.readouterr().out

    def test_an_in_process_build_keeps_its_own_parse(self, capsys):
        """Control: a build carrying no ``routed_errors`` is untouched by the carry."""
        cmd_run_common(_failing_result(), _in_process_parser, 'python')
        stdout = capsys.readouterr().out

        assert 'test/test_local.py' in stdout
        assert _SYNTHETIC not in stdout

    def test_the_carry_key_is_not_leaked_into_the_emitted_payload(self, capsys):
        """``routed_errors`` is an INPUT to the renderer, like ``routed_tests_run``."""
        cmd_run_common(_failing_result(routed_errors=_CARRIED_ROWS), _empty_parser, 'python')

        assert 'routed_errors' not in capsys.readouterr().out
