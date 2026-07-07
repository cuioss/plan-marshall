#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _pyproject_cmd_parse.py (direct parser API).

Tests the pyproject build log parser directly (not through pyproject_build.py).

Note: test_pyproject_build.py also tests parse_log() but through the build
script module loader with mocked dependencies. This file tests the parser in
isolation for detailed coverage of mypy/ruff/pytest output patterns.
"""

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by conftest)
from _build_parse import Issue, UnitTestSummary, read_log_text

from conftest import load_script_module

_pyproject_cmd_parse_mod = load_script_module('plan-marshall', 'build-pyproject', '_pyproject_cmd_parse.py', '_pyproject_cmd_parse')

parse_log = _pyproject_cmd_parse_mod.parse_log
_REGISTRY = _pyproject_cmd_parse_mod._REGISTRY
_has_pytest_output = _pyproject_cmd_parse_mod._has_pytest_output


@contextmanager
def _temp_log(content: str) -> Iterator[str]:
    """Write content to a temp .log file, yield its path, and unlink on exit."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        path = f.name
    try:
        yield path
    finally:
        Path(path).unlink()


def test_parse_mypy_errors():
    """Extracts mypy type errors with file and line."""
    content = """src/main.py:10: error: Incompatible types in assignment
src/utils.py:25: error: Missing return statement
Found 2 errors in 2 files
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert len(issues) == 2
    assert issues[0].file == 'src/main.py'
    assert issues[0].line == 10
    assert issues[0].category == 'type_error'
    assert issues[0].severity == 'error'
    assert 'Incompatible types' in issues[0].message


def test_parse_mypy_no_errors():
    """Returns empty issues for clean mypy output."""
    content = """Success: no issues found in 5 source files\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert len(issues) == 0


def test_parse_ruff_errors():
    """Extracts ruff lint errors with file, line, and rule code."""
    content = """src/main.py:15:1: E501 Line too long (120 > 88)
src/utils.py:30:5: F401 'os' imported but unused
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert len(issues) == 2
    assert issues[0].file == 'src/main.py'
    assert issues[0].line == 15
    assert issues[0].category == 'lint_error'
    assert 'E501' in issues[0].message


def test_parse_pytest_failures():
    """Extracts pytest test failures with file and message."""
    content = """FAILED test/test_main.py::test_addition - AssertionError: assert 1 == 2
FAILED test/test_utils.py::test_helper
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert len(issues) == 2
    assert issues[0].file == 'test/test_main.py'
    assert issues[0].category == 'test_failure'
    assert 'AssertionError' in issues[0].message
    assert issues[1].message == 'Test test_helper failed'


def test_parse_pytest_summary():
    """Extracts pytest summary with passed, failed, skipped counts."""
    content = """================ 40 passed, 2 failed, 1 skipped in 5.23s ================\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        _, test_summary, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.passed == 40
    assert test_summary.failed == 2
    assert test_summary.skipped == 1
    assert test_summary.total == 43


def test_parse_pytest_summary_passed_only():
    """Handles pytest summary with only passed tests."""
    content = """================ 100 passed in 12.5s ================\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        _, test_summary, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert test_summary is not None
    assert test_summary.passed == 100
    assert test_summary.failed == 0
    assert test_summary.skipped == 0


def test_parse_no_test_summary():
    """Returns None when no pytest summary found."""
    content = """mypy: success\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        _, test_summary, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert test_summary is None


def test_parse_missing_file():
    """Returns empty results for missing log file."""
    issues, test_summary, build_status = parse_log('/nonexistent/path.log')
    assert issues == []
    assert test_summary is None
    assert build_status == 'FAILURE'


def test_parse_empty_file():
    """Returns empty results for empty log file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write('')
        f.flush()
        issues, test_summary, build_status = parse_log(f.name)
        Path(f.name).unlink()

    assert issues == []
    assert test_summary is None


def test_parse_mixed_output():
    """Handles log with mypy, ruff, and pytest output together."""
    content = """src/main.py:10: error: Argument has incompatible type
src/main.py:15:1: E501 Line too long
FAILED test/test_main.py::test_foo - assert False
================ 5 passed, 1 failed in 2.1s ================
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, test_summary, build_status = parse_log(f.name)
        Path(f.name).unlink()

    categories = [i.category for i in issues]
    assert 'type_error' in categories
    assert 'lint_error' in categories
    assert 'test_failure' in categories
    assert test_summary is not None
    assert test_summary.failed == 1


def test_parse_issues_are_issue_instances():
    """All returned issues are Issue dataclass instances."""
    content = """src/main.py:10: error: Bad type\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    for issue in issues:
        assert isinstance(issue, Issue)


# =============================================================================
# End-to-end regression coverage for the confirmed live failure (ANSI colour +
# failed-before-passed summary ordering), driven through the registry path.
# =============================================================================

# ANSI SGR escape sequences the confirmed live pytest run emitted into the
# captured log. Colour wraps the FAILED marker and each summary count.
_RED = '\x1b[31m'
_GREEN = '\x1b[32m'
_BOLD = '\x1b[1m'
_RESET = '\x1b[0m'


def test_colored_live_failure_end_to_end_via_registry():
    """Reproduces the confirmed live failure end-to-end through the registry.

    An ANSI-coloured log with a coloured FAILED line and a coloured
    ``1 failed, 10308 passed`` summary (failed-before-passed ordering) must,
    when parsed end-to-end through the registry path (``parse_log`` ->
    ``_REGISTRY.parse_multi``): (a) detect the failing tool at the registry
    content-check under colour, and (b) yield a populated ``errors[]`` row with
    ``failed=1`` — never the empty-errors / failed=0 contradiction the raw
    (un-stripped) parser produced.
    """
    # Arrange: a coloured FAILED line plus a coloured failed-before-passed summary.
    colored = (
        f'{_RED}FAILED{_RESET} test/test_foo.py::test_bar - '
        'AssertionError: assert 1 == 2\n'
        f'{_BOLD}==================={_RESET} '
        f'{_RED}1 failed{_RESET}, {_GREEN}10308 passed{_RESET} '
        f'{_BOLD}in 45.67s ==================={_RESET}\n'
    )

    with _temp_log(colored) as path:
        # Act: registry content-check detection under colour + end-to-end parse.
        detected_tool = _REGISTRY.detect_tool_type(read_log_text(path), '')
        issues, test_summary, build_status = parse_log(path)

    # Assert (a): the registry content-check detects pytest under colour.
    assert detected_tool == 'pytest'

    # Assert (b): a populated errors[] row with the failing test surfaced.
    assert build_status == 'FAILURE'
    assert len(issues) >= 1
    assert all(issue.severity == 'error' for issue in issues)
    assert any(issue.category == 'test_failure' for issue in issues)
    assert any(issue.file == 'test/test_foo.py' for issue in issues)

    # Assert (b): failed count is 1 — no status/errors[] contradiction.
    assert test_summary is not None
    assert test_summary.failed == 1
    assert test_summary.passed == 10308


def test_registry_read_site_strips_colour_before_detection():
    """Proves the registry read site (not only the tool parsers) is stripped.

    A coloured FAILED line with no summary line is detectable ONLY once the
    registry's own read strips the colour: the naive ``_has_pytest_output``
    content-check returns False against the raw coloured content (the summary
    fallback cannot fire without a summary line, and ``FAILED `` is broken by
    the colour reset), so a registry read that skipped stripping would never
    route to the pytest parser and would leave ``errors[]`` empty. A populated
    result therefore proves the registry read site itself applied the strip.
    """
    # Arrange: a coloured FAILED line only — no pytest summary line.
    colored = (
        f'{_RED}FAILED{_RESET} test/test_foo.py::test_bar - '
        'AssertionError: assert 1 == 2\n'
    )

    # Assert the raw coloured content defeats the naive content-check, so the
    # end-to-end result can only succeed if the registry read stripped colour.
    assert _has_pytest_output(colored) is False

    with _temp_log(colored) as path:
        # Act: parse end-to-end through the registry path.
        issues, _, build_status = parse_log(path)

    # Assert: detection + extraction succeeded because the registry read stripped.
    assert build_status == 'FAILURE'
    assert len(issues) >= 1
    assert any(issue.category == 'test_failure' for issue in issues)
    assert any(issue.file == 'test/test_foo.py' for issue in issues)


def test_summary_extraction_is_order_independent():
    """Both summary count orderings yield identical passed/failed/skipped counts.

    pytest renders its summary counts in a tool-determined order — a
    passing-dominant run shows ``10308 passed, 1 failed`` while a
    failing-dominant run shows ``1 failed, 10308 passed``. Extraction must be
    independent of that ordering.
    """
    # Arrange: the same counts rendered in both orderings.
    passed_first = '=============== 10308 passed, 1 failed in 45.67s ===============\n'
    failed_first = '=============== 1 failed, 10308 passed in 45.67s ===============\n'

    # Act: parse each ordering end-to-end.
    with _temp_log(passed_first) as path_a:
        _, summary_a, _ = parse_log(path_a)
    with _temp_log(failed_first) as path_b:
        _, summary_b, _ = parse_log(path_b)

    # Assert: both orderings extracted the same counts.
    assert summary_a is not None
    assert summary_b is not None
    assert summary_a.passed == summary_b.passed == 10308
    assert summary_a.failed == summary_b.failed == 1
    assert summary_a.skipped == summary_b.skipped == 0
    assert (summary_a.passed, summary_a.failed, summary_a.skipped) == (
        summary_b.passed,
        summary_b.failed,
        summary_b.skipped,
    )
