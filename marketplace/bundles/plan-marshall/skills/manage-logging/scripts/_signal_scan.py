#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The deterministic script-failure scan behind lessons Signal 3.

``phase-6-finalize`` item 4b counts three marker classes and buckets each by
the distinct failing notation:

1. ``[FAILED]`` work-log lines — explicit failure markers.
2. ``[ERROR] ... script_failure`` work-log lines — the canonical per-call
   non-zero-exit marker emitted by the phase Error Handling sections.
3. B7 no-progress reclassifications — the DECISION-log line the orchestrator
   writes when the no-progress predicate reclassifies a
   ``voluntary_checkpoint`` return as ``error``.

Class 3 used to be looked for in the WORK log, while the writer has always
written it to the DECISION log — so a genuine reclassification was invisible
and the signal under-counted. The marker string below is the single statement
of what the writer emits and what this scanner matches; the writer's prose in
``plan-marshall/workflow/execution.md`` and the scanner's prose in
``phase-6-finalize/SKILL.md`` are doc-tested against it, so the two cannot
drift apart again.

A prescribed orchestrator-tier build hand-back (``termination_cause:
verification_handback``) is NOT lesson-bearing: the leaf did exactly what the
workflow told it to do. It is reported separately and never enters the count,
however many hand-back rows the phase carries — including a re-attach, which
writes two consecutive hand-back rows for the same task.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from file_ops import get_plan_dir

#: The exact marker the B7 writer emits and this scanner matches.
#:
#: The writer's full line is
#: ``(plan-marshall:phase-5-execute:no-progress) reclassified
#: voluntary_checkpoint as error — in_progress={N}, completed_delta={D},
#: tokens={X}``. Matching the marker (not the whole line) keeps the scanner
#: insensitive to the three predicate values it must not re-parse.
NO_PROGRESS_MARKER = 'reclassified voluntary_checkpoint as error'
NO_PROGRESS_SCOPE = 'plan-marshall:phase-5-execute'

#: The termination cause of a prescribed build hand-back. Named here so the
#: exclusion is stated once; the member itself is owned by
#: ``manage-metrics.DISPATCH_TERMINATION_CAUSES``.
VERIFICATION_HANDBACK_CAUSE = 'verification_handback'

_FAILED_MARKER = '[FAILED]'
_ERROR_MARKER = '[ERROR]'
_SCRIPT_FAILURE_MARKER = 'script_failure'

#: ``bundle:skill:script`` — the failing-notation token Signal 3 buckets by.
_NOTATION_RE = re.compile(r'\b([a-z0-9-]+):([a-z0-9-]+):([A-Za-z0-9_.-]+)\b')
#: The executor's structured ``notation=<bundle:skill:script>`` field. Preferred
#: over the generic scan because the marker line also carries the EXECUTOR's own
#: ``plan-marshall:execute-script:<exit_code>`` scope, which the generic pattern
#: would otherwise take first.
_NOTATION_FIELD_RE = re.compile(r'\bnotation=([a-z0-9-]+:[a-z0-9-]+:[A-Za-z0-9_.-]+)')

_DISPATCH_BOUNDARY_HEADER_RE = re.compile(r'^rows\[\d*\]\{(?P<columns>[^}]*)\}:')
_PHASE_5_BOUNDARY_SUFFIX = '5-execute'


def _read_lines(path: Path) -> list[str]:
    """Read a log file's non-empty lines, tolerating an absent file."""
    if not path.is_file():
        return []
    try:
        return [line for line in path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
    except OSError:
        return []


def _notation_of(line: str) -> str | None:
    """Return the ``bundle:skill:script`` token a line carries, or ``None``.

    An explicit ``notation=`` field wins: the executor's ``script_failure`` line
    also carries the executor's own ``plan-marshall:execute-script:<exit_code>``
    scope, which a generic first-match scan would report as the failing script.
    """
    field = _NOTATION_FIELD_RE.search(line)
    if field is not None:
        return field.group(1)
    match = _NOTATION_RE.search(line)
    if match is None:
        return None
    return f'{match.group(1)}:{match.group(2)}:{match.group(3)}'


def _boundary_cause_counts(path: Path) -> dict[str, int]:
    """Count ``termination_cause`` values in a dispatch-boundary artifact.

    The row shape is positional CSV under a ``rows[]{...}:`` header, so the
    cause column is resolved BY NAME from the declared header rather than
    assumed. A file with no header contributes nothing: nothing declares what
    its cells mean.
    """
    counts: dict[str, int] = {}
    columns: tuple[str, ...] = ()
    in_rows = False
    for line in _read_lines(path):
        header = _DISPATCH_BOUNDARY_HEADER_RE.match(line.strip())
        if header is not None:
            declared = tuple(name.strip() for name in header.group('columns').split(',') if name.strip())
            columns = declared
            in_rows = True
            continue
        if not in_rows or 'termination_cause' not in columns:
            continue
        parts = [cell.strip() for cell in line.strip().split(',')]
        index = columns.index('termination_cause')
        if index >= len(parts):
            continue
        cause = parts[index]
        if cause:
            counts[cause] = counts.get(cause, 0) + 1
    return counts


def scan_signal_3(plan_id: str) -> dict[str, Any]:
    """Scan one plan's logs for lessons Signal 3 and return the count payload.

    Returns:
      - ``signal_3_count``: distinct notations across the union of the three
            marker classes (a notation failing under more than one class counts
            once). Hand-back rows contribute nothing.
      - ``notations``: the distinct notations, sorted.
      - ``by_class``: per-class match counts (``failed``, ``script_failure``,
            ``no_progress_reclassification``).
      - ``unattributable_count``: marker-bearing lines with no parseable
            notation. Reported rather than silently dropped, and never counted
            toward ``signal_3_count`` — a count cannot name a notation it could
            not read.
      - ``boundary_cause_counts``: the phase-5 dispatch-boundary rows by cause,
            for evidence.
      - ``verification_handback_rows``: the hand-back row count (always
            excluded from the signal) — reported so a reader sees the excluded
            population rather than inferring it.
    """
    plan_dir = get_plan_dir(plan_id)
    work_lines = _read_lines(plan_dir / 'logs' / 'work.log')
    decision_lines = _read_lines(plan_dir / 'logs' / 'decision.log')
    boundary_path = plan_dir / 'work' / f'metrics-dispatch-boundaries-{_PHASE_5_BOUNDARY_SUFFIX}.toon'

    notations: set[str] = set()
    matched_by_class = {'failed': 0, 'script_failure': 0, 'no_progress_reclassification': 0}
    unattributable = 0

    def record(line: str, marker_class: str, is_decision: bool) -> None:
        nonlocal unattributable
        matched_by_class[marker_class] = matched_by_class[marker_class] + 1
        if is_decision:
            # The reclassification's failing notation is the dispatched workflow,
            # named by the marker's own scope token. Taken from the constant, not
            # re-parsed: the marker line's own ``…:no-progress`` suffix is not the
            # notation Signal 3 buckets by.
            notations.add(NO_PROGRESS_SCOPE)
            return
        notation = _notation_of(line)
        if notation is None:
            unattributable += 1
            return
        notations.add(notation)

    for line in work_lines:
        if _FAILED_MARKER in line:
            record(line, 'failed', is_decision=False)
        if _ERROR_MARKER in line and _SCRIPT_FAILURE_MARKER in line:
            record(line, 'script_failure', is_decision=False)

    for line in decision_lines:
        if NO_PROGRESS_MARKER in line:
            record(line, 'no_progress_reclassification', is_decision=True)

    boundary_counts = _boundary_cause_counts(boundary_path)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'signal_3_count': len(notations),
        'notations': sorted(notations),
        'by_class': matched_by_class,
        'unattributable_count': unattributable,
        'boundary_cause_counts': boundary_counts,
        'verification_handback_rows': boundary_counts.get(VERIFICATION_HANDBACK_CAUSE, 0),
    }
