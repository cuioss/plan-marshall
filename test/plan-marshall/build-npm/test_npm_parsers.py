#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for npm log parsers (internal module testing).

Note: These tests import internal modules directly for detailed testing.
Public API tests should use npm.py CLI instead.
"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

# Cross-skill imports (PYTHONPATH set by conftest)
from _build_check_warnings import cmd_check_warnings_base
from _build_parse import SEVERITY_ERROR, SEVERITY_WARNING, Issue, UnitTestSummary
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

_npm_parse_errors_mod = load_script_module('plan-marshall', 'build-npm', '_npm_parse_errors.py', '_npm_parse_errors')
_npm_parse_eslint_mod = load_script_module('plan-marshall', 'build-npm', '_npm_parse_eslint.py', '_npm_parse_eslint')
_npm_parse_jest_mod = load_script_module('plan-marshall', 'build-npm', '_npm_parse_jest.py', '_npm_parse_jest')
_npm_parse_tap_mod = load_script_module('plan-marshall', 'build-npm', '_npm_parse_tap.py', '_npm_parse_tap')
_npm_parse_typescript_mod = load_script_module('plan-marshall', 'build-npm', '_npm_parse_typescript.py', '_npm_parse_typescript')

parse_errors = _npm_parse_errors_mod.parse_log
parse_eslint = _npm_parse_eslint_mod.parse_log
parse_jest = _npm_parse_jest_mod.parse_log
parse_tap = _npm_parse_tap_mod.parse_log
parse_typescript = _npm_parse_typescript_mod.parse_log

# Test data location (fixtures in test directory)
TEST_DATA_DIR = Path(__file__).parent / 'fixtures' / 'log-test-data'


def test_typescript_parse_log_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / 'npm-typescript-error-real.log'
    result = parse_typescript(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_typescript_parse_log_extracts_errors():
    """TypeScript errors are extracted with correct fields."""
    log_file = TEST_DATA_DIR / 'npm-typescript-error-real.log'
    issues, test_summary, build_status = parse_typescript(log_file)

    assert len(issues) >= 1
    assert build_status == 'FAILURE'
    assert test_summary is None

    error = issues[0]
    assert isinstance(error, Issue)
    assert error.file is not None
    assert error.line is not None
    assert error.severity == SEVERITY_ERROR
    assert error.category == 'compilation_error'


def test_typescript_no_test_summary():
    """TypeScript parser returns None for test_summary."""
    log_file = TEST_DATA_DIR / 'npm-typescript-error-real.log'
    issues, test_summary, build_status = parse_typescript(log_file)

    assert test_summary is None


def test_typescript_success_on_empty():
    """Empty log returns SUCCESS status."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write('> tsc --build\n\nBuild succeeded.\n')
        f.flush()

        issues, test_summary, build_status = parse_typescript(f.name)

        assert build_status == 'SUCCESS'
        assert len(issues) == 0

        Path(f.name).unlink()


def test_jest_parse_log_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / 'npm-jest-test-failure.log'
    result = parse_jest(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_jest_parse_log_failure_status():
    """Jest failures return FAILURE status."""
    log_file = TEST_DATA_DIR / 'npm-jest-test-failure.log'
    issues, test_summary, build_status = parse_jest(log_file)

    assert build_status == 'FAILURE'


def test_jest_extracts_test_summary():
    """Jest parser extracts test summary counts."""
    log_file = TEST_DATA_DIR / 'npm-jest-test-failure.log'
    issues, test_summary, build_status = parse_jest(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total > 0


def test_jest_extracts_failures():
    """Jest parser extracts test failures as issues."""
    log_file = TEST_DATA_DIR / 'npm-jest-test-failure.log'
    issues, test_summary, build_status = parse_jest(log_file)

    failures = [i for i in issues if i.category == 'test_failure']
    assert len(failures) >= 1


def test_tap_parse_log_success():
    """TAP success log returns SUCCESS status."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert build_status == 'SUCCESS'
    assert len(issues) == 0


def test_tap_parse_log_failure():
    """TAP failure log returns FAILURE status."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-failure-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert build_status == 'FAILURE'


def test_tap_extracts_test_summary_success():
    """TAP parser extracts test summary from success log."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 5
    assert test_summary.passed == 5
    assert test_summary.failed == 0


def test_tap_extracts_test_summary_failure():
    """TAP parser extracts test summary from failure log."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-failure-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 3
    assert test_summary.passed == 1
    assert test_summary.failed == 2


def test_tap_extracts_failures():
    """TAP parser extracts test failures with location info."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-failure-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert len(issues) >= 1
    # Check that at least one issue has location extracted
    issues_with_file = [i for i in issues if i.file is not None]
    assert len(issues_with_file) >= 1


def test_eslint_parse_log_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    result = parse_eslint(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_eslint_extracts_errors():
    """ESLint parser extracts errors from output."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert len(errors) >= 1
    assert build_status == 'FAILURE'


def test_eslint_extracts_warnings():
    """ESLint parser extracts warnings from output."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]
    assert len(warnings) >= 1


def test_eslint_issue_fields():
    """ESLint issues have correct fields populated."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    assert len(issues) >= 1
    issue = issues[0]
    assert isinstance(issue, Issue)
    assert issue.file is not None
    assert issue.line is not None
    assert issue.category == 'lint_error'
    assert issue.message is not None


def test_eslint_no_test_summary():
    """ESLint parser returns None for test_summary."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    assert test_summary is None


def test_npm_errors_eresolve():
    """npm error parser extracts ERESOLVE errors."""
    log_file = TEST_DATA_DIR / 'npm-dependency-error.log'
    issues, test_summary, build_status = parse_errors(log_file)

    assert build_status == 'FAILURE'
    assert len(issues) >= 1
    assert 'ERESOLVE' in issues[0].message
    assert issues[0].category == 'npm_dependency'


def test_npm_errors_e404():
    """npm error parser extracts E404 errors."""
    log_file = TEST_DATA_DIR / 'npm-404-error.log'
    issues, test_summary, build_status = parse_errors(log_file)

    assert build_status == 'FAILURE'
    assert len(issues) >= 1
    assert 'E404' in issues[0].message
    assert issues[0].category == 'npm_error'


def test_npm_errors_no_test_summary():
    """npm error parser returns None for test_summary."""
    log_file = TEST_DATA_DIR / 'npm-dependency-error.log'
    issues, test_summary, build_status = parse_errors(log_file)

    assert test_summary is None


def test_npm_errors_success_on_empty():
    """Empty log returns SUCCESS status."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write('> npm install\nadded 150 packages in 10s\n')
        f.flush()

        issues, test_summary, build_status = parse_errors(f.name)

        assert build_status == 'SUCCESS'
        assert len(issues) == 0

        Path(f.name).unlink()


def test_issue_to_dict():
    """Issue.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    assert len(issues) >= 1
    d = issues[0].to_dict()

    assert 'file' in d
    assert 'line' in d
    assert 'message' in d
    assert 'severity' in d


def test_test_summary_to_dict():
    """UnitTestSummary.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert test_summary is not None
    d = test_summary.to_dict()

    assert d['passed'] == 5
    assert d['failed'] == 0
    assert d['skipped'] == 0
    assert d['total'] == 5


def test_parse_log_file_not_found():
    """Raises FileNotFoundError for missing log file."""
    with pytest.raises(FileNotFoundError):
        parse_typescript('/nonexistent/path/to/log.log')


def test_mixed_typescript_and_jest_output():
    """Test parsing log with both TypeScript errors and Jest failures (H51).

    Verifies that when multiple tool outputs are in a single log,
    at least one parser detects the issues.
    """
    content = """
src/components/App.tsx(15,3): error TS2339: Property 'x' does not exist on type 'Props'.
src/utils/helper.ts(42,10): error TS2345: Argument of type 'string' is not assignable.

FAIL src/components/__tests__/App.test.tsx
  ● App component › should render correctly

    expect(received).toBe(expected)

    Expected: true
    Received: false

      at Object.<anonymous> (src/components/__tests__/App.test.tsx:25:10)

Tests:       1 failed, 5 passed, 6 total
Test Suites: 1 failed, 2 passed, 3 total
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()

        # TypeScript parser should detect TS errors
        ts_issues, _, ts_status = parse_typescript(f.name)
        assert len(ts_issues) >= 2, 'TypeScript parser should find TS errors'
        assert ts_status == 'FAILURE'

        # Jest parser should detect test failures
        jest_issues, jest_summary, jest_status = parse_jest(f.name)
        assert jest_status == 'FAILURE'
        assert jest_summary is not None
        assert jest_summary.failed >= 1

        Path(f.name).unlink()


# =========================================================================
# Caller-baselined warning-count gate (build-npm --warning-baseline)
# =========================================================================


def _warn(message: str, wtype: str = 'javadoc_warning', severity: str = 'WARNING') -> dict:
    """Build a minimal warning dict (javadoc_warning classifies as fixable)."""
    return {'type': wtype, 'message': message, 'severity': severity}


def _warn_args(warnings: list[dict], *, baseline: int | None = None, with_baseline: bool = True) -> SimpleNamespace:
    """Build an argparse-like namespace for cmd_check_warnings_base.

    When ``with_baseline`` is False the ``warning_baseline`` attribute is omitted
    entirely, mirroring build-maven/build-gradle whose parsers never register the
    flag (getattr default keeps them unaffected).
    """
    ns = SimpleNamespace(warnings=json.dumps(warnings), acceptable_warnings=None)
    if with_baseline:
        ns.warning_baseline = baseline
    return ns


def test_warning_baseline_satisfied_reports_pass_gate(capsys):
    """actionable <= baseline → gate.status pass and the gate is authoritative for exit 0."""
    args = _warn_args([_warn('one'), _warn('two')], baseline=2)

    exit_code = cmd_check_warnings_base(args, matcher='substring')
    output = parse_toon(capsys.readouterr().out)

    assert output['gate']['baseline'] == 2
    assert output['gate']['actual'] == 2
    assert output['gate']['status'] == 'pass'
    # A supplied baseline overrides the base fixable/unknown exit rule: the gate
    # passing exits 0 even though two fixable (actionable > 0) warnings were found.
    assert exit_code == 0


def test_warning_baseline_satisfied_all_acceptable_exits_zero(capsys):
    """A zero-actionable run under baseline passes the gate and exits 0."""
    args = SimpleNamespace(
        warnings=json.dumps([_warn('known issue', wtype='other')]),
        acceptable_warnings=json.dumps({'g': ['known issue']}),
        warning_baseline=0,
    )

    exit_code = cmd_check_warnings_base(args, matcher='substring')
    output = parse_toon(capsys.readouterr().out)

    assert output['gate']['actual'] == 0
    assert output['gate']['status'] == 'pass'
    assert exit_code == 0


def test_warning_baseline_exceeded_fails_gate_and_exits_1(capsys):
    """actionable > baseline → gate.status fail and exit code 1."""
    args = _warn_args([_warn('one'), _warn('two'), _warn('three')], baseline=1)

    exit_code = cmd_check_warnings_base(args, matcher='substring')
    output = parse_toon(capsys.readouterr().out)

    assert output['gate']['baseline'] == 1
    assert output['gate']['actual'] == 3
    assert output['gate']['status'] == 'fail'
    assert exit_code == 1


def test_no_warning_baseline_leaves_output_and_exit_unchanged(capsys):
    """Omitting the baseline attribute (maven/gradle case) adds no gate block."""
    warnings = [_warn('one')]

    args_absent = _warn_args(warnings, with_baseline=False)
    exit_absent = cmd_check_warnings_base(args_absent, matcher='substring')
    out_absent = parse_toon(capsys.readouterr().out)

    args_none = _warn_args(warnings, baseline=None)
    exit_none = cmd_check_warnings_base(args_none, matcher='substring')
    out_none = parse_toon(capsys.readouterr().out)

    assert 'gate' not in out_absent
    assert 'gate' not in out_none
    # A None baseline behaves identically to no baseline attribute at all.
    assert exit_absent == exit_none == 1


def test_npm_cli_warning_baseline_gates():
    """The npm CLI registers --warning-baseline and routes it to the handler."""
    warnings = json.dumps([_warn('one'), _warn('two')])
    script = get_script_path('plan-marshall', 'build-npm', 'npm.py')

    exceeded = run_script(script, 'check-warnings', '--warnings', warnings, '--warning-baseline', '1')
    assert exceeded.returncode == 1
    assert 'fail' in exceeded.stdout

    satisfied = run_script(script, 'check-warnings', '--warnings', warnings, '--warning-baseline', '5')
    # gate passes (actionable 2 <= 5) and is authoritative for the exit code.
    assert 'pass' in satisfied.stdout
    assert satisfied.returncode == 0
