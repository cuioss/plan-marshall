#!/usr/bin/env python3
"""Assert that written pytest identifiers appear in a module-test log.

This helper is the second half of the execute-task module_testing guardrail
(D2 in the lesson-2026-04-17-009 solution outline). After a green
``module-tests`` run, the execute-task skill calls this helper with:

1. The pytest node identifiers (``module::class::test``) that the task just
   wrote or modified in the active worktree, and
2. The path to the most recent module-test log captured from the build run.

The helper returns a :class:`DiffResult` describing which identifiers were
located on some line of the log (``found``) and which were not (``missing``).
``passed`` is true iff every written identifier appears at least once.

The matching is a case-sensitive regex anchored to a whitespace boundary or
end-of-line: ``{re.escape(identifier)}(?:\\s|$)``. Anchoring prevents prefix
collisions (e.g., ``test_login`` would otherwise false-match
``test_login_failure``), which is a real concern when test-function names
share a common prefix — the helper's job is to surface absent identifiers, so
a prefix collision that hides a missing identifier defeats the guardrail.

Why regex rather than equality: the log line also carries a status token
(``PASSED``, ``FAILED``, ``SKIPPED``), a separator, timing, and sometimes a
leading ``tests/...`` relative path. The node identifier is embedded in that
line, followed by whitespace before the status token. The anchor lets us
accept all of those surrounding tokens while still requiring the identifier
to end at a token boundary.

Contract
--------

``assert_identifiers_in_log(written_identifiers, log_path) -> DiffResult``

* Reads ``log_path`` line by line. For each identifier in
  ``written_identifiers``, checks whether any line contains the identifier as
  a substring. Returns a :class:`DiffResult` with ``passed=True`` iff every
  identifier was found on at least one line.
* Input order is preserved in both ``found`` and ``missing`` tuples so the
  caller can display a stable, deterministic diff.
* Empty ``written_identifiers`` yields ``DiffResult(passed=True, found=(),
  missing=())`` — vacuously true.
* Missing or unreadable ``log_path`` raises :class:`FileNotFoundError` (or
  :class:`PermissionError` / :class:`OSError`) with a clear message. The
  helper never swallows IO errors; callers must decide how to report them.

CLI
---

``python3 assert_test_identifiers.py run --identifiers-file {path} --log {path}``

``--identifiers-file`` is a newline-delimited list of identifiers; blank lines
are stripped. TOON output carries ``status``, ``passed``, ``found_count``,
``missing_count``, and the ``missing[]`` table so callers can surface the gap
without re-parsing the log.

Exit codes follow the task's explicit pass/fail contract (not the generic
output-contract exit semantics), because execute-task shells the exit status
as a guardrail boolean:

* ``0`` — assertion passed (every identifier found)
* ``1`` — assertion failed (one or more identifiers missing)
* ``2`` — usage error or IO error (argparse failure, log unreadable)
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DiffResult:
    """Outcome of comparing written identifiers against a module-test log.

    Attributes:
        passed: True iff every input identifier appeared on some line of the
            log. Vacuously true when the input is empty.
        found: Identifiers located on at least one log line, preserving the
            input order.
        missing: Identifiers that did not appear on any log line, preserving
            the input order.
    """

    passed: bool
    found: tuple[str, ...]
    missing: tuple[str, ...]


def assert_identifiers_in_log(
    written_identifiers: Iterable[str],
    log_path: Path,
) -> DiffResult:
    """Check that every written identifier appears in the module-test log.

    Args:
        written_identifiers: Pytest node identifiers (``module::class::test``)
            that the current task wrote or modified. Order is preserved in the
            result for deterministic diffs. An empty iterable is a vacuous
            pass and does not require the log to exist — except that we still
            read the log to surface IO errors early; callers that truly want
            to skip the check should not call this helper.
        log_path: Path to the module-test log file to search. Must exist and
            be readable; otherwise a :class:`FileNotFoundError` /
            :class:`OSError` is raised with a clear message.

    Returns:
        A :class:`DiffResult` describing which identifiers were found and
        which were not. ``passed`` is ``True`` iff ``missing`` is empty.

    Raises:
        FileNotFoundError: ``log_path`` does not exist.
        PermissionError: ``log_path`` exists but is not readable by the
            current process.
        OSError: Any other IO failure while reading ``log_path``.
    """
    identifiers = tuple(written_identifiers)

    # Vacuous pass: no identifiers to check. Return early without touching the
    # filesystem so callers can use this helper as a no-op when the task
    # produced no test output.
    if not identifiers:
        return DiffResult(passed=True, found=(), missing=())

    if not log_path.exists():
        raise FileNotFoundError(f'module-test log not found: {log_path}')
    if not log_path.is_file():
        raise FileNotFoundError(f'module-test log path is not a regular file: {log_path}')

    # Read the log into memory once. Module-test logs are typically small
    # (tens to hundreds of KB); the regex scan over a list of lines is both
    # faster and easier to reason about than a streaming scan, and it lets us
    # preserve input order cheaply. ``errors='replace'`` tolerates odd bytes
    # pytest occasionally emits without hiding IO errors.
    with log_path.open('r', encoding='utf-8', errors='replace') as handle:
        lines = handle.readlines()

    found: list[str] = []
    missing: list[str] = []
    for identifier in identifiers:
        # Anchor to a whitespace boundary or end-of-line so that e.g.
        # ``test_login`` does not false-match a line carrying only
        # ``test_login_failure``. pytest writes nodeid<whitespace>STATUS so the
        # anchor is always satisfied when the test was actually collected.
        pattern = re.compile(rf'{re.escape(identifier)}(?:\s|$)')
        if any(pattern.search(line) for line in lines):
            found.append(identifier)
        else:
            missing.append(identifier)

    return DiffResult(
        passed=not missing,
        found=tuple(found),
        missing=tuple(missing),
    )


def _load_identifiers(identifiers_path: Path) -> list[str]:
    """Load identifiers from a newline-delimited text file.

    Blank lines (empty or whitespace-only) are stripped. Non-blank lines are
    returned with trailing whitespace removed so that a trailing newline in
    the file does not affect the substring match.
    """
    if not identifiers_path.exists():
        raise FileNotFoundError(f'identifiers file not found: {identifiers_path}')
    if not identifiers_path.is_file():
        raise FileNotFoundError(f'identifiers file path is not a regular file: {identifiers_path}')

    with identifiers_path.open('r', encoding='utf-8') as handle:
        raw_lines = handle.readlines()

    identifiers: list[str] = []
    for raw in raw_lines:
        stripped = raw.rstrip('\r\n').strip()
        if stripped:
            identifiers.append(stripped)
    return identifiers


def _emit_toon(result: DiffResult) -> None:
    """Write the TOON output contract for ``run`` to stdout.

    The shape is kept flat on purpose so the output is easy to diff and easy
    to parse with :func:`toon_parser.parse_toon` in tests.
    """
    print('status: success')
    print(f'passed: {"true" if result.passed else "false"}')
    print(f'found_count: {len(result.found)}')
    print(f'missing_count: {len(result.missing)}')
    if result.missing:
        print(f'missing[{len(result.missing)}]:')
        for identifier in result.missing:
            print(f'  - {identifier}')
    else:
        # Empty uniform array — keep the key present so downstream parsers
        # always see a stable schema. ``missing[0]:`` is the TOON idiom for
        # "this list exists and is empty".
        print('missing[0]:')


def _emit_toon_error(message: str) -> None:
    """Write the TOON error contract for usage / IO failures to stdout.

    Uses ``status: error`` (not ``success``) to signal that the assertion
    never ran — distinguishing a pass/fail outcome from a plumbing failure.
    """
    print('status: error')
    # Normalise newlines in the error message so multi-line exception text
    # never breaks the flat TOON shape.
    flattened = message.replace('\n', ' ').strip()
    print(f'error: {flattened}')


def cmd_run(args: argparse.Namespace) -> int:
    """Handle the ``run`` subcommand.

    Returns the process exit code directly (``0`` pass, ``1`` fail, ``2``
    usage/IO error) so ``main`` can forward it to :func:`sys.exit` without
    translation.
    """
    identifiers_path = Path(args.identifiers_file)
    log_path = Path(args.log)

    try:
        identifiers = _load_identifiers(identifiers_path)
        result = assert_identifiers_in_log(identifiers, log_path)
    except FileNotFoundError as exc:
        _emit_toon_error(str(exc))
        return 2
    except PermissionError as exc:
        _emit_toon_error(f'permission denied reading log: {exc}')
        return 2
    except OSError as exc:
        _emit_toon_error(f'IO error: {exc}')
        return 2

    _emit_toon(result)
    return 0 if result.passed else 1


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``run`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Assert that pytest node identifiers written by the current task '
            'appear in the module-test log. Used by plan-marshall:execute-task '
            'as a structural guardrail against silently-skipped tests.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command_name', required=True)

    run_parser = subparsers.add_parser(
        'run',
        help=('Diff written identifiers against a module-test log and report the outcome as TOON'),
        allow_abbrev=False,
    )
    run_parser.add_argument(
        '--identifiers-file',
        required=True,
        dest='identifiers_file',
        help=('Path to a newline-delimited list of pytest node identifiers. Blank lines are stripped.'),
    )
    run_parser.add_argument(
        '--log',
        required=True,
        dest='log',
        help='Path to the module-test log file to search.',
    )
    run_parser.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())
