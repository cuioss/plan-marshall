#!/usr/bin/env python3
"""Analyze ``work.log``, ``script-execution.log``, and ``decision.log`` for a plan.

Counts entries by level, phase, and tag; extracts script durations and
error-tag frequencies. Output is a deterministic TOON fragment consumed by
``compile-report.py`` and interpreted by ``references/log-analysis.md``.

Inputs:
- Live mode: logs are read from ``<plan_dir>/logs/`` (where plan_dir is
  resolved via ``base_path('plans', plan_id)``).
- Archived mode: logs are read from ``<archived_plan_path>/logs/``.

The script does NOT invoke ``manage-logging`` — it reads log files directly
because archived plans do not participate in the ``PLAN_BASE_DIR`` lookup
that ``manage-logging`` performs. Live mode produces the same values as
``manage-logging read`` would, keyed by the same file layout.

Usage:
    python3 analyze-logs.py run --plan-id my-plan --mode live
    python3 analyze-logs.py run --archived-plan-path /abs/path --mode archived
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]

# Recognized log level tokens in the work/decision logs.
_LEVELS = ('INFO', 'WARN', 'ERROR')

# Regex to extract ``[TAG]`` square-bracket prefixes from work-log messages.
_TAG_RE = re.compile(r'\[([A-Z]+)\]')

# Regex for work/decision phase markers. Phase names match the 6-phase
# model (1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize).
_PHASE_RE = re.compile(r'plan-marshall:phase-(\d+-[a-z]+)')

# Regex for script-log duration fragments of the form ``(1.234s)``.
_DURATION_RE = re.compile(r'\((\d+\.?\d*)s\)')

# Regex for script-log notation extraction. Script log lines look like
# ``{TS} LEVEL {notation} {subcommand} (0.23s)``.
_NOTATION_RE = re.compile(r'([a-z][\w-]*:[\w-]+:[\w-]+)')


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
    raise ValueError(f"Unknown mode: {mode!r}")


def resolve_logs_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan's ``logs/`` directory."""
    return resolve_plan_dir(mode, plan_id, archived_plan_path) / 'logs'


def read_modified_files(plan_dir: Path) -> list[str]:
    """Return the ``modified_files`` list from ``references.json``.

    A missing or unreadable references file is treated as an empty list so the
    regression check cannot falsely fire for plans that simply never recorded
    references. This mirrors the defensive reads elsewhere in the
    retrospective pipeline.
    """
    references_path = plan_dir / 'references.json'
    if not references_path.exists():
        return []
    try:
        refs = json.loads(references_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f'WARN: analyze-logs failed to read references.json: {exc}',
            file=sys.stderr,
        )
        return []
    raw = refs.get('modified_files', [])
    if isinstance(raw, str):
        raw = [raw]
    return [str(p).strip() for p in raw if p]


def read_log(path: Path) -> list[str]:
    """Return the non-empty lines of ``path``.

    A missing target file is surfaced as a stderr WARN line so callers (and
    plan retrospectives) notice silent log-source drift, rather than treating
    an absent log as "no entries". OSError on read is treated the same way:
    the operator needs to know the input was unreadable, not get a green
    fragment with zero counts.
    """
    if not path.exists():
        print(
            f'WARN: analyze-logs missing log file: {path}',
            file=sys.stderr,
        )
        return []
    try:
        content = path.read_text(encoding='utf-8')
    except OSError as exc:
        print(
            f'WARN: analyze-logs failed to read log file {path}: {exc}',
            file=sys.stderr,
        )
        return []
    return [line for line in content.splitlines() if line.strip()]


def count_levels(lines: list[str]) -> dict[str, int]:
    """Count ``INFO``/``WARN``/``ERROR`` occurrences across lines."""
    counts = dict.fromkeys(_LEVELS, 0)
    for line in lines:
        for level in _LEVELS:
            # Level tokens appear as whole words after the timestamp.
            if f' {level} ' in line:
                counts[level] += 1
                break
    return counts


def extract_tags(lines: list[str]) -> list[str]:
    """Extract every ``[TAG]`` prefix found in log lines."""
    tags: list[str] = []
    for line in lines:
        match = _TAG_RE.search(line)
        if match:
            tags.append(match.group(1))
    return tags


def extract_phases(lines: list[str]) -> list[str]:
    """Extract distinct phase identifiers referenced in log lines."""
    seen: set[str] = set()
    for line in lines:
        for match in _PHASE_RE.finditer(line):
            seen.add(match.group(1))
    return sorted(seen)


def extract_script_durations(lines: list[str]) -> list[tuple[str, float]]:
    """Parse script-log lines for ``(notation, duration_ms)`` tuples.

    Lines without a notation or a duration are skipped. Durations are
    returned in milliseconds for easier downstream percentile math.
    """
    out: list[tuple[str, float]] = []
    for line in lines:
        dur_match = _DURATION_RE.search(line)
        if not dur_match:
            continue
        notation_match = _NOTATION_RE.search(line)
        if not notation_match:
            continue
        try:
            seconds = float(dur_match.group(1))
        except ValueError:
            continue
        out.append((notation_match.group(1), seconds * 1000.0))
    return out


def percentile(values: list[float], pct: float) -> float:
    """Simple nearest-rank percentile implementation for stdlib-only use.

    Returns 0.0 for empty input so the fragment always contains numeric
    fields (easier for downstream consumers).
    """
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_vals = sorted(values)
    k = max(0, min(len(sorted_vals) - 1, int(round(pct / 100.0 * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def top_n(counter: Counter, n: int) -> list[dict[str, Any]]:
    """Return ``most_common(n)`` as a list of ``{tag, count}`` dicts."""
    return [{'tag': tag, 'count': count} for tag, count in counter.most_common(n)]


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    logs_dir = plan_dir / 'logs'

    work = read_log(logs_dir / 'work.log')
    decision = read_log(logs_dir / 'decision.log')
    script = read_log(logs_dir / 'script-execution.log')

    work_levels = count_levels(work)
    script_levels = count_levels(script)

    tags = extract_tags(work)
    tag_counter = Counter(tags)
    error_lines = [line for line in work if ' ERROR ' in line]
    error_tags = Counter(extract_tags(error_lines))
    artifact_entries = tag_counter.get('ARTIFACT', 0)

    durations = extract_script_durations(script)
    duration_values = [ms for _, ms in durations]
    # Build slowest-scripts list deterministically: sort by duration desc, then notation.
    slowest = sorted(durations, key=lambda x: (-x[1], x[0]))[:3]

    modified_files = read_modified_files(plan_dir)
    findings: list[dict[str, str]] = []
    if modified_files and artifact_entries == 0:
        findings.append({
            'severity': 'error',
            'message': (
                f'ARTIFACT entries missing: modified_files={len(modified_files)} '
                f'but artifact_entries=0'
            ),
        })

    return {
        'status': 'success',
        'aspect': 'log_analysis',
        'plan_id': args.plan_id or Path(args.archived_plan_path or '').name,
        'counts': {
            'work_entries': len(work),
            'decision_entries': len(decision),
            'script_entries': len(script),
            'errors_work': work_levels['ERROR'],
            'errors_script': script_levels['ERROR'],
            'warnings_work': work_levels['WARN'],
            'warnings_script': script_levels['WARN'],
            'artifact_entries': artifact_entries,
        },
        'phases_seen': extract_phases(work + decision),
        'script_duration_p50_ms': round(percentile(duration_values, 50.0), 3),
        'script_duration_p95_ms': round(percentile(duration_values, 95.0), 3),
        'script_duration_max_ms': round(max(duration_values) if duration_values else 0.0, 3),
        'slowest_scripts': [
            {'notation': notation, 'duration_ms': round(ms, 3)}
            for notation, ms in slowest
        ],
        'top_tags': top_n(tag_counter, 5),
        'top_error_tags': top_n(error_tags, 5),
        'findings': findings,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Analyze plan log files for retrospective facts',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Analyze logs', allow_abbrev=False)
    run_parser.add_argument('--plan-id', help='Plan identifier (live mode)')
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

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
