#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for maven parse functionality (internal module testing).

Note: These tests import internal modules directly for detailed testing.
Public API tests should use maven.py CLI instead.
"""

# Direct imports - conftest sets up PYTHONPATH (cross-skill)
from pathlib import Path

import pytest
from _build_parse import SEVERITY_ERROR, SEVERITY_WARNING, Issue, UnitTestSummary

from conftest import get_script_path, load_script_module, run_script

_maven_cmd_parse_mod = load_script_module('plan-marshall', 'build-maven', '_maven_cmd_parse.py', '_maven_cmd_parse')

parse_log = _maven_cmd_parse_mod.parse_log

# CLI entry point for the parse subcommand (routes through cmd_parse_common,
# where the seam-(b) truthful-status derivation lives).
SCRIPT_PATH = get_script_path('plan-marshall', 'build-maven', 'maven.py')

# Test data location (fixtures in test directory)
TEST_DATA_DIR = Path(__file__).parent / 'fixtures' / 'log-test-data'


# =============================================================================
# Success Log Tests
# =============================================================================


def test_parse_log_success_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    result = parse_log(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_parse_log_success_build_status():
    """Successful build returns SUCCESS status."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert build_status == 'SUCCESS'


def test_parse_log_success_test_summary():
    """Successful build returns UnitTestSummary with correct counts."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 4892
    assert test_summary.passed == 4892
    assert test_summary.failed == 0
    assert test_summary.skipped == 0


def test_parse_log_success_issues_are_issue_objects():
    """Issues in result are Issue dataclass instances."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    # All issues should be Issue instances
    for issue in issues:
        assert isinstance(issue, Issue)


def test_parse_log_success_no_errors():
    """Successful build has no ERROR severity issues."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert len(errors) == 0


# =============================================================================
# Failure Log Tests
# =============================================================================


def test_parse_log_failure_build_status():
    """Failed build returns FAILURE status."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert build_status == 'FAILURE'


def test_parse_log_failure_has_errors():
    """Failed build returns errors in issues list."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert len(errors) > 0


def test_parse_log_failure_error_fields():
    """Error issues have correct fields populated."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]

    # Find the "cannot find symbol" error
    symbol_errors = [e for e in errors if 'cannot find symbol' in e.message]
    assert len(symbol_errors) >= 1

    error = symbol_errors[0]
    assert error.file is not None
    assert error.file.endswith('.java')
    assert error.line is not None
    assert error.category == 'compilation_error'


def test_parse_log_failure_has_warnings():
    """Failed build includes warnings in issues list."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]
    assert len(warnings) >= 1


def test_parse_log_failure_warning_category():
    """Warnings have correct category assigned."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]

    # Should have deprecation warning
    deprecation = [w for w in warnings if 'deprecation' in w.category]
    assert len(deprecation) >= 1


def test_parse_log_failure_test_summary():
    """Failed build returns UnitTestSummary with failures."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 51
    assert test_summary.failed == 2  # Maven: Failures(2) + Errors(0)
    assert test_summary.skipped == 0
    assert test_summary.passed == 49  # 51 - 2 - 0


# =============================================================================
# Issue Object Tests
# =============================================================================


def test_issue_to_dict():
    """Issue.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert issues, 'failure log must yield at least one issue'
    d = issues[0].to_dict()

    assert 'file' in d
    assert 'line' in d
    assert 'message' in d
    assert 'severity' in d


def test_test_summary_to_dict():
    """UnitTestSummary.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    d = test_summary.to_dict()

    assert d['passed'] == 4892
    assert d['failed'] == 0
    assert d['skipped'] == 0
    assert d['total'] == 4892


# =============================================================================
# Truthful-status regression (seam b): cmd_parse_common status derivation
# =============================================================================


def test_parse_log_testfailureignore_raw_build_status_and_failures():
    """The raw parse of the testFailureIgnore fixture yields BUILD SUCCESS with
    failed > 0 — the exact untruthful-green window cmd_parse_common must resolve
    to error. detect_build_status only checks failure markers, so a log with no
    [ERROR]/BUILD FAILURE marker keeps build_status == 'SUCCESS'.
    """
    log_file = TEST_DATA_DIR / 'maven-testfailureignore-green.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert build_status == 'SUCCESS'
    assert test_summary is not None
    assert test_summary.failed == 2  # Maven: Failures(0) + Errors(2)


def test_parse_cli_testfailureignore_reports_error_status():
    """Seam (b): the parse CLI (cmd_parse_common) resolves status=error when
    test_summary.failed > 0 despite a BUILD SUCCESS marker — a BUILD SUCCESS
    string alone must never report success over erroring tests.
    """
    log_file = TEST_DATA_DIR / 'maven-testfailureignore-green.log'
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(log_file))

    data = result.toon()
    assert data.get('status') == 'error', (
        f'BUILD SUCCESS with errored tests must report error, not success: {data}'
    )


# =============================================================================
# Edge Cases
# =============================================================================


def test_parse_log_file_not_found():
    """Raises FileNotFoundError for missing log file."""
    with pytest.raises(FileNotFoundError):
        parse_log('/nonexistent/path/to/log.log')


def test_parse_log_no_tests(tmp_path):
    """Handles log without test summary gracefully."""
    content = """[INFO] Scanning for projects...
[INFO] BUILD SUCCESS
[INFO] Total time: 1.234 s
"""
    log_file = tmp_path / 'no-tests.log'
    log_file.write_text(content)

    issues, test_summary, build_status = parse_log(str(log_file))

    assert build_status == 'SUCCESS'
    assert test_summary is None


# =============================================================================
# The published executed-test count, from a maven caller
# =============================================================================
#
# The count and the routed-arm propagation live in the SHARED emit choke point,
# so they are tool-agnostic by construction. Driving them from a maven caller is
# what makes that claim checkable rather than assumed: a fix that only worked for
# the tool it was written against would pass its own suite and leave every other
# build wrapper publishing the wrong number.


def _emit_maven_success(capsys, parser, **result_extra) -> dict:
    """Run the shared emit path with a maven-shaped result and return the JSON.

    The result is built as a plain dict and cast, because ``tests_run`` — which
    the routed arm stamps onto the result at the boundary — is not a declared key
    of ``DirectCommandResult``. Declaring it there is the correct modelling and
    is outside this deliverable's write set, so the gap is named here rather than
    papered over silently.
    """
    import json
    from typing import Any, cast

    import _build_shared
    from _build_result import DirectCommandResult

    result: dict[str, Any] = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 12,
        'log_file': '/tmp/does-not-matter.log',
        'command': './mvnw verify',
        **result_extra,
    }
    assert (
        _build_shared.cmd_run_common(
            cast(DirectCommandResult, result), parser, 'maven', output_format='json'
        )
        == 0
    )
    emitted: dict = json.loads(capsys.readouterr().out)
    return emitted


def test_maven_published_count_excludes_skipped_tests(capsys):
    """A Surefire summary with skips publishes only what Surefire actually ran."""

    def _skips_parser(log_file, *args):
        return ([], UnitTestSummary(passed=2, failed=0, skipped=9, total=11), 'SUCCESS')

    emitted = _emit_maven_success(capsys, _skips_parser)

    assert emitted['tests_run'] == 2


def test_maven_routed_arm_publishes_the_routed_jobs_count(capsys):
    """The routed job's count crosses the boundary instead of being re-derived.

    This is the DA boundary fix. On the routed arm the log the outer wrapper
    holds is the daemon's JOB log — the inner wrapper's result TOON with none of
    Surefire's output — so the parser stub returns no summary, exactly as the
    real parse of that log would. A re-derivation publishes ``0``; the propagated
    count publishes what the routed job measured.

    It is a RECURRENCE, not a new field bug: the same wrapper-boundary
    substitution was already fixed field-scoped for ``duration_seconds`` at this
    boundary, and ``tests_run`` was left behind it.
    """

    def _job_log_parser(log_file, *args):
        return ([], None, 'SUCCESS')

    emitted = _emit_maven_success(capsys, _job_log_parser, tests_run=4892)

    assert emitted['tests_run'] == 4892


def test_control_maven_in_process_arm_still_parses_its_own_log(capsys):
    """CONTROL: with no propagated count the local parse is still used.

    Without this the propagation could be satisfied by ignoring the parse
    entirely, which would zero the count for every non-routed maven build.
    """

    def _full_run_parser(log_file, *args):
        return ([], UnitTestSummary(passed=4892, failed=0, skipped=0, total=4892), 'SUCCESS')

    emitted = _emit_maven_success(capsys, _full_run_parser)

    assert emitted['tests_run'] == 4892
