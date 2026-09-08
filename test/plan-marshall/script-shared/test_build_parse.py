#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for build_parse.py module."""

import json
from pathlib import Path

import _build_parse as _build_parse_mod
import pytest

MODE_ACTIONABLE = _build_parse_mod.MODE_ACTIONABLE
MODE_ERRORS = _build_parse_mod.MODE_ERRORS
MODE_STRUCTURED = _build_parse_mod.MODE_STRUCTURED
SEVERITY_ERROR = _build_parse_mod.SEVERITY_ERROR
SEVERITY_WARNING = _build_parse_mod.SEVERITY_WARNING
Issue = _build_parse_mod.Issue
UnitTestSummary = _build_parse_mod.UnitTestSummary
filter_warnings = _build_parse_mod.filter_warnings
generate_summary_from_issues = _build_parse_mod.generate_summary_from_issues
is_warning_accepted = _build_parse_mod.is_warning_accepted
load_acceptable_warnings = _build_parse_mod.load_acceptable_warnings
partition_issues = _build_parse_mod.partition_issues
read_log_text = _build_parse_mod.read_log_text
strip_ansi = _build_parse_mod.strip_ansi


def test_severity_constants():
    """Severity constants have expected values."""
    assert SEVERITY_ERROR == 'error'
    assert SEVERITY_WARNING == 'warning'


def test_mode_constants():
    """Mode constants have expected values."""
    assert MODE_ACTIONABLE == 'actionable'
    assert MODE_STRUCTURED == 'structured'
    assert MODE_ERRORS == 'errors'


def test_issue_creation_minimal():
    """Issue can be created with minimal fields."""
    issue = Issue(file='Main.java', line=15, message='cannot find symbol', severity=SEVERITY_ERROR)
    assert issue.file == 'Main.java'
    assert issue.line == 15
    assert issue.message == 'cannot find symbol'
    assert issue.severity == SEVERITY_ERROR
    assert issue.category is None
    assert issue.stack_trace is None
    assert issue.accepted is False


def test_issue_creation_full():
    """Issue can be created with all fields."""
    issue = Issue(
        file='Test.java',
        line=42,
        message='test failed',
        severity=SEVERITY_ERROR,
        category='test_failure',
        stack_trace='at Test.method(Test.java:42)',
        accepted=True,
    )
    assert issue.category == 'test_failure'
    assert issue.stack_trace == 'at Test.method(Test.java:42)'
    assert issue.accepted is True


def test_issue_none_file_and_line():
    """Issue can have None file and line."""
    issue = Issue(file=None, line=None, message='general warning', severity=SEVERITY_WARNING)
    assert issue.file is None
    assert issue.line is None


def test_issue_to_dict_minimal():
    """to_dict returns minimal required fields."""
    issue = Issue(file='Main.java', line=15, message='error', severity=SEVERITY_ERROR)
    result = issue.to_dict()

    assert result['file'] == 'Main.java'
    assert result['line'] == 15
    assert result['message'] == 'error'
    assert result['severity'] == SEVERITY_ERROR
    assert 'category' not in result
    assert 'stack_trace' not in result
    assert 'accepted' not in result


def test_issue_to_dict_with_category():
    """to_dict includes category when present."""
    issue = Issue(file='Main.java', line=15, message='error', severity=SEVERITY_ERROR, category='compilation')
    result = issue.to_dict()
    assert result['category'] == 'compilation'


def test_issue_to_dict_with_stack_trace():
    """to_dict includes stack_trace when present."""
    issue = Issue(
        file='Test.java', line=42, message='test failed', severity=SEVERITY_ERROR, stack_trace='stack trace here'
    )
    result = issue.to_dict()
    assert result['stack_trace'] == 'stack trace here'


def test_issue_to_dict_with_accepted():
    """to_dict includes accepted when True."""
    issue = Issue(file='Main.java', line=15, message='warning', severity=SEVERITY_WARNING, accepted=True)
    result = issue.to_dict()
    assert result['accepted'] is True


def test_issue_to_dict_without_accepted_false():
    """to_dict excludes accepted when False."""
    issue = Issue(file='Main.java', line=15, message='warning', severity=SEVERITY_WARNING, accepted=False)
    result = issue.to_dict()
    assert 'accepted' not in result


def test_test_summary_creation():
    """UnitTestSummary can be created with all fields."""
    summary = UnitTestSummary(passed=10, failed=2, skipped=1, total=13)
    assert summary.passed == 10
    assert summary.failed == 2
    assert summary.skipped == 1
    assert summary.total == 13


def test_test_summary_to_dict():
    """to_dict returns all fields."""
    summary = UnitTestSummary(passed=10, failed=2, skipped=1, total=13)
    result = summary.to_dict()

    assert result['passed'] == 10
    assert result['failed'] == 2
    assert result['skipped'] == 1
    assert result['total'] == 13


def test_test_summary_zero_values():
    """UnitTestSummary handles zero values."""
    summary = UnitTestSummary(passed=0, failed=0, skipped=0, total=0)
    result = summary.to_dict()
    assert all(v == 0 for v in result.values())


# =============================================================================
# UnitTestSummary.executed — the EXECUTED count, distinct from the collected one
# =============================================================================
#
# ``executed`` is ``passed + failed``. ``total`` additionally counts SKIPPED
# tests, so the two answer different questions and diverge exactly when it
# matters: a summary that is all skips has a non-zero ``total`` and executed
# nothing. Publishing ``total`` under a name that says "executed" is what let a
# skips-only run present itself as evidence that the suite ran.


def test_executed_is_passed_plus_failed():
    """The executed count sums the two outcomes that required running a test."""
    summary = UnitTestSummary(passed=10, failed=2, skipped=1, total=13)

    assert summary.executed == 12


def test_executed_excludes_skips_so_it_differs_from_total():
    """A skips-bearing summary's ``executed`` is strictly below its ``total``.

    The discriminating case, asserted with a summary whose two values cannot
    coincide: were ``executed`` ever redefined as ``total``, this is the shape
    that catches it. A summary with no skips would not — both would read 12.
    """
    summary = UnitTestSummary(passed=10, failed=2, skipped=1, total=13)

    assert summary.executed == 12
    assert summary.total == 13
    assert summary.executed != summary.total


def test_a_skips_only_summary_executed_nothing():
    """``2 passed, 9 skipped`` executes 2; all-skips executes 0.

    The second half is the false-green case in full: eleven tests collected,
    every one of them skipped, and the honest executed count is zero — even
    though ``total`` reports eleven.
    """
    partial = UnitTestSummary(passed=2, failed=0, skipped=9, total=11)
    all_skipped = UnitTestSummary(passed=0, failed=0, skipped=11, total=11)

    assert partial.executed == 2
    assert all_skipped.executed == 0
    assert all_skipped.total == 11


def test_executed_counts_a_failing_run_as_executed():
    """A test that FAILED still ran, so it counts toward ``executed``.

    Guards the opposite error from the skip one: defining ``executed`` as
    ``passed`` alone would report zero for a run that executed every test and
    failed them, and a zero there suppresses the reconciliation the count gates.
    """
    summary = UnitTestSummary(passed=0, failed=7, skipped=0, total=7)

    assert summary.executed == 7


def test_executed_is_not_serialised_by_to_dict():
    """``executed`` is derived, and the serialised summary shape is unchanged.

    The wire/JSON test-summary shape is a consumed contract and ``executed`` is
    computable from the fields already in it, so the property exists to let an
    emission site NAME what it means rather than to add a field.
    """
    summary = UnitTestSummary(passed=10, failed=2, skipped=1, total=13)

    assert set(summary.to_dict()) == {'passed', 'failed', 'skipped', 'total'}


def _use_plan_base_dir(monkeypatch, tmpdir: str) -> None:
    """Point ``PLAN_BASE_DIR`` at ``tmpdir`` for the rest of the test.

    Through ``monkeypatch`` rather than a hand-rolled save/assign/restore around
    ``os.environ``: the autouse ``_plan_base_dir_sandbox`` fixture already owns
    this variable for every test, so a manual restore writes back whatever it
    happened to read — the sandbox's own value — and the two mechanisms agree
    only by ordering luck. One owner, one unwind.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', tmpdir)


#: ``(run-configuration.json content, patterns loaded for 'maven')``. ``None``
#: means the file is never written, which is a different absence from a file
#: that exists and holds no maven section — both must yield the empty list.
_ACCEPTABLE_WARNINGS_CASES = [
    (None, []),
    (json.dumps({'npm': {'acceptable_warnings': ['pattern']}}), []),
    (json.dumps({'maven': {'other_key': 'value'}}), []),
    (
        json.dumps({'maven': {'acceptable_warnings': ['unchecked', 'deprecated', '^.*raw type.*$']}}),
        ['unchecked', 'deprecated', '^.*raw type.*$'],
    ),
    ('not valid json', []),
]

_ACCEPTABLE_WARNINGS_IDS = [
    'no-config-file-at-all',
    'config-without-a-maven-section',
    'maven-section-without-the-key',
    'maven-patterns-are-loaded-in-order',
    'config-file-is-not-json',
]


@pytest.mark.parametrize(
    'config_text,expected', _ACCEPTABLE_WARNINGS_CASES, ids=_ACCEPTABLE_WARNINGS_IDS
)
def test_load_acceptable_warnings(monkeypatch, tmp_path: Path, config_text, expected):
    _use_plan_base_dir(monkeypatch, str(tmp_path))
    if config_text is not None:
        (tmp_path / 'run-configuration.json').write_text(config_text)

    assert load_acceptable_warnings(str(tmp_path), 'maven') == expected


#: ``(warning message, acceptance patterns, accepted?)``. A pattern starting
#: with ``^`` is treated as a regex and anything else as a substring, and both
#: match case-insensitively — so each spelling carries a matching row, a
#: differently-cased row, and a non-matching row.
_WARNING_ACCEPTANCE_CASES = [
    ('some warning', [], False),
    ('uses unchecked or unsafe operations', ['unchecked'], True),
    ('Uses UNCHECKED operations', ['unchecked'], True),
    ('some warning', ['unchecked'], False),
    ('raw type usage in Main.java', ['^.*raw type.*$'], True),
    ('RAW TYPE usage', ['^.*raw type.*$'], True),
    ('some warning', ['^.*unchecked.*$'], False),
    ('some warning', ['^(invalid'], False),
    ('deprecated API', ['unchecked', 'deprecated', 'raw type'], True),
]

_WARNING_ACCEPTANCE_IDS = [
    'no-patterns-accepts-nothing',
    'substring-match',
    'substring-match-is-case-insensitive',
    'substring-that-does-not-match',
    'regex-match',
    'regex-match-is-case-insensitive',
    'regex-that-does-not-match',
    'unparseable-regex-is-skipped',
    'any-one-of-several-patterns-matching-is-enough',
]


@pytest.mark.parametrize(
    'message,patterns,expected', _WARNING_ACCEPTANCE_CASES, ids=_WARNING_ACCEPTANCE_IDS
)
def test_is_warning_accepted(message: str, patterns: list[str], expected: bool):
    warning = Issue(None, None, message, SEVERITY_WARNING)

    assert bool(is_warning_accepted(warning, patterns)) is expected


#: The two-warning input every mode row is filtered from: one message the
#: pattern accepts and one it does not.
_MIXED_WARNING_MESSAGES = ['unchecked operation', 'other warning']

#: ``(mode, the messages that survive)``. Stating the surviving MESSAGES rather
#: than a count is what makes the actionable row assert WHICH warning was
#: dropped, not merely that one was.
_FILTER_MODE_CASES = [
    (MODE_ACTIONABLE, ['other warning']),
    (MODE_STRUCTURED, ['unchecked operation', 'other warning']),
    (MODE_ERRORS, []),
]

_FILTER_MODE_IDS = [
    'actionable-drops-the-accepted-warning',
    'structured-keeps-both',
    'errors-keeps-none',
]


@pytest.mark.parametrize('mode,expected_messages', _FILTER_MODE_CASES, ids=_FILTER_MODE_IDS)
def test_filter_warnings_per_mode(mode: str, expected_messages: list[str]):
    warnings = [Issue(None, None, message, SEVERITY_WARNING) for message in _MIXED_WARNING_MESSAGES]

    result = filter_warnings(warnings, ['unchecked'], mode)

    assert [warning.message for warning in result] == expected_messages


def test_filter_warnings_default_mode():
    """Actionable is the default mode."""
    warnings = [Issue(None, None, 'unchecked', SEVERITY_WARNING)]
    patterns = ['unchecked']

    result = filter_warnings(warnings, patterns)
    assert len(result) == 0


def test_filter_warnings_structured_marks_accepted():
    """Structured mode marks accepted warnings."""
    warnings = [
        Issue(None, None, 'unchecked operation', SEVERITY_WARNING),
        Issue(None, None, 'other warning', SEVERITY_WARNING),
    ]
    patterns = ['unchecked']

    result = filter_warnings(warnings, patterns, MODE_STRUCTURED)
    accepted = [w for w in result if w.accepted]
    not_accepted = [w for w in result if not w.accepted]

    assert len(accepted) == 1
    assert accepted[0].message == 'unchecked operation'
    assert len(not_accepted) == 1
    assert not_accepted[0].message == 'other warning'


def test_filter_warnings_preserves_fields():
    """Structured mode preserves all Issue fields."""
    warning = Issue(
        file='Main.java',
        line=15,
        message='unchecked',
        severity=SEVERITY_WARNING,
        category='type_safety',
        stack_trace='trace',
    )

    result = filter_warnings([warning], ['unchecked'], MODE_STRUCTURED)
    assert len(result) == 1
    assert result[0].file == 'Main.java'
    assert result[0].line == 15
    assert result[0].category == 'type_safety'
    assert result[0].stack_trace == 'trace'


#: ``(severities to build issues from, expected error count, expected warning
#: count)``. The severity homogeneity of each partition is asserted on every row
#: rather than only on the mixed one, since it is the property the split exists
#: to produce.
_PARTITION_CASES = [
    ([], 0, 0),
    ([SEVERITY_ERROR, SEVERITY_ERROR], 2, 0),
    ([SEVERITY_WARNING, SEVERITY_WARNING], 0, 2),
    ([SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_WARNING], 2, 2),
]

_PARTITION_IDS = ['no-issues', 'errors-only', 'warnings-only', 'mixed']


@pytest.mark.parametrize(
    'severities,expected_errors,expected_warnings', _PARTITION_CASES, ids=_PARTITION_IDS
)
def test_partition_issues(severities: list[str], expected_errors: int, expected_warnings: int):
    issues = [
        Issue(None, None, f'issue {index}', severity)
        for index, severity in enumerate(severities)
    ]

    errors, warnings = partition_issues(issues)

    assert len(errors) == expected_errors
    assert len(warnings) == expected_warnings
    assert all(issue.severity == SEVERITY_ERROR for issue in errors)
    assert all(issue.severity == SEVERITY_WARNING for issue in warnings)


def test_partition_issues_preserves_order():
    """Preserves order within each partition."""
    issues = [
        Issue(None, None, 'error 1', SEVERITY_ERROR),
        Issue(None, None, 'error 2', SEVERITY_ERROR),
        Issue(None, None, 'warning 1', SEVERITY_WARNING),
    ]
    errors, warnings = partition_issues(issues)
    assert errors[0].message == 'error 1'
    assert errors[1].message == 'error 2'


def test_generate_summary_empty():
    """Returns zero counts for empty issues list."""
    summary = generate_summary_from_issues([])
    assert summary['total_issues'] == 0
    assert summary['total_errors'] == 0
    assert summary['total_warnings'] == 0


def test_generate_summary_all_categories():
    """Counts all categories dynamically based on what's present."""
    issues = [
        Issue(None, None, 'msg', SEVERITY_ERROR, category='compilation_error'),
        Issue(None, None, 'msg', SEVERITY_ERROR, category='test_failure'),
        Issue(None, None, 'msg', SEVERITY_WARNING, category='javadoc_warning'),
        Issue(None, None, 'msg', SEVERITY_WARNING, category='deprecation_warning'),
        Issue(None, None, 'msg', SEVERITY_WARNING, category='unchecked_warning'),
        Issue(None, None, 'msg', SEVERITY_ERROR, category='dependency_error'),
        Issue(None, None, 'msg', SEVERITY_WARNING, category='openrewrite_info'),
    ]
    summary = generate_summary_from_issues(issues)
    assert summary['total_issues'] == 7
    assert summary['total_errors'] == 3
    assert summary['total_warnings'] == 4
    assert summary['compilation_error'] == 1
    assert summary['test_failure'] == 1
    assert summary['javadoc_warning'] == 1
    assert summary['deprecation_warning'] == 1
    assert summary['unchecked_warning'] == 1
    assert summary['dependency_error'] == 1
    assert summary['openrewrite_info'] == 1


def test_generate_summary_other_categories():
    """Dynamic categories — any category name is tracked."""
    issues = [
        Issue(None, None, 'msg', SEVERITY_ERROR, category='unknown_error_type'),
        Issue(None, None, 'msg', SEVERITY_WARNING, category='unknown_warning_type'),
    ]
    summary = generate_summary_from_issues(issues)
    assert summary['unknown_error_type'] == 1
    assert summary['unknown_warning_type'] == 1
    assert summary['total_issues'] == 2
    assert summary['total_errors'] == 1
    assert summary['total_warnings'] == 1


# =============================================================================
# STRIP layer: strip_ansi and read_log_text
# =============================================================================


#: ``(text as read from a log, text after stripping)``. The last row is the
#: matched control: text carrying no escape sequence must come back untouched,
#: without which a stripper that mangled ordinary output would still pass.
_STRIP_ANSI_CASES = [
    (
        '\x1b[31mFAILED\x1b[0m tests/test_foo.py::test_bar',
        'FAILED tests/test_foo.py::test_bar',
    ),
    (
        '\x1b[31m1 failed\x1b[0m, \x1b[32m10308 passed\x1b[0m in 42.00s',
        '1 failed, 10308 passed in 42.00s',
    ),
    ('1 failed, 10308 passed in 42.00s', '1 failed, 10308 passed in 42.00s'),
]

_STRIP_ANSI_IDS = [
    'coloured-failure-line',
    'coloured-summary-line',
    'text-with-no-escape-sequences',
]


@pytest.mark.parametrize('text,expected', _STRIP_ANSI_CASES, ids=_STRIP_ANSI_IDS)
def test_strip_ansi(text: str, expected: str):
    """strip_ansi removes ANSI SGR colour codes and leaves everything else alone."""
    result = strip_ansi(text)

    assert result == expected
    assert '\x1b' not in result


def test_read_log_text_strips_ansi_from_file(tmp_path):
    """read_log_text reads a file AND strips ANSI codes in one call."""
    # Arrange
    log = tmp_path / 'colored.log'
    log.write_text('\x1b[31m1 failed\x1b[0m, \x1b[32m10308 passed\x1b[0m\n', encoding='utf-8')

    # Act
    content = read_log_text(log)

    # Assert
    assert content == '1 failed, 10308 passed\n'
    assert '\x1b' not in content


def test_read_log_text_clean_file_unchanged(tmp_path):
    """read_log_text returns a colour-free log file unchanged."""
    # Arrange
    log = tmp_path / 'clean.log'
    original = 'FAILED tests/test_foo.py::test_bar\n1 failed, 3 passed\n'
    log.write_text(original, encoding='utf-8')

    # Act
    content = read_log_text(log)

    # Assert
    assert content == original
