# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``script-failure-analysis.py``.

The script classifies non-zero-exit script calls in
``script-execution.log`` by stderr signature (invented_subcommand,
missing_required_flag, invented_flag, script_internal_error) and emits a
deduped TOON fragment for the retrospective compile-report consumer.
"""


from __future__ import annotations

from _script_failure_analysis_fixtures import (
    EMITTED_MESSAGE_FORMAT,
    _failure,
    _header,
    _legacy_work_failure,
    _mod,
    _success,
    _work_failure,
    _work_status,
)

# ---------------------------------------------------------------------------
# Unit tests (pure helpers)
# ---------------------------------------------------------------------------


class TestClassifyFailure:
    def test_invented_subcommand_signature(self):
        f = {'exit_code': 2, 'stderr': "argparse: invalid choice: 'nuke' (choose from 'add', 'read')"}
        assert _mod.classify_failure(f) == ('anti-pattern', 'invented_subcommand')

    def test_missing_required_flag_signature(self):
        f = {'exit_code': 2, 'stderr': 'usage: foo\nfoo: error: the following arguments are required: --plan-id'}
        assert _mod.classify_failure(f) == ('anti-pattern', 'missing_required_flag')

    def test_invented_flag_signature(self):
        f = {'exit_code': 2, 'stderr': 'foo: error: unrecognized arguments: --made-up-flag'}
        assert _mod.classify_failure(f) == ('anti-pattern', 'invented_flag')

    def test_argparse_other_falls_through(self):
        f = {'exit_code': 2, 'stderr': 'something weird argparse said'}
        assert _mod.classify_failure(f) == ('anti-pattern', 'argparse_other')

    def test_script_internal_error_on_exit_one(self):
        f = {'exit_code': 1, 'stderr': 'Traceback (most recent call last)'}
        assert _mod.classify_failure(f) == ('bug', 'script_internal_error')


class TestParseFailures:
    def test_skips_successful_calls(self):
        lines = (
            _success('01', 'plan-marshall:manage-files:manage-files', 'read') + '\n'
            + _success('02', 'plan-marshall:manage-tasks:manage-tasks', 'list')
        ).splitlines()
        assert _mod.parse_failures(lines) == []

    def test_captures_failure_with_stderr_block(self):
        lines = (
            _failure(
                '01', 'plan-marshall:manage-tasks:manage-tasks', 'invalid-sub', 2,
                "argparse: invalid choice: 'invalid-sub' (choose from 'add', 'read')",
            ) + '\n'
            + _success('05', 'plan-marshall:manage-files:manage-files', 'read')
        ).splitlines()
        failures = _mod.parse_failures(lines)
        assert len(failures) == 1
        f = failures[0]
        assert f['notation'] == 'plan-marshall:manage-tasks:manage-tasks'
        assert f['subcommand'] == 'invalid-sub'
        assert f['exit_code'] == 2
        assert 'invalid choice' in f['stderr']

    def test_skips_header_with_zero_exit_code_continuation(self):
        # A header whose continuation block reports exit_code 0 is a success.
        lines = (
            _failure(
                '01', 'plan-marshall:manage-files:manage-files', 'read', 0, 'ignored',
            )
        ).splitlines()
        assert _mod.parse_failures(lines) == []

    def test_captures_multiline_stderr_blob(self):
        # stderr that wraps across continuation lines is accumulated. An
        # indented line that looks like a field but is NOT one of the known
        # continuation keys (e.g. ``  details: ...``) must stay part of the
        # stderr blob — _FIELD_RE is restricted to the known keys so it does
        # not prematurely close stderr accumulation.
        lines = [
            _header('01', 'plan-marshall:manage-tasks:manage-tasks', 'add', level='ERROR'),
            '  exit_code: 2',
            '  args: add --plan-id x',
            '  stderr: usage: manage-tasks add',
            'manage-tasks: error: the following arguments are required: --title',
            '  details: some indented error details',
        ]
        failures = _mod.parse_failures(lines)
        assert len(failures) == 1
        assert failures[0]['exit_code'] == 2
        assert 'the following arguments are required' in failures[0]['stderr']
        # The indented field-like line must be captured, not silently dropped.
        assert 'details: some indented error details' in failures[0]['stderr']


class TestParseWorkLogFailures:
    """Unit coverage for the work.log executor-failure parser."""

    def test_captures_argparse_rejection_line(self):
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-status:manage-status', 2, 'argparse_rejection',
                "manage-status.py: error: unrecognized arguments: --field metadata",
            ),
        ]
        scan = _mod.parse_work_log_failures(lines)
        assert len(scan.failures) == 1
        assert scan.unrecognized_lines == 0
        f = scan.failures[0]
        assert f['notation'] == 'plan-marshall:manage-status:manage-status'
        assert f['exit_code'] == 2
        assert f['subcommand'] is None
        assert 'unrecognized arguments' in f['stderr']

    def test_classifies_via_shared_signatures(self):
        # The work.log-sourced diagnostic text flows through the SAME classifier.
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-findings:manage-findings', 2, 'argparse_rejection',
                "manage-findings: error: invalid choice: 'query' (choose from 'add', 'list')",
            ),
        ]
        scan = _mod.parse_work_log_failures(lines)
        assert _mod.classify_failure(scan.failures[0]) == ('anti-pattern', 'invented_subcommand')

    def test_ignores_non_failure_lines(self):
        lines = [
            _work_status('01', 'Starting execute phase'),
            _work_status('02', 'Active worktree set'),
        ]
        scan = _mod.parse_work_log_failures(lines)
        assert scan.failures == []
        # No script_failure marker anywhere → nothing to recognise, so the
        # unmatched guard must stay silent. This is the "scanned a clean log"
        # state, distinct from "recognised no line shape".
        assert scan.unrecognized_lines == 0

    def test_drops_exit_zero_lines(self):
        # An exit_code=0 executor line is an operation failure, never a script
        # failure — it must be dropped even if it carries a script_failure marker.
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-references:manage-references', 0, 'operation_failure',
                'field_not_found',
            ),
        ]
        scan = _mod.parse_work_log_failures(lines)
        assert scan.failures == []
        # The line WAS recognised — it was dropped on the exit-code rule, not
        # because its shape was unknown.
        assert scan.unrecognized_lines == 0

    def test_handles_script_internal_failure_empty_detail(self):
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-references:manage-references', 1,
                'script_internal_failure', '',
            ),
        ]
        scan = _mod.parse_work_log_failures(lines)
        assert len(scan.failures) == 1
        assert scan.unrecognized_lines == 0
        assert scan.failures[0]['exit_code'] == 1
        assert _mod.classify_failure(scan.failures[0]) == ('bug', 'script_internal_error')


class TestProducerDerivedLineShape:
    """The fixture builder is bound to the executor template, not to a literal.

    These tests are the guard the deliverable asks for: they fail when the
    executor renames the trailing field of its dispatch-failure line, because
    the fixture renders that line from the producer's own format string.
    """

    def test_producer_emitted_line_parses_into_one_record(self):
        """A line rendered from the PRODUCER's format parses into exactly one record."""
        lines = [
            _work_failure(
                '01', 'plan-marshall:manage-tasks:manage-tasks', 2, 'argparse_rejection',
                "manage-tasks: error: invalid choice: 'start' (choose from 'add', 'read')",
            ),
        ]
        scan = _mod.parse_work_log_failures(lines)
        assert len(scan.failures) == 1, (
            'the parser no longer recognises the shape the executor emits — '
            f'derived format: {EMITTED_MESSAGE_FORMAT!r}'
        )
        assert scan.unrecognized_lines == 0
        record = scan.failures[0]
        assert record['notation'] == 'plan-marshall:manage-tasks:manage-tasks'
        assert record['exit_code'] == 2
        assert 'invalid choice' in record['stderr']

    def test_retired_tail_shape_reports_unrecognized_not_clean_zero(self):
        """The retired ``stderr=`` tail yields zero failures AND a non-zero unmatched count.

        This is the distinguishability the sink previously lacked: before the
        fix, a producer rename looked identical to a log with no failures.
        """
        lines = [
            _legacy_work_failure(
                '01', 'plan-marshall:manage-status:manage-status', 2, 'argparse_rejection',
            ),
        ]
        scan = _mod.parse_work_log_failures(lines)
        assert scan.failures == []
        assert scan.unrecognized_lines == 1
