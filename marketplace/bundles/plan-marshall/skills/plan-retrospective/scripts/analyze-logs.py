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

Folded-in global logs: under the move-based finalize model the plan's OWN
global logs (``{prefix}-YYYY-MM-DD.log``) are folded into ``<plan_dir>/logs/``
at integrate-into-main. This script parses those folded-in copies for per-plan
operational signals (error/non-INFO lines, slow calls, fixture leaks) — a
per-plan complement to the cross-plan ``global-log-analysis`` audit check's
live-corpus correlation. A plan with no folded-in global logs (pre-fold archives, live mode
before finalize) yields all-zero signal counts.

Usage:
    python3 analyze-logs.py run --plan-id EXAMPLE-PLAN --mode live
    python3 analyze-logs.py run --archived-plan-path /abs/path --mode archived
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from _references_core import (  # type: ignore[import-not-found]
    compute_plan_branch_diff,
    resolve_base_ref,
)
from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
)

# Recognized log level tokens in the work/decision logs.
#
# This list is STRICT and intentionally aligned with the Python stdlib
# ``logging`` module's level names ("WARNING", not "WARN"). Historical log
# files written before the WARN→WARNING rename will contain bracketed
# ``[WARN]`` tokens and will therefore NOT be counted in ``warnings_*``
# fields. This is a deliberate breaking change: a green retrospective on a
# stale archive should reflect the current vocabulary, not silently sum
# values across two incompatible level tokens.
_LEVELS = ('INFO', 'WARNING', 'ERROR')

# Level tokens also appear as bracketed [LEVEL] tokens inside the production
# log shape; ``extract_tags`` filters them out so only category tags like
# [STATUS] / [ARTIFACT] / [VERIFY] surface in the counter.
_LEVEL_TOKENS = frozenset(_LEVELS)

# Regex to extract ``[TAG]`` square-bracket prefixes from work-log messages.
# Production work-log lines are shaped ``[ts] [LEVEL] [hash] [CATEGORY] ...``
# so a plain ``search`` returns ``LEVEL`` and never sees ``CATEGORY``; the
# consumers use ``findall`` and drop level tokens instead.
_TAG_RE = re.compile(r'\[([A-Z]+)\]')

# Regex for work/decision phase markers. Phase names match the 6-phase
# model (1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize).
_PHASE_RE = re.compile(r'plan-marshall:phase-(\d+-[a-z]+)')

# Regex for script-log duration fragments of the form ``(1.234s)``.
_DURATION_RE = re.compile(r'\((\d+\.?\d*)s\)')

# Regex for script-log notation extraction. Script log lines look like
# ``{TS} LEVEL {notation} {subcommand} (0.23s)``.
_NOTATION_RE = re.compile(r'([a-z][\w-]*:[\w-]+:[\w-]+)')

# Folded-in global-log line grammar — the bracketed
# ``[ts] [LEVEL] [hash] <rest>`` shape written by manage-logging into the
# date-stamped ``{prefix}-YYYY-MM-DD.log`` files folded into the plan dir at
# finalize. Mirrors the cross-plan global-log-analysis grammar.
_GLOBAL_LOG_LINE_RE = re.compile(
    r'^\[(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\]\s+'
    r'\[(?P<level>[A-Z]+)\]\s+\[(?P<hash>[0-9a-f]+)\]\s+(?P<rest>.*)$'
)

# Trailing ``(0.22s)`` script-call duration, anchored to end-of-line.
_GLOBAL_LOG_DUR_RE = re.compile(r'\(([0-9.]+)s\)\s*$')

# Body signals a failure even when the LEVEL cell is INFO (a script can exit
# non-zero while the logging wrapper stamps INFO).
_GLOBAL_LOG_FAIL_RE = re.compile(
    r'invalid choice|unrecognized arguments|the following arguments are required'
    r'|Traceback|exit[_ ]?code\s*[=:]?\s*[12]|argparse_rejection|\bError\b|\bfailed\b'
    r'|status:\s*error',
    re.IGNORECASE,
)

# Slow-call ceiling (seconds): a folded-in script call at/over this is slow.
_GLOBAL_LOG_SLOW_SECONDS = 30.0

# Test-fixture leak signatures: synthetic bundle/plan ids that must NEVER
# appear in a real plan's folded-in global log. Their presence means a test run
# wrote to the real logs instead of an isolated ``PLAN_BASE_DIR``.
_GLOBAL_LOG_FIXTURE_LEAK_RE = re.compile(
    r'\bfake-[a-z0-9-]*bundle\b|\bidem-bundle\b|\braising-bundle\b|\borphan-md-[a-z0-9-]+\b',
    re.IGNORECASE,
)


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


def resolve_logs_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan's ``logs/`` directory."""
    return resolve_plan_dir(mode, plan_id, archived_plan_path) / 'logs'


def resolve_footprint(plan_dir: Path) -> list[str]:
    """Resolve the plan footprint for the ARTIFACT-coverage regression check.

    Three-tier resolution, in order:

    1. **Live diff** — when ``status.metadata.worktree_path`` resolves to a git
       worktree on disk, derive the footprint via ``compute_plan_branch_diff``
       (``{base}...HEAD`` ∪ porcelain).
    2. **Legacy key** — fall back to ``references.modified_files`` when present
       (archived plans created before the ledger was removed still carry it).
    3. **Empty** — when neither resolves, return an empty list so the regression
       check cannot falsely fire for plans that recorded no footprint.

    A missing or unreadable references file is treated defensively, mirroring the
    other reads in the retrospective pipeline.
    """
    references_path = plan_dir / 'references.json'
    refs: dict = {}
    if references_path.exists():
        try:
            loaded = json.loads(references_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f'WARNING: analyze-logs failed to read references.json: {exc}',
                file=sys.stderr,
            )
            loaded = None
        if isinstance(loaded, dict):
            refs = loaded

    status_path = plan_dir / 'status.json'
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            status = {}
        if isinstance(status, dict):
            metadata = status.get('metadata', {})
            if isinstance(metadata, dict):
                worktree_path = metadata.get('worktree_path', '')
                if isinstance(worktree_path, str) and worktree_path:
                    worktree = Path(worktree_path)
                    if worktree.is_dir():
                        base_ref = resolve_base_ref(None, refs)
                        try:
                            return sorted(compute_plan_branch_diff(worktree, base_ref))
                        except subprocess.CalledProcessError:
                            pass  # fall through to the legacy-key read

    raw = refs.get('modified_files', [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(p).strip() for p in raw if p]


def read_log(path: Path) -> list[str]:
    """Return the non-empty lines of ``path``.

    A missing target file is surfaced as a stderr WARNING line so callers (and
    plan retrospectives) notice silent log-source drift, rather than treating
    an absent log as "no entries". OSError on read is treated the same way:
    the operator needs to know the input was unreadable, not get a green
    fragment with zero counts.
    """
    if not path.exists():
        print(
            f'WARNING: analyze-logs missing log file: {path}',
            file=sys.stderr,
        )
        return []
    try:
        content = path.read_text(encoding='utf-8')
    except OSError as exc:
        print(
            f'WARNING: analyze-logs failed to read log file {path}: {exc}',
            file=sys.stderr,
        )
        return []
    return [line for line in content.splitlines() if line.strip()]


def count_levels(lines: list[str]) -> dict[str, int]:
    """Count ``INFO``/``WARNING``/``ERROR`` occurrences across lines.

    Matches the bracketed production shape ``[LEVEL]`` emitted by
    ``manage-logging``. At most one level contributes per line.
    """
    counts = dict.fromkeys(_LEVELS, 0)
    for line in lines:
        for level in _LEVELS:
            if f'[{level}]' in line:
                counts[level] += 1
                break
    return counts


def extract_tags(lines: list[str]) -> list[str]:
    """Extract every category ``[TAG]`` occurrence across log lines.

    Production work-log lines carry multiple bracketed uppercase tokens
    (``[LEVEL]`` plus one or more ``[CATEGORY]`` tokens), so every match
    per line is collected and level tokens are filtered out afterwards.
    """
    tags: list[str] = []
    for line in lines:
        for tag in _TAG_RE.findall(line):
            if tag in _LEVEL_TOKENS:
                continue
            tags.append(tag)
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


# =============================================================================
# Phase-5 logging-gap fact extractors (lesson 2026-05-08-14-001)
# =============================================================================
#
# These extractors are pure fact-gathering: they count and pair, never judge.
# Judgement happens in the LLM rules in `references/logging-gap-analysis.md`.
# Each extractor returns a small dict whose shape is documented inline so the
# downstream rule application is unambiguous.

# Bracketed marker the `[OUTCOME]` work-log lines emitted by manage-tasks
# finalize-step (see manage-tasks/SKILL.md § "Script-Level [OUTCOME] Emission").
_OUTCOME_TASK_RE = re.compile(r'\[OUTCOME\]\s*\([^)]*\)\s*Completed\s+(TASK-\d+)')

# Bracketed marker for manage-tasks completion confirmations (one per task close).
_MANAGE_TASKS_COMPLETED_RE = re.compile(r'\[MANAGE-TASKS\]\s+Completed\s+(TASK-\d+)')

# Bracketed marker for the new "Re-entering execute phase" status line (D2).
_RE_ENTERING_RE = re.compile(
    r'\[STATUS\]\s*\(plan-marshall:phase-5-execute\)\s*Re-entering execute phase'
)

# Bracketed marker for the standard "Starting execute phase" status line.
_STARTING_RE = re.compile(
    r'\[STATUS\]\s*\(plan-marshall:phase-5-execute\)\s*Starting execute phase'
)

# `[ARTIFACT] (plan-marshall:phase-5-execute:{N})` — the three-segment caller
# is the documented exception for per-task artifact emission.
_ARTIFACT_TASK_RE = re.compile(
    r'\[ARTIFACT\]\s*\(plan-marshall:phase-5-execute:(\d+)\)'
)

# Production work-log lines start with an ISO-8601 timestamp inside square
# brackets, e.g. `[2026-05-08T14:23:11.123Z] [INFO] [hash] [STATUS] ...`.
_LINE_TIMESTAMP_RE = re.compile(r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\]')


def _parse_iso_seconds(timestamp: str) -> float | None:
    """Convert an ISO-8601 timestamp into UNIX seconds. Best-effort; returns None on failure."""
    from datetime import datetime

    try:
        cleaned = timestamp.replace('Z', '+00:00')
        return datetime.fromisoformat(cleaned).timestamp()
    except (ValueError, TypeError):
        return None


def pair_outcome_emissions(work_log_lines: list[str]) -> dict[str, Any]:
    """Pair `[OUTCOME]` lines with `[MANAGE-TASKS] Completed` confirmations.

    Returns a dict with three keys:
      - paired: number of TASK-NNN values present in BOTH outcome and completed sets
      - unpaired_completed: TASK-NNN ids present in [MANAGE-TASKS] Completed
            but missing from [OUTCOME] (the failure mode lesson 2026-05-08-14-001
            describes — the script-level guard fires but the orchestrator/agent
            failed to emit the [OUTCOME] line, OR vice versa on stale builds).
      - unpaired_outcome: TASK-NNN ids present in [OUTCOME] but missing from
            [MANAGE-TASKS] Completed (mostly happens on hand-emitted [OUTCOME]
            lines without a corresponding finalize-step call — an orchestrator
            anti-pattern).
    """
    outcomes: set[str] = set()
    for line in work_log_lines:
        match = _OUTCOME_TASK_RE.search(line)
        if match:
            outcomes.add(match.group(1))

    completed: set[str] = set()
    for line in work_log_lines:
        match = _MANAGE_TASKS_COMPLETED_RE.search(line)
        if match:
            completed.add(match.group(1))

    paired = outcomes & completed
    return {
        'paired': len(paired),
        'unpaired_completed': sorted(completed - outcomes),
        'unpaired_outcome': sorted(outcomes - completed),
    }


def cluster_dispatches(
    work_log_lines: list[str],
    script_log_lines: list[str],
    gap_threshold_s: float = 30.0,
) -> dict[str, Any]:
    """Cluster phase-5-execute dispatches by inter-line gap to infer dispatch boundaries.

    Returns a dict with:
      - inferred_dispatches: number of dispatch clusters detected (a cluster is
            a contiguous run of phase-5-related log lines whose timestamps are
            all within `gap_threshold_s` of the previous line in the run).
      - starting_markers: count of `[STATUS] ... Starting execute phase` lines.
      - re_entering_markers: count of `[STATUS] ... Re-entering execute phase` lines.

    The cluster count gives the LLM rule a way to flag plans where the
    orchestrator re-dispatched the per-task `phase-5-execute` envelope more times
    than there are Re-entering markers (the symptom of D2's re-entry logging
    being skipped).
    """
    timestamps: list[float] = []
    for line in work_log_lines + script_log_lines:
        # Restrict to lines that mention the phase-5-execute caller — non-phase-5-execute lines
        # do not contribute to phase-5-execute dispatch counting.
        if 'plan-marshall:phase-5-execute' not in line:
            continue
        ts_match = _LINE_TIMESTAMP_RE.search(line)
        if not ts_match:
            continue
        seconds = _parse_iso_seconds(ts_match.group(1))
        if seconds is None:
            continue
        timestamps.append(seconds)

    timestamps.sort()
    inferred = 0
    last_ts: float | None = None
    for ts in timestamps:
        if last_ts is None or (ts - last_ts) > gap_threshold_s:
            inferred += 1
        last_ts = ts

    starting = sum(1 for line in work_log_lines if _STARTING_RE.search(line))
    re_entering = sum(1 for line in work_log_lines if _RE_ENTERING_RE.search(line))

    return {
        'inferred_dispatches': inferred,
        'starting_markers': starting,
        're_entering_markers': re_entering,
    }


def detect_outcome_for_diffed_tasks(
    work_log_lines: list[str], plan_dir: Path
) -> dict[str, Any]:
    """For each task whose status is `done` in the persisted task files,
    decide whether an `[OUTCOME]` line was emitted. Pure counting — no
    judgement on whether absence is a defect.

    Returns:
      - tasks_with_diff_no_outcome: list of `TASK-NNN` ids that the persisted
            task state declares `status: done` AND for which no
            `[OUTCOME] (...) Completed TASK-NNN` line appears in `work.log`.

    The fact extractor cannot know the per-task git diff cheaply (the SHA
    range is not persisted in a stable place), so it uses the persisted task
    `status: done` as a proxy for "the task closed successfully and would have
    emitted [ARTIFACT] entries had its diff been non-empty". This is
    intentionally over-inclusive — the LLM rule applies the diff guard.
    """
    outcomes: set[str] = set()
    for line in work_log_lines:
        match = _OUTCOME_TASK_RE.search(line)
        if match:
            outcomes.add(match.group(1))

    done_tasks: set[str] = set()
    tasks_dir = plan_dir / 'tasks'
    if tasks_dir.exists():
        for task_path in sorted(tasks_dir.glob('TASK-*.json')):
            try:
                task_data = json.loads(task_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            if task_data.get('status') == 'done':
                # File names are TASK-NNN.json — strip the suffix.
                done_tasks.add(task_path.stem)

    missing = sorted(done_tasks - outcomes)
    return {'tasks_with_diff_no_outcome': missing}


def _parse_dispatch_boundary_file(artifact: Path) -> dict[str, Any]:
    """Parse a single ``metrics-dispatch-boundaries-{phase}.toon`` artifact.

    Returned dict shape (unchanged from the legacy phase-5-only reader):
      - present: bool
      - rows: list of {timestamp, termination_cause, total_tokens, tool_uses, duration_ms}
      - unknown_count: number of rows with ``termination_cause == "unknown"``
      - clean_exit_queue_empty_count: number of rows with
            ``termination_cause == "clean_exit_queue_empty"``
    """
    if not artifact.is_file():
        return {
            'present': False,
            'rows': [],
            'unknown_count': 0,
            'clean_exit_queue_empty_count': 0,
        }

    try:
        content = artifact.read_text(encoding='utf-8')
    except OSError:
        return {
            'present': False,
            'rows': [],
            'unknown_count': 0,
            'clean_exit_queue_empty_count': 0,
        }

    rows: list[dict[str, Any]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(('plan_id:', 'phase:', 'rows[]')):
            continue
        parts = stripped.split(',')
        if len(parts) != 5:
            continue
        try:
            row = {
                'timestamp': parts[0],
                'termination_cause': parts[1],
                'total_tokens': int(parts[2]),
                'tool_uses': int(parts[3]),
                'duration_ms': int(parts[4]),
            }
        except (ValueError, IndexError):
            continue
        rows.append(row)

    unknown_count = sum(1 for row in rows if row['termination_cause'] == 'unknown')
    clean_exit_queue_empty_count = sum(
        1 for row in rows if row['termination_cause'] == 'clean_exit_queue_empty'
    )
    return {
        'present': True,
        'rows': rows,
        'unknown_count': unknown_count,
        'clean_exit_queue_empty_count': clean_exit_queue_empty_count,
    }


_ATTEMPT_RE = re.compile(r'\[ATTEMPT\]')

# Genuine background-poll signal: a ``run_in_background=true`` (or
# ``run_in_background: true``) marker in a window line. This is the dispatch-then-
# poll anti-pattern's load-bearing signature — the agent launched a background task
# and is about to poll for it rather than waiting synchronously. The flag separator
# is either ``=`` or ``:`` and tolerates surrounding whitespace; the value is
# matched case-insensitively.
_RUN_IN_BACKGROUND_RE = re.compile(r'run_in_background\s*[=:]\s*true', re.IGNORECASE)

# Genuine background-poll signal: an ``until ... sleep ... done`` shell-loop shape
# spanning the window — the hand-rolled poll loop the voluntary-checkpoint rule is
# meant to catch. The three tokens must appear in order across the joined window
# text, with ``until`` and ``sleep`` and ``done`` all present.
_UNTIL_SLEEP_DONE_RE = re.compile(r'\buntil\b.*?\bsleep\b.*?\bdone\b', re.IGNORECASE | re.DOTALL)

# CI-wait exemptions: line shapes that contain a generic ``wait`` token but are
# legitimate SYNCHRONOUS CI waits, never voluntary-checkpoint polling. A window
# line matching either shape is skipped when scanning for a background-poll signal
# so it can neither trigger a candidate nor be confused for the poll-loop shape.
#   - ``ci checks wait``: the CI-abstraction synchronous wait invocation.
#   - ``ci_complete_precondition``: the work-log marker emitted around a synchronous
#     CI-completion gate.
_CI_WAIT_EXEMPT_RE = re.compile(r'ci\s+checks\s+wait|ci_complete_precondition', re.IGNORECASE)


def detect_voluntary_checkpoint_polling(work_log_lines: list[str]) -> dict[str, Any]:
    """Detect candidate [ATTEMPT] + background-poll consecutive-line pairs in work.log.

    Precondition: at least one ``[ATTEMPT]`` line must exist for the rule to fire.
    When the precondition is absent, ``precondition_met`` is False and
    ``polling_pairs_count`` is 0.

    A candidate pair fires ONLY when the 5-line window after an ``[ATTEMPT]`` line
    carries a GENUINE background-poll signal — a ``run_in_background=true`` marker in
    a window line, OR an ``until ... sleep ... done`` shell-loop shape spanning the
    window. A bare generic keyword (``wait``, ``background``, ``sleep``) with no such
    signal no longer triggers a candidate: those produced the false-positive class
    this detector was tightened to eliminate.

    CI-wait line shapes — ``ci checks wait`` invocations and the
    ``ci_complete_precondition`` work-log marker — are exempt: they contain the word
    ``wait`` but are legitimate synchronous CI waits, not voluntary-checkpoint
    polling. An exempt line is skipped when scanning the window so it cannot
    contribute to a candidate (neither as a poll signal nor as part of the
    ``until ... sleep ... done`` span).

    The extractor counts candidates only; downstream LLM rules apply judgement.

    Returns:
      - precondition_met: True when any ``[ATTEMPT]`` line exists in work_log_lines
      - polling_pairs_count: number of [ATTEMPT] lines whose window carries a genuine
            background-poll signal (CI-wait lines excluded)
      - candidate_line_numbers: 1-based indices of the [ATTEMPT] lines that triggered
            a candidate pair (for LLM inspection)
    """
    attempt_indices = [i for i, line in enumerate(work_log_lines) if _ATTEMPT_RE.search(line)]
    if not attempt_indices:
        return {
            'precondition_met': False,
            'polling_pairs_count': 0,
            'candidate_line_numbers': [],
        }

    candidates: list[int] = []
    for idx in attempt_indices:
        # Look at the next 5 lines (exclusive) for a genuine background-poll signal.
        window_end = min(idx + 6, len(work_log_lines))
        window = work_log_lines[idx + 1 : window_end]
        # Drop CI-wait lines before scanning — a legitimate synchronous CI wait
        # never contributes to a voluntary-checkpoint-polling candidate.
        non_exempt = [line for line in window if not _CI_WAIT_EXEMPT_RE.search(line)]
        if not non_exempt:
            continue
        # Per-line run_in_background=true marker, OR the until..sleep..done shape
        # spanning the joined (non-exempt) window text.
        if any(_RUN_IN_BACKGROUND_RE.search(line) for line in non_exempt) or _UNTIL_SLEEP_DONE_RE.search(
            '\n'.join(non_exempt)
        ):
            candidates.append(idx + 1)  # 1-based line number

    return {
        'precondition_met': True,
        'polling_pairs_count': len(candidates),
        'candidate_line_numbers': candidates,
    }


def read_dispatch_boundaries_per_phase(plan_dir: Path) -> dict[str, dict[str, Any]]:
    """Glob ``work/metrics-dispatch-boundaries-*.toon`` and parse each as a per-phase entry.

    The artifact filename ``metrics-dispatch-boundaries-{phase}.toon`` encodes
    the originating phase as the trailing path-stem segment. The returned dict
    is keyed by extracted phase name (e.g. ``"4-plan"``, ``"5-execute"``,
    ``"6-finalize"``) with each value carrying the same per-file shape as the
    legacy single-phase reader (``present``, ``rows``, ``unknown_count``,
    ``clean_exit_queue_empty_count``).

    An empty work directory produces an empty dict — the top-level
    ``dispatch_boundaries`` key surfaces in ``cmd_run`` output regardless,
    which is the structural signal that plan-retrospective discovered no
    boundary artifacts (vs. a structural error reading them).

    Generalised from the prior phase-5-only reader to cover phase-4-plan and
    phase-6-finalize dispatch-boundary artifacts as well (lesson
    `2026-05-20-12-002`).
    """
    work_dir = plan_dir / 'work'
    if not work_dir.exists():
        return {}

    per_phase: dict[str, dict[str, Any]] = {}
    for artifact in sorted(work_dir.glob('metrics-dispatch-boundaries-*.toon')):
        # ``metrics-dispatch-boundaries-{phase}.toon`` → extract ``{phase}``
        # from the stem by stripping the fixed prefix.
        stem = artifact.stem  # e.g. ``metrics-dispatch-boundaries-5-execute``
        prefix = 'metrics-dispatch-boundaries-'
        if not stem.startswith(prefix):
            continue
        phase = stem[len(prefix):]
        if not phase:
            continue
        per_phase[phase] = _parse_dispatch_boundary_file(artifact)

    return per_phase


def analyze_folded_global_logs(logs_dir: Path) -> dict[str, Any]:
    """Parse the plan's folded-in global logs for per-plan operational signals.

    Globs the date-stamped ``{script-execution,work,decision}-*.log`` files
    folded into ``<plan_dir>/logs/`` at finalize and surfaces per-plan signal
    counts: total lines parsed, error/non-INFO lines, slow calls
    (``>= _GLOBAL_LOG_SLOW_SECONDS``), and fixture leaks. This per-plan view
    complements the cross-plan ``global-log-analysis`` audit check (each plan's own
    signals are surfaced here from its folded-in copies, while the audit check
    does the cross-plan live-corpus correlation).

    A plan with no folded-in global logs (live mode before finalize, pre-fold
    archives) yields all-zero counts and ``logs_present: false``.
    """
    patterns = ('script-execution-*.log', 'work-*.log', 'decision-*.log')
    log_files: list[Path] = []
    if logs_dir.is_dir():
        for pat in patterns:
            log_files.extend(logs_dir.glob(pat))

    total_lines = 0
    error_count = 0
    slow_call_count = 0
    fixture_leak_count = 0
    fixture_leak_signatures: list[str] = []

    for log in sorted(log_files):
        try:
            content = log.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for raw in content.splitlines():
            match = _GLOBAL_LOG_LINE_RE.match(raw)
            if not match:
                continue
            total_lines += 1
            level = match.group('level')
            rest = match.group('rest')

            dur_match = _GLOBAL_LOG_DUR_RE.search(rest)
            if dur_match:
                try:
                    seconds = float(dur_match.group(1))
                except ValueError:
                    seconds = 0.0
                if seconds >= _GLOBAL_LOG_SLOW_SECONDS:
                    slow_call_count += 1

            if level != 'INFO' or _GLOBAL_LOG_FAIL_RE.search(rest):
                error_count += 1

            leak_match = _GLOBAL_LOG_FIXTURE_LEAK_RE.search(rest)
            if leak_match:
                fixture_leak_count += 1
                fixture_leak_signatures.append(leak_match.group(0))

    return {
        'logs_present': bool(log_files),
        'folded_log_files': len(log_files),
        'total_lines': total_lines,
        'error_count': error_count,
        'slow_call_count': slow_call_count,
        'fixture_leak_count': fixture_leak_count,
        'fixture_leak_signatures': sorted(set(fixture_leak_signatures)),
    }


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

    footprint = resolve_footprint(plan_dir)
    findings: list[dict[str, str]] = []
    if footprint and artifact_entries == 0:
        findings.append(
            {
                'severity': 'error',
                'message': (f'ARTIFACT entries missing: footprint={len(footprint)} but artifact_entries=0'),
            }
        )

    # Phase-5 logging-gap fact extractors (lesson 2026-05-08-14-001).
    # Pure counting/pairing — judgement lives in the LLM rules.
    voluntary_checkpoint_polling = detect_voluntary_checkpoint_polling(work)
    phase5_logging_gaps = {
        'outcome_pairing': pair_outcome_emissions(work),
        'dispatch_clustering': cluster_dispatches(work, script),
        'outcome_for_diffed_tasks': detect_outcome_for_diffed_tasks(work, plan_dir),
        'voluntary_checkpoint_polling': voluntary_checkpoint_polling,
    }

    # Surface a warning finding when the precondition is met and polling pairs exist.
    if (
        voluntary_checkpoint_polling['precondition_met']
        and voluntary_checkpoint_polling['polling_pairs_count'] > 0
    ):
        findings.append(
            {
                'severity': 'warning',
                'message': (
                    f"VOLUNTARY_CHECKPOINT_POLLING: {voluntary_checkpoint_polling['polling_pairs_count']} "
                    f"candidate [ATTEMPT]+polling-language pair(s) detected in work.log "
                    f"(lines: {voluntary_checkpoint_polling['candidate_line_numbers']}) — "
                    'agent may have dispatched a subagent then polled rather than running '
                    'synchronously. See logging-gap-analysis.md § VOLUNTARY_CHECKPOINT_POLLING.'
                ),
            }
        )

    # Per-phase dispatch-boundary artifacts (lesson 2026-05-20-12-002). The
    # generalised reader globs ``work/metrics-dispatch-boundaries-*.toon`` and
    # returns a per-phase dict keyed by phase name. It is hoisted to a
    # top-level fragment so the compile-report renderer can emit a dedicated
    # Phase Dispatch Boundaries section without descending into the phase-5
    # logging-gap bag.
    dispatch_boundaries = read_dispatch_boundaries_per_phase(plan_dir)

    # Folded-in global-log per-plan signals (a per-plan complement to the
    # cross-plan global-log-analysis audit check). Surfaces a finding
    # when the plan's own folded-in global logs carry error lines or fixture
    # leaks; slow-call counts ride the fragment for the LLM to weigh.
    global_log_signals = analyze_folded_global_logs(logs_dir)
    if global_log_signals['error_count'] > 0:
        findings.append(
            {
                'severity': 'warning',
                'message': (
                    f"GLOBAL_LOG_ERRORS: {global_log_signals['error_count']} error/non-INFO "
                    f"line(s) in the plan's folded-in global logs "
                    f"({global_log_signals['folded_log_files']} file(s)). "
                    'See log-analysis.md § Folded-in global logs.'
                ),
            }
        )
    if global_log_signals['fixture_leak_count'] > 0:
        findings.append(
            {
                'severity': 'error',
                'message': (
                    f"GLOBAL_LOG_FIXTURE_LEAK: {global_log_signals['fixture_leak_count']} synthetic "
                    f"test-fixture signature(s) leaked into the plan's folded-in global logs "
                    f"({';'.join(global_log_signals['fixture_leak_signatures'])}) — a test run wrote "
                    'to the real logs instead of an isolated PLAN_BASE_DIR.'
                ),
            }
        )

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
            'warnings_work': work_levels['WARNING'],
            'warnings_script': script_levels['WARNING'],
            'artifact_entries': artifact_entries,
        },
        'phases_seen': extract_phases(work + decision),
        'script_duration_p50_ms': round(percentile(duration_values, 50.0), 3),
        'script_duration_p95_ms': round(percentile(duration_values, 95.0), 3),
        'script_duration_max_ms': round(max(duration_values) if duration_values else 0.0, 3),
        'slowest_scripts': [{'notation': notation, 'duration_ms': round(ms, 3)} for notation, ms in slowest],
        'top_tags': top_n(tag_counter, 5),
        'top_error_tags': top_n(error_tags, 5),
        'phase5_logging_gaps': phase5_logging_gaps,
        'dispatch_boundaries': dispatch_boundaries,
        'global_log_signals': global_log_signals,
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
