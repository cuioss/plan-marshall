#!/usr/bin/env python3
"""Scan ``script-execution.log`` AND ``work.log`` for argparse / script-internal failures.

Pure deterministic fact extractor — classifies non-zero-exit script calls by
stderr signature and emits a TOON fragment shaped for ``compile-report.py`` to
consume under the ``script-failure-analysis`` aspect.

Two log sinks are scanned and merged:

1. ``logs/script-execution.log`` — the two-tier executor audit log. A failed
   call is a header line followed by a two-space-indented continuation block
   whose ``exit_code:`` field is non-zero.
2. ``logs/work.log`` — the work log into which the executor mirrors a single
   ``[ERROR] (...:execute-script:N) script_failure notation=... exit_code=N
   failure_kind=... stderr=...`` line for every non-zero-exit call. This sink
   catches argparse rejections (exit 2) that an agent emitted directly to the
   work log when the ``script-execution.log`` entry was never written (the
   originating-context recurrence gap).

The two failure lists are merged and fed through ``dedupe_findings`` so the
within-log key ``(notation, subtype)`` collapses a ``script-execution.log``
entry and a ``work.log`` entry for the same notation + subtype into a single
finding. ``total_failures`` / ``unique_failures`` reflect both sinks.

Failure criterion: ONLY exit code 1 and exit code 2 are script failures.

| exit_code | stderr signature                          | subtype                 | type         |
|-----------|-------------------------------------------|-------------------------|--------------|
| 2         | ``invalid choice: ``                      | invented_subcommand     | anti-pattern |
| 2         | ``the following arguments are required: ``| missing_required_flag   | anti-pattern |
| 2         | ``unrecognized arguments: ``              | invented_flag           | anti-pattern |
| 2         | (no recognized argparse signature)        | argparse_other          | anti-pattern |
| 1         | non-argparse                              | script_internal_error   | bug          |
| 0         | (status: error TOON on stdout)            | NOT a failure — ignored | (n/a)        |

An exit code of ``0`` is NEVER a script failure, even when the call emitted a
``status: error`` TOON payload on stdout. Per the canonical output contract,
exit 0 means the script ran and produced a meaningful result; a
``status: error`` at exit 0 is a caller-handled *operation* failure (item not
found, validation failed), not a crash. ``parse_failures._flush`` and
``parse_work_log_failures`` both drop exit-0 (and ``None``) entries before
classification, so an operation failure can never be mislabeled
``script_internal_error``. There is deliberately NO
stdout-when-stderr-empty classifier: re-deriving a "failure" from an empty
stderr would mask future producer contract violations rather than surface
them, so that path is intentionally absent.

Each ``(component, subtype)`` pair surfaces once in ``findings[]`` plus a
seed-lesson fragment under ``lessons[]`` that ``compile-report`` and the
optional ``manage-lessons`` recorder downstream can pick up.

The script reads logs from disk directly — like ``analyze-logs.py``,
it does NOT invoke ``manage-logging`` because archived plans don't
participate in ``PLAN_BASE_DIR`` resolution.

Usage:
    python3 script-failure-analysis.py run --plan-id EXAMPLE-PLAN --mode live
    python3 script-failure-analysis.py run --archived-plan-path /abs/path --mode archived
"""

from __future__ import annotations

import argparse
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
)

# script-execution.log record shape (per manage-logging/standards/log-format.md):
#   [ts] [LEVEL] [hash] {notation} {subcommand} ({duration}s)
#     exit_code: N        <-- error entries only, two-space-indented continuation
#     args: ...           <-- error entries only
#     stderr: ...         <-- error entries only
# The header line carries NO inline ``exit_code`` token. A successful
# (exit-zero) call is a bare header with no continuation block; a failed
# call follows its header with a two-space-indented continuation block
# whose ``exit_code:`` field holds a non-zero value. The parser matches
# the header by notation (plus optional subcommand/duration) and then scans
# the continuation block for ``exit_code:``, ``args:``, and ``stderr:``.
_HEADER_RE = re.compile(
    r'^\[(?P<ts>[^\]]+)\]\s+\[(?P<level>[A-Z]+)\]\s+\[[^\]]+\]\s+'
    r'(?P<notation>[a-z][\w-]*:[\w-]+:[\w-]+)'
    r'(?:\s+(?P<sub>[\w-]+))?',
)

# Two-space-indented continuation field: ``  {key}: {value}``. Used to scan
# the block that follows an error-entry header for ``exit_code``, ``args``,
# ``stdout``, and ``stderr`` fields. The key alternation is restricted to the
# known continuation-field names so an indented line inside a wrapped stderr
# blob (e.g. ``  details: foo`` or ``  code: 123``) is NOT mistaken for a
# field — matching it would set ``in_stderr=False`` and prematurely truncate
# the accumulated stderr.
_FIELD_RE = re.compile(r'^  (?P<key>exit_code|args|stdout|stderr):\s?(?P<value>.*)$')

# Stderr-signature classifiers (substring matches on the accumulated stderr
# block). Order matters: ``invalid choice`` is checked before
# ``unrecognized arguments`` because argparse can emit both on subcommand
# typos.
_ARGPARSE_SIGNATURES: tuple[tuple[str, str], ...] = (
    ('invalid choice: ', 'invented_subcommand'),
    ('the following arguments are required: ', 'missing_required_flag'),
    ('unrecognized arguments: ', 'invented_flag'),
)

# work.log executor failure line. The executor mirrors every non-zero-exit
# call into the work log as a single physical line of the shape:
#
#   [ts] [LEVEL] [hash] [ERROR] (plan-marshall:execute-script:N) script_failure \
#       notation=<notation> exit_code=<N> failure_kind=<kind> stderr=<...>
#
# The leading manage-logging header ([ts] [LEVEL] [hash]) is tolerated by
# anchoring the match on the ``(...:execute-script:N) script_failure`` marker
# rather than the start of the line. ``notation`` and ``exit_code`` are
# captured as named groups; everything after ``stderr=`` (to end-of-line) is
# the embedded stderr signature used by the shared argparse classifier.
_WORK_LOG_FAILURE_RE = re.compile(
    r'\(\S*?execute-script:\d+\)\s+script_failure\s+'
    r'notation=(?P<notation>[a-z][\w-]*:[\w-]+:[\w-]+)\s+'
    r'exit_code=(?P<exit_code>\d+)\s+'
    r'failure_kind=(?P<failure_kind>\S+)'
    r'(?:\s+stderr=(?P<stderr>.*))?$',
)

# Leading manage-logging header for a work.log line: ``[ts] [LEVEL] [hash] ``.
# Used only to recover the timestamp for the failure record's representative
# sample; the failure marker itself is matched independently of the header.
_WORK_LOG_TS_RE = re.compile(r'^\[(?P<ts>[^\]]+)\]')


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan directory for ``mode``."""
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def read_log(path: Path) -> list[str]:
    """Return raw lines of ``path``. Missing file → empty list (silent).

    Unlike ``analyze-logs.read_log``, a missing script-execution log is the
    common case (some plans never invoke any script). Emitting a stderr
    warning here would create noise on every legitimate empty-log retrospective.
    """
    if not path.is_file():
        return []
    try:
        return path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return []


def parse_failures(lines: list[str]) -> list[dict[str, Any]]:
    """Walk ``lines`` and emit one dict per non-zero-exit script call.

    Returned shape per entry:
        {
            'timestamp': str,
            'notation': str,
            'subcommand': str | None,
            'exit_code': int,
            'stderr': str,  # accumulated stderr block joined by newlines
        }

    Each script call is recorded as a header line (``[ts] [LEVEL] [hash]
    notation subcommand (duration)``) optionally followed by a two-space-
    indented continuation block. A successful (exit-zero) call has no
    continuation block; a failed call carries ``exit_code: N`` (colon, not
    equals) plus ``args:`` and ``stderr:`` continuation fields. A header is
    treated as a failure only when its continuation block holds a non-zero
    ``exit_code:`` value.

    The parser is robust to ``stderr`` blobs that wrap across multiple lines:
    once an ``stderr:`` field is seen, every subsequent continuation line that
    is not itself a recognised field is appended to the stderr buffer.
    """
    failures: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    stderr_buf: list[str] = []
    in_stderr = False

    def _flush() -> None:
        if current is None:
            return
        # A record is a failure only when its continuation block carried a
        # non-zero exit_code. Bare headers (success entries) and headers whose
        # block reports exit_code 0 are dropped.
        code = current.get('exit_code')
        if code is None or code == 0:
            return
        current['stderr'] = '\n'.join(stderr_buf).strip()
        failures.append(current)

    for line in lines:
        header_match = _HEADER_RE.match(line)
        if header_match:
            _flush()
            stderr_buf = []
            in_stderr = False
            current = {
                'timestamp': header_match.group('ts'),
                'notation': header_match.group('notation'),
                'subcommand': header_match.group('sub'),
                'exit_code': None,
                'stderr': '',
            }
            continue
        if current is None:
            continue
        field_match = _FIELD_RE.match(line)
        if field_match:
            key = field_match.group('key')
            value = field_match.group('value')
            if key == 'exit_code':
                try:
                    current['exit_code'] = int(value.strip())
                except ValueError:
                    current['exit_code'] = None
                in_stderr = False
                continue
            if key == 'stderr':
                stderr_buf = [value.strip()]
                in_stderr = True
                continue
            # Any other recognised field (e.g. args, stdout) closes the
            # stderr accumulation.
            in_stderr = False
            continue
        # Non-field continuation line: append to stderr only when we are
        # inside a wrapped stderr blob.
        if in_stderr:
            stderr_buf.append(line)

    _flush()
    return failures


def parse_work_log_failures(lines: list[str]) -> list[dict[str, Any]]:
    """Walk ``work.log`` ``lines`` and emit one dict per executor failure line.

    The executor mirrors every non-zero-exit call into the work log as a single
    physical line carrying ``script_failure notation=... exit_code=...
    failure_kind=... stderr=...``. Each matching line yields one failure record
    in the SAME shape as :func:`parse_failures` so both sinks feed the shared
    :func:`classify_failure` / :func:`dedupe_findings` pipeline unchanged:

        {
            'timestamp': str,
            'notation': str,
            'subcommand': None,   # the work.log line does not carry a subcommand
            'exit_code': int,
            'stderr': str,        # the embedded stderr signature (may be empty)
        }

    A line whose ``exit_code`` is ``0`` is dropped (operation failures exit 0
    and are caller-handled outcomes, never script failures). Lines that do not
    match the executor failure marker are ignored.
    """
    failures: list[dict[str, Any]] = []
    for line in lines:
        match = _WORK_LOG_FAILURE_RE.search(line)
        if match is None:
            continue
        try:
            exit_code = int(match.group('exit_code'))
        except ValueError:
            continue
        if exit_code == 0:
            continue
        ts_match = _WORK_LOG_TS_RE.match(line)
        timestamp = ts_match.group('ts') if ts_match else ''
        stderr = (match.group('stderr') or '').strip()
        failures.append(
            {
                'timestamp': timestamp,
                'notation': match.group('notation'),
                'subcommand': None,
                'exit_code': exit_code,
                'stderr': stderr,
            }
        )
    return failures


def classify_failure(failure: dict[str, Any]) -> tuple[str, str]:
    """Return ``(type, subtype)`` for a failure record.

    - exit_code == 2 with an argparse signature → anti-pattern + named subtype
    - exit_code == 2 with no recognized signature → anti-pattern + ``argparse_other``
    - exit_code != 2 (typically 1) → bug + ``script_internal_error``
    """
    code = failure.get('exit_code', 0)
    stderr = failure.get('stderr', '') or ''
    if code == 2:
        for needle, subtype in _ARGPARSE_SIGNATURES:
            if needle in stderr:
                return 'anti-pattern', subtype
        return 'anti-pattern', 'argparse_other'
    return 'bug', 'script_internal_error'


def dedupe_findings(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse failures into one finding per ``(notation, subtype)`` pair.

    The first occurrence's timestamp + stderr excerpt is retained as a
    representative sample; the rest contribute only to ``occurrence_count``.

    Ordering: insertion-order of first occurrence so the fragment is
    deterministic across runs with identical inputs.
    """
    grouped: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
    for failure in failures:
        ftype, subtype = classify_failure(failure)
        notation = failure.get('notation', '<unknown>')
        key = (notation, subtype)
        if key in grouped:
            grouped[key]['occurrence_count'] += 1
            continue
        # Truncate stderr to keep the TOON fragment small (operators read it
        # in compile-report; the full log is one click away).
        stderr_excerpt = (failure.get('stderr') or '').strip()
        if len(stderr_excerpt) > 200:
            stderr_excerpt = stderr_excerpt[:197] + '...'
        grouped[key] = {
            'type': ftype,
            'subtype': subtype,
            'component': notation,
            'subcommand': failure.get('subcommand') or '',
            'exit_code': failure.get('exit_code'),
            'first_timestamp': failure.get('timestamp', ''),
            'stderr_excerpt': stderr_excerpt,
            'occurrence_count': 1,
        }
    return list(grouped.values())


def build_seed_lessons(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Seed one lesson-fragment per ``(component, subtype)`` finding.

    The seed is a hint for the downstream ``manage-lessons`` recorder; the
    retrospective never writes lessons on its own. Title and category are
    deterministic functions of the subtype so the dedup-classification step
    in plan-retrospective Step 5a can recognise prior recurrences.
    """
    seeds: list[dict[str, Any]] = []
    for f in findings:
        subtype = f['subtype']
        title_map = {
            'invented_subcommand': f'Invented subcommand drift in {f["component"]}',
            'missing_required_flag': f'Missing required flag in {f["component"]} call',
            'invented_flag': f'Invented flag drift in {f["component"]} call',
            'argparse_other': f'Argparse rejection in {f["component"]} call',
            'script_internal_error': f'Script-internal error in {f["component"]}',
        }
        title = title_map.get(subtype, f'Script failure in {f["component"]}')
        category = 'anti-pattern' if f['type'] == 'anti-pattern' else 'bug'
        seeds.append(
            {
                'component': f['component'],
                'category': category,
                'title': title,
                'subtype': subtype,
                'occurrence_count': f['occurrence_count'],
            }
        )
    return seeds


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    exec_log_path = plan_dir / 'logs' / 'script-execution.log'
    work_log_path = plan_dir / 'logs' / 'work.log'

    exec_failures = parse_failures(read_log(exec_log_path))
    work_failures = parse_work_log_failures(read_log(work_log_path))

    # Merge both sinks before dedup so the within-log key (notation, subtype)
    # collapses a script-execution.log entry and a work.log entry for the same
    # notation + subtype into a single finding. script-execution.log entries
    # come first so they supply the representative sample on a tie.
    raw_failures = exec_failures + work_failures
    findings = dedupe_findings(raw_failures)
    lessons = build_seed_lessons(findings)

    plan_id = args.plan_id or Path(args.archived_plan_path or '').name
    return {
        'aspect': 'script-failure-analysis',
        'status': 'success',
        'plan_id': plan_id,
        'log_path': str(exec_log_path),
        'work_log_path': str(work_log_path),
        'total_failures': len(raw_failures),
        'unique_failures': len(findings),
        'findings': findings,
        'lessons': lessons,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Classify script-execution.log failures for plan-retrospective',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Analyze script failures', allow_abbrev=False)
    add_plan_id_arg(run_parser, required=False)
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
