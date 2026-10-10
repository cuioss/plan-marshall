#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for maven parse functionality (internal module testing).

Note: These tests import internal modules directly for detailed testing.
Public API tests should use maven.py CLI instead.
"""

# Direct imports - conftest sets up PYTHONPATH (cross-skill)
import re
from pathlib import Path
from typing import NamedTuple

import pytest
from _build_parse import (
    POPULATION_MEASURED,
    POPULATION_UNMEASURED,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Issue,
    UnitTestSummary,
    categorize_issue,
)

from conftest import get_script_path, load_script_module, run_script

_maven_cmd_parse_mod = load_script_module('plan-marshall', 'build-maven', '_maven_cmd_parse.py', '_maven_cmd_parse')

parse_log = _maven_cmd_parse_mod.parse_log
MAVEN_PATTERNS = _maven_cmd_parse_mod.MAVEN_PATTERNS

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
    """Exactly the fixture's genuine javac deprecation lines are categorised as deprecation."""
    # Arrange
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    genuine = [line for line in log_file.read_text(encoding='utf-8').splitlines() if '[deprecation]' in line]
    assert len(genuine) == 1, 'the failure fixture carries exactly one genuine javac deprecation line'

    # Act
    issues, test_summary, build_status = parse_log(log_file)

    # Assert
    deprecation = [i for i in issues if i.category == 'deprecation_warning']
    assert len(deprecation) == len(genuine)
    assert deprecation[0].severity == SEVERITY_WARNING
    assert '[deprecation]' in deprecation[0].message


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
    assert data.get('status') == 'error', f'BUILD SUCCESS with errored tests must report error, not success: {data}'


# =============================================================================
# Summing every Surefire / Failsafe summary block
# =============================================================================
#
# A Maven log carries one summary block per module and per test plugin, so the
# summary must be the SUM of every block, never the last one. The expected values
# are derived from the blocks each fixture actually carries instead of being
# pinned, and every summed case first proves its fixture holds more than one
# block — a one-block fixture cannot tell "sum every block" from "keep the last".
#
# The fixture reader below is deliberately simpler than the parser: it treats a
# count line without ``Time elapsed`` as a summary and names its runner from the
# nearest preceding execution header. That holds for every sequential fixture
# here; the parser's own ambiguity rules are exercised by the quiet and parallel
# cases, which state their expectations directly.

_COUNT_LINE = re.compile(r'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)')
_EXECUTION_HEADER = re.compile(r'---\s+(\S+):\S+:\S+\s.*@.*---')


class _CountLine(NamedTuple):
    """One ``Tests run:`` line of a fixture, with the runner whose execution encloses it."""

    runner: str | None
    per_class: bool
    total: int
    failed: int
    skipped: int


def _count_lines(log_file: Path) -> list[_CountLine]:
    """Every count line of the fixture, in log order."""
    runner: str | None = None
    rows: list[_CountLine] = []
    for line in log_file.read_text(encoding='utf-8').splitlines():
        header = _EXECUTION_HEADER.search(line)
        if header:
            plugin = header.group(1)
            runner = 'surefire' if 'surefire' in plugin else 'failsafe' if 'failsafe' in plugin else None
            continue
        match = _COUNT_LINE.search(line)
        if match:
            total, failures, errors, skipped = (int(group) for group in match.groups())
            rows.append(_CountLine(runner, 'Time elapsed' in line, total, failures + errors, skipped))
    return rows


def _summary_blocks(log_file: Path) -> list[_CountLine]:
    """The fixture's summary lines — every count line that is not a per-class line."""
    return [row for row in _count_lines(log_file) if not row.per_class]


def _executed_by_runner(blocks: list[_CountLine]) -> dict[str, int]:
    """Executed count (total minus skipped) per runner, summed over the blocks."""
    executed: dict[str, int] = {}
    for block in blocks:
        assert block.runner is not None, 'a sequential fixture names the runner of every summary block'
        executed[block.runner] = executed.get(block.runner, 0) + block.total - block.skipped
    return executed


#: ``(fixture, the runners its summary blocks belong to)``.
_SUMMED_FIXTURE_CASES = [
    ('maven-verify-surefire-failsafe.log', {'surefire', 'failsafe'}),
    ('maven-reactor-three-modules.log', {'surefire'}),
    ('maven-verify-failsafe-zero.log', {'surefire', 'failsafe'}),
]

_SUMMED_FIXTURE_IDS = [
    'one-module-surefire-then-failsafe',
    'three-module-reactor',
    'surefire-then-failsafe-of-zero',
]


@pytest.mark.parametrize('fixture_name,runners', _SUMMED_FIXTURE_CASES, ids=_SUMMED_FIXTURE_IDS)
def test_parse_log_sums_every_summary_block(fixture_name: str, runners: set[str]):
    # Arrange
    log_file = TEST_DATA_DIR / fixture_name
    blocks = _summary_blocks(log_file)
    assert len(blocks) > 1, f'{fixture_name} must carry more than one summary block'
    assert {block.runner for block in blocks} == runners
    expected_total = sum(block.total for block in blocks)
    expected_failed = sum(block.failed for block in blocks)
    expected_skipped = sum(block.skipped for block in blocks)
    # Non-vacuity: keeping only the last block must give a different total, or
    # this case could not catch a regression to last-match parsing.
    assert blocks[-1].total != expected_total

    # Act
    _, summary, _ = parse_log(log_file)

    # Assert
    assert summary is not None
    assert summary.population == POPULATION_MEASURED
    assert summary.total == expected_total
    assert summary.failed == expected_failed
    assert summary.skipped == expected_skipped
    assert summary.passed == expected_total - expected_failed - expected_skipped
    assert summary.by_runner == _executed_by_runner(blocks)


def test_parse_log_failsafe_block_of_zero_still_names_its_runner():
    """A Failsafe execution that ran no test is reported as ``failsafe: 0``.

    Absent and zero are different facts: an absent runner did not execute at all,
    a zero runner executed and found nothing to run.
    """
    _, summary, _ = parse_log(TEST_DATA_DIR / 'maven-verify-failsafe-zero.log')

    assert summary is not None
    assert summary.by_runner is not None
    assert summary.by_runner['failsafe'] == 0


def test_parse_log_quiet_log_without_results_marker_is_unmeasured():
    """A quiet (``-q``) log drops the ``[INFO] Results:`` marker, so its summary
    line cannot be told from any other count line — the summary is unmeasured,
    while the failure it carries stays visible to the truthful-status check."""
    # Arrange
    log_file = TEST_DATA_DIR / 'maven-quiet-unmeasured.log'
    assert 'Results:' not in log_file.read_text(encoding='utf-8')
    summary_shaped = [row for row in _count_lines(log_file) if not row.per_class]
    assert summary_shaped, 'the quiet fixture must carry a summary-shaped count line'

    # Act
    _, summary, _ = parse_log(log_file)

    # Assert
    assert summary is not None
    assert summary.population == POPULATION_UNMEASURED
    assert summary.failed > 0
    assert summary.failed == sum(row.failed for row in summary_shaped)
    assert summary.total == sum(row.total for row in summary_shaped)
    assert summary.by_runner is None


_PARALLEL_LOG = TEST_DATA_DIR / 'maven-parallel-verify.log'
_PARALLEL_BANNER = 'MultiThreadedBuilder'


def test_parse_log_parallel_build_keeps_the_sum_and_omits_by_runner():
    # Arrange
    assert _PARALLEL_BANNER in _PARALLEL_LOG.read_text(encoding='utf-8')
    blocks = _summary_blocks(_PARALLEL_LOG)
    assert len(blocks) > 1, 'the parallel fixture must carry more than one summary block'

    # Act
    _, summary, _ = parse_log(_PARALLEL_LOG)

    # Assert
    assert summary is not None
    assert summary.population == POPULATION_MEASURED
    assert summary.total == sum(block.total for block in blocks)
    assert summary.skipped == sum(block.skipped for block in blocks)
    assert summary.by_runner is None


def test_control_parallel_log_without_the_banner_reports_by_runner(tmp_path):
    """CONTROL: the banner, not the log's shape, is what withholds ``by_runner``.

    The same interleaved log with the banner removed is attributed by nearest
    header — and the attribution under-counts, because an interleaved compiler
    header sits between one module's Surefire header and its summary. That
    under-count is exactly why a parallel build must not publish the breakdown.
    """
    # Arrange
    sequential = [
        line for line in _PARALLEL_LOG.read_text(encoding='utf-8').splitlines() if _PARALLEL_BANNER not in line
    ]
    log_file = tmp_path / 'parallel-without-banner.log'
    log_file.write_text('\n'.join(sequential) + '\n', encoding='utf-8')

    # Act
    _, summary, _ = parse_log(log_file)

    # Assert
    assert summary is not None
    assert summary.by_runner is not None
    assert sum(summary.by_runner.values()) < summary.executed


#: ``(plugin token in the execution header, goal, runner it attributes to)``.
#: Maven 3.8 prints the long ``maven-*-plugin`` token, Maven 3.9 / 4 the short one.
_HEADER_FORM_CASES = [
    ('maven-surefire-plugin', 'test', 'surefire'),
    ('surefire', 'test', 'surefire'),
    ('maven-failsafe-plugin', 'integration-test', 'failsafe'),
    ('failsafe', 'integration-test', 'failsafe'),
]

_HEADER_FORM_IDS = [
    'maven-3.8-long-surefire',
    'maven-3.9-and-4-short-surefire',
    'maven-3.8-long-failsafe',
    'maven-3.9-and-4-short-failsafe',
]


@pytest.mark.parametrize('plugin,goal,runner', _HEADER_FORM_CASES, ids=_HEADER_FORM_IDS)
def test_parse_log_execution_header_forms_attribute_to_their_runner(tmp_path, plugin: str, goal: str, runner: str):
    # Arrange
    log_file = tmp_path / 'header-form.log'
    log_file.write_text(
        f'[INFO] --- {plugin}:3.5.2:{goal} (default-{goal}) @ core ---\n'
        '[WARNING] Tests run: 5, Failures: 0, Errors: 0, Skipped: 1, Time elapsed: 0.042 s -- in probe.CoreTest\n'
        '[INFO]\n'
        '[INFO] Results:\n'
        '[INFO]\n'
        '[WARNING] Tests run: 5, Failures: 0, Errors: 0, Skipped: 1\n',
        encoding='utf-8',
    )

    # Act
    _, summary, _ = parse_log(log_file)

    # Assert
    assert summary is not None
    assert summary.by_runner == {runner: 4}


# =============================================================================
# Bracketed javac tags are matched as literal text
# =============================================================================
#
# `categorize_issue` treats any pattern carrying a regex metacharacter as a regex,
# so an unescaped `[deprecation]` is a character class matching any one of its
# letters — and nearly every Maven line contains one of them.

#: ``(message, category it must receive under MAVEN_PATTERNS)``.
_JAVAC_TAG_CASES = [
    ('[deprecation] foo() in Bar has been deprecated', 'deprecation_warning'),
    ('Bar.java:[12,5] [deprecation] foo() in Bar', 'deprecation_warning'),
    ('[unchecked] unchecked call to add(E) as a member of the raw type List', 'unchecked_warning'),
]

_JAVAC_TAG_IDS = [
    'deprecation-tag-with-deprecated-phrase',
    'deprecation-tag-alone',
    'unchecked-tag',
]


def test_surefire_goal_failure_is_not_a_deprecation_warning():
    """The goal-failure line carries no javac tag, so it is not a deprecation warning."""
    category = categorize_issue('Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin', MAVEN_PATTERNS)

    assert category != 'deprecation_warning'


@pytest.mark.parametrize('message,expected', _JAVAC_TAG_CASES, ids=_JAVAC_TAG_IDS)
def test_genuine_javac_tag_lines_keep_their_category(message: str, expected: str):
    assert categorize_issue(message, MAVEN_PATTERNS) == expected


def _unescaped_brackets(pattern: str) -> list[str]:
    """Every ``[`` / ``]`` in the pattern that is not preceded by an escaping backslash."""
    found: list[str] = []
    escaped = False
    for char in pattern:
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif char in '[]':
            found.append(char)
    return found


def test_control_unescaped_bracket_detector_flags_a_bare_tag():
    """CONTROL: the detector flags the bare tag and passes the escaped one, so the
    population test below cannot pass by never seeing a bracket."""
    assert _unescaped_brackets('[deprecation]') == ['[', ']']
    assert _unescaped_brackets(r'\[deprecation\]') == []


def test_no_maven_pattern_carries_an_unescaped_bracket():
    # Arrange
    patterns = [pattern for category_patterns in MAVEN_PATTERNS.values() for pattern in category_patterns]
    assert any('[' in pattern for pattern in patterns), 'MAVEN_PATTERNS must carry a bracketed tag for this to bite'

    # Act
    offenders = [pattern for pattern in patterns if _unescaped_brackets(pattern)]

    # Assert
    assert offenders == []


# =============================================================================
# Maven's failure epilogue and passing test-count lines are not issues
# =============================================================================
#
# Both fixtures reproduce a fail-at-end run of the same three-module reactor: `a`
# passes with one skipped test, `b` has one failing Surefire test, `c` does not
# compile. The expected diagnostics are written out rather than derived from the
# parser, so a parser that drops a real diagnostic fails here as surely as one
# that files an epilogue line.

_MAVEN3_EPILOGUE_LOG = TEST_DATA_DIR / 'maven-failure-epilogue.log'
_MAVEN4_EPILOGUE_LOG = TEST_DATA_DIR / 'maven4-failure-epilogue.log'

_SUREFIRE_GOAL_FAILURE = (
    'Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin:3.5.2:test (default-test) '
    'on project b: There are test failures.'
)
_COMPILER_GOAL_FAILURE = (
    'Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.13.0:compile (default-compile) '
    'on project c: Compilation failure'
)
_COMPILER_ERROR = '/home/dev/probe/c/src/main/java/probe/c/Broken.java:[5,9] cannot find symbol'

#: The Maven 3.9.16 fixture's real diagnostics, in log order (the repeated compiler
#: error in the goal-failure block is deduplicated).
_MAVEN3_DIAGNOSTICS = [
    'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.031 s <<< FAILURE! -- in probe.b.BTest',
    'probe.b.BTest.fails -- Time elapsed: 0.012 s  <<< FAILURE!',
    'Failures:',
    'BTest.fails:10 expected: <1> but was: <2>',
    'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0',
    'COMPILATION ERROR :',
    _COMPILER_ERROR,
    _SUREFIRE_GOAL_FAILURE,
    _COMPILER_GOAL_FAILURE,
    'symbol:   class Missing',
    'location: class probe.c.Broken',
]

#: The Maven 4.0.0-rc-7 fixture's real diagnostics, in log order.
_MAVEN4_DIAGNOSTICS = [
    'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.029 s <<< FAILURE! -- in probe.b.BTest',
    'probe.b.BTest.fails -- Time elapsed: 0.011 s  <<< FAILURE!',
    'Failures:',
    'BTest.fails:10 expected: <1> but was: <2>',
    'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0',
    'COMPILATION ERROR :',
    _COMPILER_ERROR,
    _SUREFIRE_GOAL_FAILURE,
    _COMPILER_GOAL_FAILURE,
    'symbol:   class Missing',
    'location: class probe.c.Broken',
]

#: The Maven 3 fixture's `[ERROR]` / `[WARNING]` lines that must never be filed.
_MAVEN3_NOT_FILED = [
    'Tests run: 2, Failures: 0, Errors: 0, Skipped: 1, Time elapsed: 0.041 s -- in probe.a.ATest',
    'Tests run: 2, Failures: 0, Errors: 0, Skipped: 1',
    'See /home/dev/probe/b/target/surefire-reports for the individual test results.',
    'See dump files (if any exist) [date].dump, [date]-jvmRun[N].dump and [date].dumpstream.',
    'To see the full stack trace of the errors, re-run Maven with the -e switch.',
    'Re-run Maven using the -X switch to enable full debug logging.',
    'For more information about the errors and possible solutions, please read the following articles:',
    '[Help 1] http://cwiki.apache.org/confluence/display/MAVEN/MojoFailureException',
    'After correcting the problems, you can resume the build with the command',
    'mvn <args> -rf :b',
]

#: The Maven 4 fixture's `[ERROR]` / `[WARNING]` lines that must never be filed.
_MAVEN4_NOT_FILED = [
    'Tests run: 2, Failures: 0, Errors: 0, Skipped: 1, Time elapsed: 0.044 s -- in probe.a.ATest',
    'Tests run: 2, Failures: 0, Errors: 0, Skipped: 1',
    'b .................................................. FAILURE [  0.953 s]',
    'c .................................................. FAILURE [  0.388 s]',
    'BUILD FAILURE',
    'See /home/dev/probe/b/target/surefire-reports for the individual test results.',
    'See dump files (if any exist) [date].dump, [date]-jvmRun[N].dump and [date].dumpstream.',
    "To see the full stack trace of the errors, re-run Maven with the '-e' switch",
    "Re-run Maven using the '-X' switch to enable verbose output",
    'For more information about the errors and possible solutions, please read the following articles:',
    '[Help 1] http://cwiki.apache.org/confluence/display/MAVEN/MojoFailureException',
    '[Help 2] http://cwiki.apache.org/confluence/display/MAVEN/CompilationFailureException',
    'After correcting the problems, you can resume the build with the command',
    'mvn [args] -r',
]

_EPILOGUE_FIXTURE_CASES = [
    (_MAVEN3_EPILOGUE_LOG, _MAVEN3_DIAGNOSTICS, _MAVEN3_NOT_FILED),
    (_MAVEN4_EPILOGUE_LOG, _MAVEN4_DIAGNOSTICS, _MAVEN4_NOT_FILED),
]

_EPILOGUE_FIXTURE_IDS = ['maven-3.9', 'maven-4']


def _logged_messages(log_file: Path) -> list[str]:
    """Every `[ERROR]` / `[WARNING]` line of the fixture with its level prefix stripped."""
    prefix = re.compile(r'^\[(?:ERROR|WARNING)\]\s*')
    return [
        prefix.sub('', line.strip())
        for line in log_file.read_text(encoding='utf-8').splitlines()
        if prefix.match(line.strip())
    ]


@pytest.mark.parametrize('log_file,diagnostics,not_filed', _EPILOGUE_FIXTURE_CASES, ids=_EPILOGUE_FIXTURE_IDS)
def test_failure_epilogue_is_not_filed_and_real_diagnostics_are(
    log_file: Path, diagnostics: list[str], not_filed: list[str]
):
    # Arrange — every line the test names is really in the fixture at a filing level.
    logged = _logged_messages(log_file)
    assert set(diagnostics) <= set(logged)
    assert set(not_filed) <= set(logged)

    # Act
    issues, _, _ = parse_log(log_file)

    # Assert
    messages = [issue.message for issue in issues]
    assert not set(messages) & set(not_filed)
    assert messages == diagnostics


def test_older_surefire_report_pointer_is_not_filed():
    """``maven-failure-real.log`` carries the older ``Please refer to …`` report pointer."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    assert 'Please refer to' in log_file.read_text(encoding='utf-8')

    issues, _, _ = parse_log(log_file)

    assert not [issue for issue in issues if issue.message.startswith('Please refer to')]


def test_older_surefire_dump_file_pointer_is_not_filed():
    """``sample-maven-failure.log`` carries the older ``Please refer to dump files …`` line."""
    log_file = TEST_DATA_DIR.parent / 'sample-maven-failure.log'
    assert 'Please refer to dump files' in log_file.read_text(encoding='utf-8')

    issues, _, _ = parse_log(log_file)

    assert not [issue for issue in issues if issue.message.startswith('Please refer to')]


def test_passing_test_count_line_is_not_a_test_failure(tmp_path):
    # Arrange
    log_file = tmp_path / 'passing-count.log'
    log_file.write_text('[WARNING] Tests run: 27, Failures: 0, Errors: 0, Skipped: 1\n', encoding='utf-8')

    # Act
    issues, _, _ = parse_log(log_file)

    # Assert
    assert not [issue for issue in issues if issue.category == 'test_failure']


def test_control_failing_test_count_line_is_still_filed(tmp_path):
    """CONTROL: the zero-failure skip must not swallow a count line that reports failures."""
    # Arrange
    message = 'Tests run: 5, Failures: 2, Errors: 0, Skipped: 0'
    log_file = tmp_path / 'failing-count.log'
    log_file.write_text(f'[ERROR] {message}\n', encoding='utf-8')

    # Act
    issues, _, _ = parse_log(log_file)

    # Assert
    filed = [issue for issue in issues if issue.message == message]
    assert len(filed) == 1
    assert filed[0].category == 'test_failure'
    assert filed[0].severity == SEVERITY_ERROR


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
    assert _build_shared.cmd_run_common(cast(DirectCommandResult, result), parser, 'maven', output_format='json') == 0
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

    emitted = _emit_maven_success(capsys, _job_log_parser, routed_tests_run=4892)

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
