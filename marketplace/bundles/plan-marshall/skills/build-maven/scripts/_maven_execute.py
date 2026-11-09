#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Maven command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for Maven command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- apply_selector_miss_guard(): the run-path truth check for a ``-Dtest`` miss
- apply_zero_test_guard(): the run-path truth check for a test run that ran none

Usage:
    from _maven_execute import execute_direct, cmd_run
"""

import os
import re
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree as ET

from _build_execute import CaptureStrategy
from _build_execute_factory import ExecuteConfig, create_execute_handlers, default_command_key_fn
from _build_parse import SEVERITY_ERROR, read_log_text
from _build_result import STATUS_ERROR, STATUS_SUCCESS, indeterminate_result
from _build_shared import DEFAULT_BUILD_TIMEOUT
from _maven_cmd_parse import (
    TEST_LOG_UNREADABLE,
    TEST_RUN_EXECUTED_NOTHING,
    TEST_SELECTOR_MATCHED_NOTHING,
    collected_test_count,
    dtest_selector,
    executed_test_count,
    is_selector_miss_message,
    parse_log,
    selector_miss_pattern,
    selector_miss_reason,
)

# Outer timeout floor (seconds) for Maven builds. Maven resolves dependencies
# and downloads plugins on a cold local repository before a single module
# compiles, so a learned duration measured against a warm repository
# under-specifies the next cold run. This declared floor protects against that
# under-specification: no learned value can drop the outer wrapper bound below
# it, so a cold-cache resolve is never killed mid-download and reported as a
# build failure. Peer of ``_pyproject_execute.PYTEST_OUTER_FLOOR_SECONDS`` —
# every engine declares its own floor rather than inheriting ``MIN_TIMEOUT``.
MAVEN_OUTER_FLOOR_SECONDS = 300

#: Issue categories that name a build failure whatever severity they carry — the
#: two "did not work" categories plus a dependency that could not be resolved.
#: Every other category is advisory (the ``javadoc_warning`` /
#: ``deprecation_warning`` / ``unchecked_warning`` / ``openrewrite_info``
#: patterns) or the default ``other``.
#:
#: A category alone is not enough, in both directions. A failing javadoc or
#: deprecation plugin prints its diagnostics at ``[ERROR]`` and a pattern keyed on
#: the word "javadoc" files them under ``javadoc_warning`` — that line IS the build
#: failure. And an unrelated ``[WARNING]`` Maven prints beside a selector miss
#: (a corrupted-stdout notice, say) files under ``other`` without being a failure
#: at all. The back-off therefore reads severity too: an ``[ERROR]``-level issue is
#: real whatever its category, and a ``[WARNING]``-level ``other`` line is not.
_FAILURE_ISSUE_CATEGORIES = frozenset({'compilation_error', 'test_failure', 'dependency_error'})

#: The advisory categories the parser vocabulary declares. Read here only so the
#: test suite can pin that the failure set plus this set covers every category
#: ``_maven_cmd_parse.MAVEN_PATTERNS`` emits — an unlisted new category then fails
#: a test instead of silently turning an advisory into a back-off (or the reverse).
_ADVISORY_ISSUE_CATEGORIES = frozenset(
    {'javadoc_warning', 'deprecation_warning', 'unchecked_warning', 'openrewrite_info'}
)

#: The Maven phases whose run is a test run: the module-tests canonical of a
#: normal module is ``test``, and the one of a module consuming a reactor test
#: artifact is ``package`` (see ``_maven_cmd_discover._build_commands``).
_TEST_PHASE_GOALS = ('test', 'package')

#: Maven's lifecycle phases. A token in this set is a GOAL.
_LIFECYCLE_PHASES = frozenset(
    {
        'validate',
        'initialize',
        'generate-sources',
        'process-sources',
        'generate-resources',
        'process-resources',
        'compile',
        'process-classes',
        'generate-test-sources',
        'process-test-sources',
        'generate-test-resources',
        'process-test-resources',
        'test-compile',
        'process-test-classes',
        'test',
        'prepare-package',
        'package',
        'pre-integration-test',
        'integration-test',
        'post-integration-test',
        'verify',
        'install',
        'deploy',
        'pre-clean',
        'clean',
        'post-clean',
        'pre-site',
        'site',
        'post-site',
        'site-deploy',
    }
)

#: The flag forms that make a test-phase invocation skip its tests, so an empty
#: test population is what the command asked for rather than a surprise. The
#: value is captured (case-insensitively — Maven parses its booleans that way) so
#: an explicit ``=false`` is NOT read as a skip.
_SKIP_FLAG_PATTERN = re.compile(r'-D(?:skipTests|maven\.test\.skip)(?:=(?P<value>true|false))?(?=\s|$)', re.IGNORECASE)

#: A plugin-goal coordinate (``surefire:test``, ``org.apache.maven.plugins:maven-surefire-plugin:test``,
#: ``g:a:v:test``). At least one colon and at least two segments; deliberately
#: narrow — no slashes and no empty first segment — so an option's value that
#: happens to contain a colon (``-pl :core``, ``-f C:/repo/pom.xml``) is not
#: mistaken for a goal. The version segment is what a fully-qualified goal adds,
#: and dropping it left such a goal unguarded.
_PLUGIN_GOAL_PATTERN = re.compile(r'[A-Za-z0-9_.\-]+(?::[A-Za-z0-9_.\-]+)+')

#: Options that take a SEPARATE value token. Their value is consumed so a value
#: that is spelled like a phase or a coordinate (``-pl integration-test``,
#: ``-pl :core``) is not read as the goal. The goal recogniser below is Maven's
#: own vocabulary; this set only decides which token to step over, and an
#: unlisted value-taking option costs at most a wrong classification when its
#: value is literally a phase name.
_VALUE_TAKING_OPTIONS = frozenset(
    {
        '-pl',
        '--projects',
        '-f',
        '--file',
        '-l',
        '--log-file',
        '-P',
        '--activate-profiles',
        '-s',
        '--settings',
        '-gs',
        '--global-settings',
        '-t',
        '--toolchains',
        '-gt',
        '--global-toolchains',
        '-rf',
        '--resume-from',
        '-T',
        '--threads',
        '-b',
        '--builder',
        '-c',
        '--color',
    }
)

#: Maven's own statement that a test-phase invocation skipped its tests, anchored
#: to a LOG LINE. The phrase is what a ``-DskipTests`` set through
#: ``.mvn/maven.config`` or ``MAVEN_OPTS`` — invisible on the command line this
#: guard is handed — leaves behind, so it is recognised as a requested skip rather
#: than reported as an empty population. Anchoring matters: a test's own output can
#: contain the same words, and treating that as the run's skip would silence the
#: zero-test guard for a run that genuinely executed nothing.
_SKIP_MARKER_PATTERN = re.compile(r'(?m)^(?:\[[A-Z]+\]\s*)?Tests are skipped\.\s*$')

#: Surefire's own statement that it matched no test class, anchored to a LOG LINE
#: for the same reason as :data:`_SKIP_MARKER_PATTERN`: a run whose test output
#: happens to print the phrase is not a run that matched nothing.
_NO_TESTS_TO_RUN_PATTERN = re.compile(r'(?m)^(?:\[[A-Z]+\]\s*)?No tests to run\.\s*$')

#: Directories a Surefire/Failsafe run writes its per-class XML reports into
#: (``target/surefire-reports`` in the module that ran the tests).
_REPORT_SUMMARY_DIRS = ('surefire-reports', 'failsafe-reports')

#: Directories a report scan never descends into: none of them is a module build
#: output, and walking them would make the guard pay for the whole checkout.
_REPORT_SCAN_PRUNED = frozenset({'.git', '.plan', 'node_modules', '.venv', '__pycache__'})


def _asks_to_skip_tests(args: str) -> bool:
    """Whether the arguments ask Maven to skip its tests.

    ``-DskipTests`` and ``-Dmaven.test.skip`` count, and so does an explicit
    ``=true``; ``=false`` does not — reading it as a skip would switch the
    zero-test guard off for the invocations most likely to need it.
    """
    for match in _SKIP_FLAG_PATTERN.finditer(args):
        value = match.group('value')
        if value is None or value.lower() != 'false':
            return True
    return False


def _maven_scope_fn(args: str) -> str:
    """Extract scope from Maven -pl argument.

    Handles both '-pl module' and '-pl=module' forms.
    """
    match = re.search(r'-pl[=\s]+(\S+)', args)
    if match:
        return match.group(1)
    return 'default'


def _maven_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build Maven command with -l flag for log file output."""
    cmd_parts = [wrapper, '-l', log_file] + args.split()
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


def _indeterminate(result: dict, message: str) -> dict:
    """Render ``result`` as ``indeterminate``, carrying everything it established.

    Everything the execution established travels with the verdict — the
    executor's optional fields included — so a consumer reading ``wrapper``, a
    bound or a future field off this result does not find it absent although
    the build did run. Only the keys ``indeterminate_result`` sets itself (plus
    the failure-renderer inputs that no longer apply) are excluded.
    """
    replaced = {
        'status',
        'error',
        'message',
        'exit_code',
        'duration_seconds',
        'log_file',
        'command',
        'errors',
        'routed_errors',
        'routed_tests_run',
    }
    carried = {name: value for name, value in result.items() if name not in replaced}
    return indeterminate_result(
        message,
        int(result.get('duration_seconds') or 0),
        str(result.get('log_file') or ''),
        str(result.get('command') or ''),
        exit_code=int(result.get('exit_code') or 0),
        **carried,
    )


def apply_selector_miss_guard(result: dict) -> dict:
    """Refuse to call a run green when its Surefire selector matched nothing.

    A ``-Dtest`` selector that matches no test is a wrong command, not a
    passing run and not a failing test. Surefire ends such a run non-zero by
    default and green with ``-Dsurefire.failIfNoSpecifiedTests=false``; both
    shapes are turned into one ``indeterminate`` result naming
    ``TEST_SELECTOR_MATCHED_NOTHING``.

    ``indeterminate`` rather than ``error`` is the recorded choice: an ``error``
    result with a zero exit code reaches the build-failure path, which stores
    every parsed issue and manufactures a synthetic failure row — a verdict out
    of a run that ran no test. Indeterminate stores no finding, synthesises no
    ``errors[]`` row, and still blocks every gate that requires ``success``.

    Scope limit, stated rather than guessed: the runner prints its miss message on
    its FAILURE path, so a miss suppressed with
    ``-Dsurefire.failIfNoSpecifiedTests=false`` is visible only when it leaves the
    run's collected count at zero. Inside a reactor where another module collected
    tests, such a miss is invisible and the run stays green; that limit is
    documented in ``build-maven/SKILL.md`` § "Test selectors".

    Args:
        result: A finished execution result (``execute_direct``'s dict).

    Returns:
        The same result unchanged when no selector miss was detected — the
        identity is preserved so a control case can assert it — or an
        ``indeterminate`` result naming the reason.
    """
    status = result.get('status')
    if status not in (STATUS_SUCCESS, STATUS_ERROR):
        return result
    command = str(result.get('command') or '')
    selector = dtest_selector(command)
    # A failed build is suspect whatever the command says (the runner's own goal
    # failure names the selector). A successful one is suspect only when a
    # selector was in play: Surefire/Failsafe print their "No tests matching
    # pattern ... were executed" line on the FAILURE path only, so an exit-0 miss
    # surfaces as a zero-collected summary instead — which is the zero-test
    # guard's ground, not this one's.
    if status == STATUS_SUCCESS and selector is None:
        return result
    try:
        log_text = read_log_text(result['log_file'])
    except (KeyError, OSError):
        # No readable log means no evidence. For an exit-0 selector run that is
        # the whole question — a green would claim the selector ran tests — so
        # the run is named unreadable instead of being trusted.
        if status == STATUS_SUCCESS:
            return _indeterminate(
                result,
                f'{TEST_LOG_UNREADABLE}: the -Dtest run exited 0 but its log could not be read, so '
                'nothing establishes that a test ran — not a green.',
            )
        # A failed build is already not green; its own failure stands.
        return result
    # The zero-collected shape is an EXIT-0 shape. On a failed build only
    # Surefire's explicit "No tests matching pattern" counts, because a reactor
    # can print a zero-test summary for an earlier module and then fail later —
    # and that real failure must not be relabelled as a wrong selector.
    reason = selector_miss_reason(log_text, command if status == STATUS_SUCCESS else None)
    if reason is None:
        return result
    # A reactor run with `--fail-at-end` can carry this selector miss AND a real
    # failure in another module. Converting the whole run to `indeterminate`
    # would drop that module's errors and findings, so the miss only claims the
    # run when every other issue in the log is informational. The miss's own
    # goal-failure line is evidence OF the miss, not a failure beside it.
    if status != STATUS_SUCCESS:
        try:
            issues, _, _ = parse_log(str(result.get('log_file') or ''))
        except (KeyError, OSError):
            return result
        if any(
            not is_selector_miss_message(issue.message)
            and (issue.severity == SEVERITY_ERROR or issue.category in _FAILURE_ISSUE_CATEGORIES)
            for issue in issues
        ):
            return result

    # Name the selector the log carries when the command line does not show it:
    # a selector set through `.mvn/maven.config`, `MAVEN_OPTS` or a profile, or
    # a Failsafe `-Dit.test` miss, is still printed by the runner on its failure
    # path.
    pattern = selector or selector_miss_pattern(log_text)
    named = f"'{pattern}'" if pattern else 'the -Dtest selector'
    executed = executed_test_count(log_text)
    if executed:
        # The selector matched in one module and missed in another; claiming the
        # run executed nothing would be false of the modules that did run.
        claim = (
            f'{named} matched no test in at least one module, while the modules that did match '
            f'executed {executed} test(s) — so the run is not a green.'
        )
    elif executed == 0:
        claim = f'{named} matched no test, so the run executed nothing — not a failure and not a green.'
    else:
        # An unmeasured summary cannot answer how much ran, so neither the
        # "executed nothing" nor a count may be claimed.
        claim = (
            f'{named} matched no test in at least one module and the log does not measure how much '
            f'else ran, so the run supports no green.'
        )
    return _indeterminate(
        result,
        f'{TEST_SELECTOR_MATCHED_NOTHING}: {claim} A miss is a wrong selection, not a test result; '
        "whether the runner prints its own 'No tests matching pattern' line depends on its "
        'fail-if-no-tests setting.',
    )


def _leading_goal(args: str) -> str | None:
    """Return the first Maven goal of an invocation, or None when it names none.

    A goal is a lifecycle phase or a plugin-goal coordinate (``surefire:test``),
    and both are recognised by Maven's own vocabulary. Tokens are walked left to
    right: an option's separately supplied value is stepped over, and every other
    non-option token is only a candidate — it becomes the goal when it has a
    goal's shape. That is what keeps ``-pl core test``, ``-pl :core test`` and
    ``-gt /path test`` from reading an option's value as the goal.
    """
    tokens = args.split()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _VALUE_TAKING_OPTIONS:
            index += 2
            continue
        if token.startswith('-'):
            index += 1
            continue
        if token in _LIFECYCLE_PHASES or _PLUGIN_GOAL_PATTERN.fullmatch(token):
            return token
        index += 1
    return None


def _test_phase_goal(args: str) -> str | None:
    """Return the test goal an invocation leads with, or None.

    Only the LEADING goal decides: a ``clean install`` or a ``verify
    -Ppre-commit`` run also executes tests, but its purpose is the build or the
    gate, and a project that has no test to run there is legitimately green. A
    plugin-goal form counts, so ``-Dtest`` via the direct ``surefire:test`` goal
    is still a test run.
    """
    goal = _leading_goal(args)
    if goal is None or goal.split(':')[-1] not in _TEST_PHASE_GOALS:
        return None
    if _asks_to_skip_tests(args):
        return None
    return goal


def _report_files(root: Path) -> Iterator[Path]:
    """Yield every Surefire/Failsafe ``TEST-*.xml`` report under ``root``.

    Walks the module tree (a reactor run writes reports in every module that ran
    tests) while pruning directories no build output lives in.

    Args:
        root: The directory the Maven invocation ran in.

    Yields:
        Paths to per-class report files.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _REPORT_SCAN_PRUNED]
        if os.path.basename(dirpath) not in _REPORT_SUMMARY_DIRS:
            continue
        for name in filenames:
            if name.startswith('TEST-') and name.endswith('.xml'):
                yield Path(dirpath) / name


def _report_executed_tests(report: Path) -> int:
    """Return the EXECUTED test count a Surefire/Failsafe report records, or 0.

    Surefire's ``tests`` attribute counts every collected test, skipped ones
    included, so a class whose whole population was ``@Disabled`` reports a
    non-zero ``tests`` while the run executed nothing. Executed is therefore
    ``tests - skipped``, clamped at 0 for a report that claims more skips than
    tests.

    A report that states neither count is no evidence: an absent or unparseable
    ``skipped`` is NEVER read as zero skips, because that would credit tests the
    report does not say ran. A malformed or unreadable report is 0 rather than an
    error: this reader only ever ADDS evidence, so an unreadable one must not
    manufacture any.

    Args:
        report: One ``TEST-*.xml`` file.

    Returns:
        The number of tests the report's root element says were executed, or 0.
    """
    try:
        root = ET.parse(report).getroot()
    except (ET.ParseError, OSError):
        return 0
    collected = _report_attribute_as_int(root, 'tests')
    skipped = _report_attribute_as_int(root, 'skipped')
    if collected is None or skipped is None:
        return 0
    return max(collected - skipped, 0)


def _report_attribute_as_int(root: ET.Element, name: str) -> int | None:
    """Return the integer value of ``root``'s ``name`` attribute, or ``None``.

    ``None`` is the "the attribute is absent or unparseable" answer, never 0: the
    two are different facts, and only a STATED count may credit a run.
    """
    raw = root.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _run_start_time(log_file: str | None, duration_seconds: object) -> float | None:
    """Return the moment this run began, or ``None`` when it cannot be bounded.

    The log file is written THROUGH the run, so its last-write stamp is the run's
    END, not its start. The start is that stamp minus the duration the wrapper
    measured, less a second of truncation slack. Where the duration is
    unavailable the end stamp cannot bound the start, so the answer is ``None``
    and no report is credited.

    Args:
        log_file: This run's log path.
        duration_seconds: The wrapper's measured run duration, when it reported one.

    Returns:
        The run's start as a POSIX timestamp, or ``None``.
    """
    if not log_file:
        return None
    try:
        ended = Path(log_file).stat().st_mtime
    except OSError:
        return None
    try:
        duration = float(duration_seconds)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return ended - duration - 1.0


def _reports_show_executed_tests(
    project_dir: str | None,
    log_file: str | None,
    duration_seconds: object = None,
) -> bool:
    """Whether a Surefire/Failsafe report written by THIS run reported executed tests.

    A quiet run — ``-q`` supplied through ``.mvn/maven.config`` or ``MAVEN_OPTS``,
    or Surefire's ``printSummary=false`` — still writes one ``TEST-*.xml`` per test
    class it processed; only the LOG's summary line is hidden. Those reports are
    therefore the evidence a hidden summary leaves behind, and reading them is
    what tells "the summary was suppressed" from "nothing was collected".

    A report older than this run's START belongs to a PREVIOUS run, and crediting
    it would turn "executed nothing" into a green — the exact false credit this
    guard exists to remove — so it is ignored. The start is derived from the log's
    last write minus the wrapper's measured duration (see
    :func:`_run_start_time`): the log is appended to THROUGH the run, so its own
    stamp marks the end, and reports are written before that end.

    Args:
        project_dir: The directory the Maven invocation ran in, or ``None`` when
            the caller supplied none — then no report can be attributed to it.
        log_file: This run's log path.
        duration_seconds: The wrapper's measured run duration, when it reported one.

    Returns:
        True only when a report written by this run reports one or more EXECUTED
        tests — Surefire's ``tests`` attribute less its ``skipped`` count.
    """
    if not project_dir:
        return False
    root = Path(project_dir)
    if not root.is_dir():
        return False
    started = _run_start_time(log_file, duration_seconds)
    if started is None:
        # Without a bound, any report on disk could be a previous run's — the exact
        # false credit this bound exists to stop.
        return False
    for report in _report_files(root):
        try:
            modified = report.stat().st_mtime
        except OSError:
            continue
        if modified < started:
            continue
        if _report_executed_tests(report) > 0:
            return True
    return False


def apply_zero_test_guard(result: dict, args: str, *, project_dir: str | None = None) -> dict:
    """Refuse to credit a green test-phase run that executed no test.

    A green exit code from ``mvn test`` reads as "the tests passed" to every
    consumer, but a run whose Surefire selector excluded every module — or a
    reactor root that builds no test module — collects nothing, and no gate may
    credit that. Such a run is neither a failure nor a green:

    - a parsed, MEASURED summary that reports zero EXECUTED tests — either no
      test collected, or a population that was skipped in full — is evidence of
      an empty population;
    - no summary on a leading ``test`` goal is EITHER an empty population OR a
      summary the run's log level hid, and the evidence tells them apart: a
      Surefire/Failsafe report this run wrote with executed tests,
      or Surefire's own ``No tests to run.`` line, keeps the green; with neither,
      nothing was collected. A leading ``package`` goal without a summary is a
      compile and package run that reported no tests — only a summary naming a
      zero population is evidence there;
    - an unreadable log of a test-phase run is no evidence either, and no
      evidence never becomes a green for a run whose truth lives in its log;
    - an empty population whose log carries NO test summary at all and states
      the build skipped its tests (``Tests are skipped.``) is a requested skip,
      not a surprise, and keeps its green — this is what recognises a
      ``-DskipTests`` set through ``.mvn/maven.config`` or ``MAVEN_OPTS``, which
      the arguments this guard is handed do not show. The marker is not consulted
      when a summary exists: a summary naming zero is evidence of an empty
      population whatever another module's skip line says.

    Args:
        result: A finished execution result (``execute_direct``'s dict).
        args: The Maven arguments the invocation carried.
        project_dir: The directory the invocation ran in. The report-file read
            that tells a hidden summary from an empty population needs it; an
            absent value means no report can be attributed to this run, and the
            no-summary case then stays indeterminate.

    Returns:
        The same result unchanged when the run executed a test, when it is no
        test-phase run, when it was not green, when an empty population was a
        requested skip, when Surefire matched no test class at all, or when a
        report this run wrote shows executed tests — otherwise an
        ``indeterminate`` result naming ``TEST_RUN_EXECUTED_NOTHING``.
    """
    if result.get('status') != STATUS_SUCCESS:
        return result
    goal = _test_phase_goal(args)
    if goal is None:
        return result
    try:
        log_text = read_log_text(result['log_file'])
    except (KeyError, OSError):
        return _indeterminate(
            result,
            f'{TEST_LOG_UNREADABLE}: the {goal} run exited 0 but its log could not be read, so '
            'nothing establishes that a test ran — not a green.',
        )
    collected = collected_test_count(log_text)
    executed = executed_test_count(log_text)
    if collected and executed != 0:
        # A MEASURED summary that executed nothing (``executed == 0``) is a
        # non-empty population that still credits no gate: the suite collected
        # tests and skipped every one. An UNMEASURED summary (``executed is
        # None``) keeps the plain collected-count evidence it has always had —
        # its executed count is not a measurement, so it cannot refute one.
        return result
    if collected == 0 or executed == 0:
        if collected:
            evidence = f"the run's log reports {collected} collected test(s) of which none executed"
        else:
            evidence = "the run's log reports zero collected tests, so nothing executed"
    elif _reports_show_executed_tests(project_dir, result.get('log_file'), result.get('duration_seconds')):
        # The summary was hidden (a quiet run, or Surefire's printSummary=false),
        # not absent: the reports this run wrote name executed test classes.
        return result
    elif goal.split(':')[-1] == 'test':
        if _SKIP_MARKER_PATTERN.search(log_text):
            return result
        if _NO_TESTS_TO_RUN_PATTERN.search(log_text):
            # Surefire RAN and matched no test class: the module has nothing to
            # run, so its green is truthful. A run that reported ``Tests run: 0``
            # took the measured-zero branch above and stays indeterminate.
            return result
        evidence = 'the log carries no Surefire or Failsafe test summary, so the run collected and executed nothing'
    else:
        return result
    return _indeterminate(
        result,
        f'{TEST_RUN_EXECUTED_NOTHING}: {evidence} — not a failure and not a green, because a test '
        'run that executed no test credits no gate.',
    )


def _selector_miss_guard(inner):
    """Wrap the factory's execute so the run-path truth guards run on every route.

    A routed build re-enters this factory inside the daemon child, so both guards
    apply there too — which is also why they must not read a routed job log: this
    wrapper only ever sees the in-process result. The wrapper names
    ``explicit_timeout`` and ``plan_id`` explicitly and forwards BOTH on its
    single inner call, as the factory's wrapper contract requires.
    """

    def execute_direct(
        args: str,
        command_key: str,
        default_timeout: int = DEFAULT_BUILD_TIMEOUT,
        project_dir: str = '.',
        env_vars: dict[str, str] | None = None,
        working_dir: str | None = None,
        explicit_timeout: int | None = None,
        *,
        plan_id: str,
    ):
        result = inner(
            args=args,
            command_key=command_key,
            default_timeout=default_timeout,
            project_dir=project_dir,
            env_vars=env_vars,
            working_dir=working_dir,
            explicit_timeout=explicit_timeout,
            plan_id=plan_id,
        )
        guarded = apply_selector_miss_guard(result)
        return apply_zero_test_guard(guarded, args, project_dir=working_dir or project_dir)

    return execute_direct


_CONFIG = ExecuteConfig(
    tool_name='maven',
    unix_wrapper='mvnw',
    windows_wrapper='mvnw.cmd',
    system_fallback='mvn',
    capture_strategy=CaptureStrategy.TOOL_LOG_FLAG,
    build_command_fn=_maven_build_command_fn,
    scope_fn=_maven_scope_fn,
    command_key_fn=default_command_key_fn,
    default_timeout=DEFAULT_BUILD_TIMEOUT,
    min_timeout=MAVEN_OUTER_FLOOR_SECONDS,
)

execute_direct, cmd_run = create_execute_handlers(_CONFIG, parse_log, wrap_execute_fn=_selector_miss_guard)
