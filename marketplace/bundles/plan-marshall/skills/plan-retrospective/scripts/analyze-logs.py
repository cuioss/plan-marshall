#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

from _footprint_resolver import (
    read_captured_footprint,
    resolve_merge_commit_footprint,
)
from _ledger_core import read_entries
from _references_core import (
    compute_plan_branch_diff,
    resolve_base_ref,
    resolve_live_worktree,
)
from file_ops import base_path, output_toon, safe_main
from input_validation import (
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
#
# This ceiling answers "is any single call pathological?" and NOTHING else. It is
# structurally blind to a script whose cost is a fraction of a percent of the
# ceiling repeated a hundred thousand times — that class is surfaced by the
# CUMULATIVE roll-up (``summarize_script_cost``) instead. The two are neighbours,
# not alternatives: changing this value redefines ``slow_call_count`` for every
# plan already measured against it, so the roll-up was added beside it rather
# than by moving it.
_GLOBAL_LOG_SLOW_SECONDS = 30.0

# How many scripts the cumulative roll-up ranks. The cap is never silent: the
# fragment publishes ``distinct_scripts`` and ``ranked_count`` beside the
# whole-population totals, so a truncated tail stays derivable.
_COST_ROLLUP_TOP_N = 10

# Test-fixture leak signatures: synthetic bundle/plan ids that must NEVER
# appear in a real plan's folded-in global log. Their presence means a test run
# wrote to the real logs instead of an isolated ``PLAN_BASE_DIR``.
_GLOBAL_LOG_FIXTURE_LEAK_RE = re.compile(
    r'\bfake-[a-z0-9-]*bundle\b|\bidem-bundle\b|\braising-bundle\b|\borphan-md-[a-z0-9-]+\b',
    re.IGNORECASE,
)


# A ledger row carries the bare execution-time ``plan_id``; an archived plan dir
# is named ``{YYYY-MM-DD}-{plan_id}``, so the date prefix is stripped when the
# plan key is derived from an archived path. A live plan_id has no prefix.
_LEDGER_DATE_PREFIX_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-')


def summarize_build_ledger(plan_key: str) -> dict[str, Any]:
    """Sum this plan's build time from the change-ledger — the build-time ORACLE.

    Reads the single append-only change-ledger
    (``<tracked-config>/work/change-ledger.jsonl``), keeps this plan's
    ``kind=build`` rows (matched on the bare ``plan_id``), and returns the plan's
    total build seconds plus the pass/error/timeout/killed status ratio. Because
    the ledger records ``command`` per build system and is written in every phase,
    the total spans EVERY build system and EVERY phase — not just the pyproject
    builds a plan happened to log.

    SUSPECT-ZERO rule: a row whose ``duration_seconds`` is ``0`` / absent /
    non-numeric is counted in ``suspect_count`` and is NOT summed into
    ``total_build_seconds`` — never averaged in as a fabricated zero. When
    ``suspect_count > 0`` the total is a FLOOR. ``killed`` is counted SEPARATELY
    from ``error`` (an infrastructure kill is not a red build). Best-effort: a
    plan with no ledger rows returns an all-zero block (``build_count: 0``), which
    the reader treats as "unavailable", never as "no builds ran".
    """
    status_keys = ('success', 'error', 'timeout', 'killed', 'unknown')
    status_counts = dict.fromkeys(status_keys, 0)
    total = 0.0
    build_count = 0
    suspect_count = 0
    for entry in read_entries():
        if entry.get('kind') != 'build' or entry.get('plan_id') != plan_key:
            continue
        build_count += 1
        status = entry.get('status')
        status_counts[status if status in status_counts else 'unknown'] += 1
        dur = entry.get('duration_seconds')
        if isinstance(dur, bool) or not isinstance(dur, (int, float)) or dur <= 0:
            suspect_count += 1
        else:
            total += float(dur)
    return {
        'total_build_seconds': round(total, 3),
        'build_count': build_count,
        'suspect_count': suspect_count,
        'pass': status_counts['success'],
        'error': status_counts['error'],
        'timeout': status_counts['timeout'],
        'killed': status_counts['killed'],
    }


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


def resolve_footprint(plan_dir: Path, plan_id: str | None = None) -> list[str]:
    """Resolve the plan footprint for the ARTIFACT-coverage regression check.

    Five-tier resolution, in order:

    1. **Live diff** — when ``plan_id`` names a live plan whose worktree the
       ONE resolver (:func:`_references_core.resolve_live_worktree`) resolves to
       a directory on disk, derive the footprint via ``compute_plan_branch_diff``
       (``{base}...HEAD`` ∪ porcelain).
    2. **Realized-footprint capture** — ``references.realized_footprint``, persisted
       by ``default:branch-cleanup`` while the worktree still existed. Primary tier
       for an archived plan; shared with the recall / mis-prune consumers through
       :func:`_footprint_resolver.read_captured_footprint`.
    3. **Merge-commit** — ``references.merge_commit_sha`` resolved via
       :func:`_footprint_resolver.resolve_merge_commit_footprint` (``git diff
       {sha}^1 {sha}``). A post-merge-only fallback below the deterministic capture.
    4. **Legacy key** — fall back to ``references.modified_files`` when present
       (archived plans created before the ledger was removed still carry it).
    5. **Empty** — when nothing resolves, return an empty list so the regression
       check cannot falsely fire for plans that recorded no footprint.

    Archived mode passes ``plan_id=None`` and therefore skips tier 1 entirely:
    an archived plan's recorded worktree names a directory finalize has already
    removed, so the tier could only ever miss. Tier 1 is reached through the
    resolver rather than by re-reading ``status.metadata.worktree_path`` here.

    A missing or unreadable references file is treated defensively, mirroring the
    other reads in the retrospective pipeline. This resolver keeps its own
    diff-failure policy — a tier-1 ``CalledProcessError`` falls THROUGH to the lower
    tiers rather than reporting unresolvable — so it composes the shared per-tier
    helpers rather than calling the whole-chain resolver.
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

    worktree = resolve_live_worktree(plan_id)
    if worktree is not None:
        base_ref = resolve_base_ref(None, refs)
        try:
            return sorted(compute_plan_branch_diff(worktree, base_ref))
        except subprocess.CalledProcessError:
            pass  # fall through to the recorded-footprint / legacy-key reads

    captured = read_captured_footprint(refs)
    if captured is not None:
        return sorted(captured)

    merge_set = resolve_merge_commit_footprint(plan_dir, refs)
    if merge_set is not None:
        return sorted(merge_set)

    # SHIM(B): archived plans' references.modified_files key, written before the change-ledger was removed.
    # shim-owner: plan-retrospective
    # shim-floor: the change-ledger removal that stopped persisting references.modified_files; the current writer no longer emits the key (predates this shallow clone's history root dcd3c00 / #1105, so not PR-pinnable here).
    # shim-remove-when: no archived plan predating the ledger removal is retained (i.e. such archives are purged/aged out).
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


def summarize_script_cost(
    durations: list[tuple[str, float]],
    population: str,
    *,
    ceiling_seconds: float = _GLOBAL_LOG_SLOW_SECONDS,
    top_n_scripts: int = _COST_ROLLUP_TOP_N,
) -> dict[str, Any]:
    """Roll ``(notation, duration_ms)`` pairs up into per-script CUMULATIVE cost.

    The per-call ceiling (``slow_call_count``) and the ``script_duration_*``
    percentiles answer *"is any single call pathological?"*. They are
    STRUCTURALLY incapable of answering *"what dominates total time?"*: a call at
    a fraction of a percent of the ceiling, repeated a hundred thousand times, is
    invisible to every one of them **by construction, not by oversight**. This
    roll-up answers the second question, and it is an ADDITION — the ceiling is
    untouched and both are reported.

    READ THE TWO TOGETHER via ``calls_at_or_over_ceiling``, published here over
    the SAME population as ``ranked``. A script ranked first with
    ``calls_at_or_over_ceiling: 0`` is exactly the dominant-but-fast class the
    ceiling cannot see; a script the ceiling flags that ranks low is a rare
    outlier rather than a cost centre. Neither reading is available from one
    instrument alone.

    ⛔ CURRENCY. Every figure here is WALL-CLOCK. It is NOT a billing share and
    does not convert into one: the script-execution log carries no per-call token
    measurement at all, so no share computed here can be restated in tokens
    without a measurement this corpus does not contain. A ranking from this
    roll-up is an operator-LATENCY finding. Saying otherwise is the
    partition-quoted-as-a-whole error this fragment exists to expose.

    ``population`` NAMES the corpus these figures count and is required rather
    than defaulted: a cumulative total is meaningless without it, and two
    roll-ups over different corpora must never be added or compared as one.

    ``ranked`` is capped at ``top_n_scripts`` and the cap is LEGIBLE — compare
    ``ranked_count`` against ``distinct_scripts``. ``total_calls`` and
    ``total_duration_ms`` always span the WHOLE population, so ``share_pct`` is a
    share of the published denominator and the truncated residual stays derivable.
    """
    call_counts: Counter[str] = Counter()
    cumulative: dict[str, float] = {}
    maxima: dict[str, float] = {}
    at_or_over_ceiling = 0
    ceiling_ms = ceiling_seconds * 1000.0

    for notation, ms in durations:
        call_counts[notation] += 1
        cumulative[notation] = cumulative.get(notation, 0.0) + ms
        maxima[notation] = max(maxima.get(notation, 0.0), ms)
        if ms >= ceiling_ms:
            at_or_over_ceiling += 1

    total_duration_ms = round(sum(cumulative.values()), 3)
    # Deterministic ordering: cumulative DESC, then notation ASC to break ties.
    ordered = sorted(cumulative, key=lambda n: (-cumulative[n], n))

    ranked: list[dict[str, Any]] = []
    for notation in ordered[:top_n_scripts]:
        script_ms = round(cumulative[notation], 3)
        ranked.append(
            {
                'notation': notation,
                'calls': call_counts[notation],
                'cumulative_ms': script_ms,
                # Computed from the ROUNDED figures this fragment publishes, so a
                # reader recomputing the share from the printed columns gets the
                # printed share back rather than a near-miss.
                'share_pct': (
                    round(script_ms / total_duration_ms * 100.0, 3) if total_duration_ms > 0 else 0.0
                ),
                'max_ms': round(maxima[notation], 3),
            }
        )

    return {
        'population': population,
        'ceiling_seconds': ceiling_seconds,
        'calls_at_or_over_ceiling': at_or_over_ceiling,
        'total_calls': sum(call_counts.values()),
        'total_duration_ms': total_duration_ms,
        'distinct_scripts': len(cumulative),
        'ranked_count': len(ranked),
        'ranked': ranked,
    }


def summarize_context_position_cost(
    per_phase: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Report cached-read cost per tool use BY PHASE — cost as a function of POSITION.

    Marginal cost scales with WHERE a step runs, not only with what it does: the
    same mechanical step late in a long phase re-reads a far larger accumulated
    context than it does early. A per-call view cannot see this, because the call
    is identical in both places — only its position differs. Phase is the
    coarsest honest proxy for position available from the dispatch-boundary
    artifacts, which are written per phase.

    The rate is WEIGHTED (``sum(cache_read) / sum(tool_uses)`` across the
    contributing rows), not a mean of per-row ratios: a dispatch with 200 tool
    uses must not weigh the same as one with 2.

    POPULATION DISCIPLINE. A dispatch-boundary row carries
    ``cache_read_input_tokens`` only when the writer MEASURED it — the reader
    omits the key for unmeasured, unrecognised and indeterminate cells alike (see
    ``_parse_dispatch_boundary_file``). Such a row is EXCLUDED and counted in
    ``unmeasured_rows``; it is never folded in as a zero, which would silently
    understate every rate it touched. A row with ``tool_uses == 0`` yields no
    per-tool-use rate either — undefined, not zero — and is excluded the same way.

    This publishes the DIMENSION and asserts no figure. Where a phase, or the
    whole corpus, has no measured row, the rate is the literal
    ``unmeasured`` token rather than a ``0.0`` a reader could mistake for a
    measurement.

    Returned dict shape:
      - total_rows / measured_rows / unmeasured_rows: the population, always
        published so a rate is never read without its denominator.
      - by_phase: list of {phase, rows, measured_rows, cache_read_per_tool_use},
        phase-ordered. ``cache_read_per_tool_use`` is a float or ``unmeasured``.
      - position_multiple: highest phase rate / lowest phase rate — the
        position effect expressed as a multiple. Requires at least TWO phases
        with a measured rate; one phase is not a position signal, so it reports
        ``unmeasured``.
      - position_multiple_basis: ``{highest_phase}/{lowest_phase}`` naming the
        two phases the multiple compares, so the figure cannot be quoted without
        its endpoints.
    """
    by_phase: list[dict[str, Any]] = []
    total_rows = 0
    measured_rows = 0

    for phase in sorted(per_phase):
        rows = per_phase[phase].get('rows') or []
        total_rows += len(rows)
        cache_read_sum = 0
        tool_use_sum = 0
        phase_measured = 0
        for row in rows:
            # An ABSENT key is never a zero — see the population discipline above.
            if 'cache_read_input_tokens' not in row:
                continue
            tool_uses = row.get('tool_uses') or 0
            if tool_uses <= 0:
                continue
            cache_read_sum += row['cache_read_input_tokens']
            tool_use_sum += tool_uses
            phase_measured += 1
        measured_rows += phase_measured
        by_phase.append(
            {
                'phase': phase,
                'rows': len(rows),
                'measured_rows': phase_measured,
                'cache_read_per_tool_use': (
                    round(cache_read_sum / tool_use_sum, 3)
                    if tool_use_sum > 0
                    else _UNMEASURED_COLUMN_TOKEN
                ),
            }
        )

    rated = [
        (row['phase'], row['cache_read_per_tool_use'])
        for row in by_phase
        if row['cache_read_per_tool_use'] != _UNMEASURED_COLUMN_TOKEN
    ]
    position_multiple: Any = _UNMEASURED_COLUMN_TOKEN
    position_multiple_basis: str = _UNMEASURED_COLUMN_TOKEN
    if len(rated) >= 2:
        highest_phase, highest_rate = max(rated, key=lambda pair: pair[1])
        lowest_phase, lowest_rate = min(rated, key=lambda pair: pair[1])
        if lowest_rate > 0:
            position_multiple = round(highest_rate / lowest_rate, 3)
            position_multiple_basis = f'{highest_phase}/{lowest_phase}'

    return {
        'total_rows': total_rows,
        'measured_rows': measured_rows,
        'unmeasured_rows': total_rows - measured_rows,
        'by_phase': by_phase,
        'position_multiple': position_multiple,
        'position_multiple_basis': position_multiple_basis,
    }


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
    """Cluster the literal execute-phase MARKER lines to infer dispatch boundaries.

    Returns a dict with:
      - inferred_dispatches: number of time-separated MARKER clusters (a cluster
            is a contiguous run of `Starting`/`Re-entering execute phase` marker
            lines whose timestamps are all within `gap_threshold_s` of the
            previous marker in the run).
      - starting_markers: count of `[STATUS] ... Starting execute phase` lines.
      - re_entering_markers: count of `[STATUS] ... Re-entering execute phase` lines.

    The cluster count gives the LLM rule a way to flag plans where the
    orchestrator re-dispatched the per-task `phase-5-execute` envelope more times
    than there are Re-entering markers (the symptom of D2's re-entry logging
    being skipped).

    Only a line matching `_STARTING_RE` or `_RE_ENTERING_RE` contributes a
    timestamp. Admitting every line merely CONTAINING the substring
    `plan-marshall:phase-5-execute` inflated the count roughly 6x-18x, because
    `work.log` is dense with unrelated `[STATUS]` / `[OUTCOME]` /
    `[MANAGE-TASKS]` / title-token lines carrying that caller tag and spaced more
    than the gap threshold apart during normal execution.

    Both counts are real dispatch signals. `phase-5-execute/SKILL.md` Step 4
    emits the `Starting execute phase` line exactly once per plan — on first
    entry, paired indivisibly with the `metadata.phase_5_first_entry_logged`
    marker write — and the `Re-entering execute phase` line on every subsequent
    re-dispatch. So `starting_markers` counts the first entry and
    `re_entering_markers` counts the re-dispatches, and the consuming
    `RE_ENTRY_COVERAGE` rule can read them as facts rather than as a
    logging-discipline artefact.

    `script_log_lines` stays in the signature for caller compatibility but is
    deliberately NOT scanned. The marker lines are emitted only into `work.log`,
    and `work_log_lines` is the sole population the `starting_markers` /
    `re_entering_markers` counts below are computed from — so admitting the
    script-log lines into the timestamp scan would let a marker-shaped line
    landing in `script-execution.log` change `inferred_dispatches` while staying
    invisible to those counts, i.e. produce a dispatch fact no marker count can
    corroborate. Scanning one population for all three outputs makes that
    divergence structurally impossible rather than merely unlikely.
    """
    timestamps: list[float] = []
    for line in work_log_lines:
        # Only the two literal execute-phase markers delimit a dispatch.
        if not (_STARTING_RE.search(line) or _RE_ENTERING_RE.search(line)):
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


def artifact_emission_population(
    work_log_lines: list[str], plan_dir: Path
) -> dict[str, Any]:
    """Publish per-task ARTIFACT emission as a POPULATION, not a non-zero floor.

    Per-task ``[ARTIFACT] (plan-marshall:phase-5-execute:{N}) Wrote {path}`` lines
    are hand-emitted at task completion, one per changed file, and a completed
    task with an empty diff emits none by design. A count-based guard
    (``artifact_entries == 0``) is therefore a FLOOR: it fires only when the whole
    plan emitted zero and is satisfied by any single artifact even when most
    completed tasks emitted nothing. That partiality reads to a consumer as "few
    artifacts produced" when the real signal may be "emission was bypassed" — a
    count-based detector cannot guard a per-item emission defect.

    This states BOTH numbers instead — ``N of M completed tasks emitted >= 1
    [ARTIFACT] line`` — so a consumer cannot read a partial count as a total.
    ``M`` (``completed_tasks``) is the completed-task population (task files with
    ``status: done``); ``N`` (``tasks_with_artifacts``) is the subset carrying at
    least one per-task artifact line. Tasks are keyed by their numeric id so the
    ``TASK-007`` file matches an ``…:7)`` caller regardless of zero-padding.
    """
    done_task_nums: set[int] = set()
    tasks_dir = plan_dir / 'tasks'
    if tasks_dir.exists():
        for task_path in sorted(tasks_dir.glob('TASK-*.json')):
            try:
                task_data = json.loads(task_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            if task_data.get('status') != 'done':
                continue
            num_match = re.search(r'TASK-(\d+)', task_path.stem)
            if num_match:
                done_task_nums.add(int(num_match.group(1)))

    artifact_task_nums: set[int] = set()
    for line in work_log_lines:
        match = _ARTIFACT_TASK_RE.search(line)
        if match:
            artifact_task_nums.add(int(match.group(1)))

    emitted = done_task_nums & artifact_task_nums
    missing = sorted(done_task_nums - artifact_task_nums)
    return {
        'completed_tasks': len(done_task_nums),
        'tasks_with_artifacts': len(emitted),
        'tasks_without_artifacts': [f'TASK-{num:03d}' for num in missing],
    }


# Dispatch-boundary row schema, consumed from the producer's declared contract.
#
# SOURCE OF TRUTH is `manage-metrics` `standards/data-format.md` § Per-Dispatch
# Context-Load Attribution — the legacy five columns, then these four appended
# at the END, and the literal an omitted context-load flag writes. This module
# runs in a different process from the writer and cannot import its constants,
# so these three are a hand-mirror of that section and MUST move with it.
#
# LOCK-STEP OBLIGATION. That section's "Restating surfaces (lock-step
# obligation)" paragraph names FOUR surfaces that restate this schema and must
# move together; this reader is one of them. The other three are the writer in
# `manage-metrics.py` (`cmd_record_dispatch_boundary` +
# `_DISPATCH_CONTEXT_LOAD_COLUMNS`), the `record-dispatch-boundary` operation
# block in `manage-metrics/SKILL.md`, and the hand-copied `_BC_LEDGER_COLUMNS` /
# `_BC_LEDGER_UNMEASURED_TOKEN` pair in
# `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`. That last
# one lives in a tree the architecture inventory does not crawl, so a content
# sweep will NOT find it — changing the schema here means editing all four by
# reading the list, never by searching.
_LEGACY_COLUMN_COUNT = 5
_CONTEXT_LOAD_COLUMNS = (
    'input_tokens',
    'output_tokens',
    'cache_read_input_tokens',
    'cache_creation_input_tokens',
)
_UNMEASURED_COLUMN_TOKEN = 'unmeasured'

# Termination-cause classes for the terminal-error vs retryable dispatch-spend
# split (plan 070-dispatch-spend-on-dispatches-that-produced-nothing). A
# findings-bearing loop-back is now stamped `returned_with_findings` — a
# PRODUCTIVE non-completion — so what remains under `error` is terminal-error
# spend. That is the strongest *proxy* for genuinely-wasted spend, NOT a proof of
# it: whether an error dispatch produced nothing is a finding-yield question, and
# confirming it against archived records is the corpus-gated D3 measurement — not
# asserted here. Retryable / infrastructure terminations are reported DISTINCTLY
# from the terminal-error spend because the two need different remedies — a
# session-restart block is infrastructure a re-run recovers, whereas a fatal
# error may be deterministic — and conflating them produces a fix for the wrong
# half.
_TERMINAL_WASTE_CAUSES = ('error',)
_RETRYABLE_CAUSES = ('blocked_session_restart', 'harness_cancellation')
_RETURNED_WITH_FINDINGS_CAUSE = 'returned_with_findings'


def _parse_dispatch_boundary_file(artifact: Path) -> dict[str, Any]:
    """Parse a single ``metrics-dispatch-boundaries-{phase}.toon`` artifact.

    Accepts BOTH the legacy five-column rows AND the widened nine-column rows
    that ``manage-metrics record-dispatch-boundary`` writes once the four
    per-dispatch context-load columns are appended. The length guard is a floor
    (``len(parts) < 5``) rather than a strict equality so a widened row is no
    longer silently dropped. The canonical column order / count / unmeasured
    representation are owned by ``manage-metrics``
    ``standards/data-format.md`` (Per-Dispatch Context-Load Attribution
    section); this reader consumes that contract.

    **The four context-load columns read FOUR ways, never two.** The writer
    distinguishes a measured value from a deliberately-unmeasured column, so
    this reader must preserve that distinction rather than folding either into a
    ``0``:

    * an integer cell — MEASURED, with one gate below for a literal ``0``.
      Carried as an int.
    * the literal ``unmeasured`` — recognised, and deliberately not measured.
      The key is OMITTED from the row dict; the column name is listed in the
      row's ``unmeasured_columns``.
    * anything else, and a column a short row does not have — UNRECOGNISED. The
      key is omitted too, but the column name is listed in the row's
      ``unrecognised_columns``, which is a different fact: the writer made a
      statement this reader failed to parse, rather than declining to measure.
    * a literal ``0`` the reader cannot date — INDETERMINATE. The pre-token
      writer defaulted every omitted context-load column to a literal ``0``, so
      "measured zero" and "wrote 0 because it had nothing" are byte-identical.
      The reader dates the row by a post-token FINGERPRINT — an ``unmeasured``
      token (only the current writer emits it) or a nonzero context-load cell
      ("nothing to measure" never yields one). A ``0`` in a row carrying either
      is a genuine measured zero and stays ``0``; a ``0`` in a row carrying
      NEITHER cannot be dated, so its key is OMITTED and the column is listed in
      the row's ``indeterminate_columns`` — distinct from ``unmeasured`` (the
      writer said so) and ``unrecognised`` (the reader could not parse it).

    A LEGACY five-column row (written before the columns existed) reports all
    four as **unmeasured** — it recorded no context-load measurement at all — and
    still parses, preserving the ``len(parts) < 5`` floor. A malformed appended
    cell reports as **unrecognised** and does not drop the whole row.

    Returned dict shape:
      - present: bool
      - rows: list of {timestamp, termination_cause, total_tokens, tool_uses,
            duration_ms, unmeasured_columns, unrecognised_columns,
            indeterminate_columns} plus one key per MEASURED context-load
            column. A consumer testing for a context-load value MUST test for the
            key's presence — an absent key is never a zero, and a column named in
            ``indeterminate_columns`` is never a measured zero either.
      - unknown_count: number of rows with ``termination_cause == "unknown"``
      - clean_exit_queue_empty_count: number of rows with
            ``termination_cause == "clean_exit_queue_empty"``
      - returned_with_findings_count: number of rows with
            ``termination_cause == "returned_with_findings"`` — the PRODUCTIVE
            loop-back population (a dispatch that returned findings and looped
            back), the opposite of wasted spend.
      - error_total_tokens: sum of ``total_tokens`` over terminal-error
            (``error``) rows — the terminal-error dispatch spend, a reported
            figure rather than a derivable one. Post-D1 (productive loop-backs
            are stamped ``returned_with_findings``, not ``error``) this is the
            strongest proxy for genuinely-wasted spend; a finding-yield
            confirmation that these rows produced nothing is the corpus-gated D3
            measurement, not asserted by this sum.
      - retryable_total_tokens: sum of ``total_tokens`` over RETRYABLE /
            infrastructure terminations (``blocked_session_restart`` +
            ``harness_cancellation``), reported DISTINCTLY from
            ``error_total_tokens`` because the two need different remedies.
    """
    if not artifact.is_file():
        return {
            'present': False,
            'rows': [],
            'unknown_count': 0,
            'clean_exit_queue_empty_count': 0,
            'returned_with_findings_count': 0,
            'error_total_tokens': 0,
            'retryable_total_tokens': 0,
        }

    try:
        content = artifact.read_text(encoding='utf-8')
    except OSError:
        return {
            'present': False,
            'rows': [],
            'unknown_count': 0,
            'clean_exit_queue_empty_count': 0,
            'returned_with_findings_count': 0,
            'error_total_tokens': 0,
            'retryable_total_tokens': 0,
        }

    rows: list[dict[str, Any]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(('plan_id:', 'phase:', 'rows[]')):
            continue
        parts = stripped.split(',')
        # Floor, not equality: a row with at least the five legacy columns parses.
        # Widened nine-column rows (legacy five + four appended context-load
        # columns) parse too rather than being silently dropped by the old
        # strict ``!= 5`` guard.
        # SHIM(B): legacy five-column dispatch-boundary rows, written before the four context-load columns were appended.
        # shim-owner: plan-retrospective
        # shim-floor: the record-dispatch-boundary column widening that appended the four per-dispatch context-load columns (input/output/cache_read/cache_creation) after the original five columns; the widening predates this shallow clone's root (dcd3c00 / #1105), and #1129 later refined those columns to distinguish unmeasured from a measured zero.
        # shim-remove-when: no dispatch-boundary log with five-column rows remains.
        if len(parts) < 5:
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
        # Read the four appended context-load columns — measured / unmeasured /
        # unrecognised / INDETERMINATE — per column, independently. Per-column
        # rather than per-row: a row whose third appended cell is corrupt still
        # carries two perfectly good measurements, and the old all-or-nothing
        # except-block discarded them along with the corrupt one.
        #
        # A literal `0` needs a ROW-LEVEL provenance gate, because the bytes on
        # disk are IDENTICAL for "measured zero" and "wrote 0 because the column
        # was never measured": the pre-token writer defaulted every omitted
        # context-load column to a literal `0`, so a nine-column pre-token row
        # reads as four measured zeros unless the reader can date it. There is no
        # out-of-band discriminator (D0's verdict) — the disambiguator is an
        # IN-band, post-token FINGERPRINT on the row itself: the `unmeasured`
        # token, which ONLY the current writer emits, or a nonzero context-load
        # cell, which "nothing to measure" never produces. A row carrying either
        # was demonstrably written by the current writer, so its literal `0`s are
        # genuine measured zeros (matches standards/data-format.md's row-3
        # example `…,9100,0,0,0` — three genuine measured zeros). A row carrying
        # NEITHER (every context-load cell a literal `0`, or `0`s beside
        # unrecognised cells) cannot be dated: its `0`s are INDETERMINATE — the
        # writer made no recoverable statement, so the reader asserts neither
        # "measured" nor "unmeasured". This is D0's no-discriminator verdict
        # surfaced per row (see standards/data-format.md § Per-Dispatch
        # Context-Load Attribution, "provenance of a measured zero").
        # First pass: measured (nonzero), unmeasured, and unrecognised are
        # decided per cell here — none of them depends on the rest of the row.
        # Only a literal `0` is deferred, because its verdict turns on whether
        # the WHOLE row carries a post-token fingerprint.
        unmeasured_columns: list[str] = []
        unrecognised_columns: list[str] = []
        indeterminate_columns: list[str] = []
        zero_columns: list[str] = []
        provably_post_change = False
        for offset, column in enumerate(_CONTEXT_LOAD_COLUMNS):
            index = _LEGACY_COLUMN_COUNT + offset
            if index >= len(parts):
                # A legacy five-column row carries no context-load measurement
                # at all. That is UNMEASURED, not a measured zero.
                unmeasured_columns.append(column)
                continue
            cell = parts[index].strip()
            if cell == _UNMEASURED_COLUMN_TOKEN:
                # The token is a writer-guaranteed post-token fingerprint.
                provably_post_change = True
                unmeasured_columns.append(column)
                continue
            try:
                value = int(cell)
            except ValueError:
                # A shape this reader does not recognise. Reported as such —
                # never defaulted, and never folded into any neighbour.
                unrecognised_columns.append(column)
                continue
            if value != 0:
                # A nonzero is a real measurement under any writer, and it dates
                # the row to the current writer.
                provably_post_change = True
                row[column] = value
            else:
                # A literal `0`; its provenance is decided in the second pass,
                # once the whole row's fingerprint is known.
                zero_columns.append(column)

        # Second pass over the deferred zeros. A `0` is a genuine measured zero
        # only when a post-token fingerprint (an `unmeasured` token or a nonzero
        # cell) dates the row to the current writer. Otherwise it cannot be
        # dated: reported as its own fourth state, INDETERMINATE — never folded
        # into `unmeasured` (a statement the writer made on purpose) nor read as
        # a measurement it never took.
        for column in zero_columns:
            if provably_post_change:
                row[column] = 0
            else:
                indeterminate_columns.append(column)
        row['unmeasured_columns'] = unmeasured_columns
        row['unrecognised_columns'] = unrecognised_columns
        row['indeterminate_columns'] = indeterminate_columns
        rows.append(row)

    unknown_count = sum(1 for row in rows if row['termination_cause'] == 'unknown')
    clean_exit_queue_empty_count = sum(
        1 for row in rows if row['termination_cause'] == 'clean_exit_queue_empty'
    )
    # The productive-loop-back population: dispatches that returned findings and
    # looped back. Counted so a reader can tell the productive dispatches apart
    # from the genuinely-wasted ones rather than reconstructing it from the rows.
    returned_with_findings_count = sum(
        1 for row in rows if row['termination_cause'] == _RETURNED_WITH_FINDINGS_CAUSE
    )
    # Genuinely-wasted (terminal) vs retryable (infrastructure) dispatch spend,
    # summed by cause-class and reported DISTINCTLY (never folded into one
    # "failure" figure) so the two, which need different remedies, stay separable.
    error_total_tokens = sum(
        row['total_tokens'] for row in rows if row['termination_cause'] in _TERMINAL_WASTE_CAUSES
    )
    retryable_total_tokens = sum(
        row['total_tokens'] for row in rows if row['termination_cause'] in _RETRYABLE_CAUSES
    )
    return {
        'present': True,
        'rows': rows,
        'unknown_count': unknown_count,
        'clean_exit_queue_empty_count': clean_exit_queue_empty_count,
        'returned_with_findings_count': returned_with_findings_count,
        'error_total_tokens': error_total_tokens,
        'retryable_total_tokens': retryable_total_tokens,
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
    ``"6-finalize"``) with each value carrying the per-file shape
    ``_parse_dispatch_boundary_file`` returns — see its "Returned dict shape"
    docstring for the authoritative key set (``present``, ``rows``, the per-cause
    counts, and the genuinely-wasted / retryable token sums). Enumerated there,
    not here, so this docstring does not drift when a key is added.

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

    Also returns ``cost_rollup`` — the CUMULATIVE per-script view over the SAME
    lines (see ``summarize_script_cost``). ``slow_call_count`` discards every
    duration below the ceiling, which makes it blind to a fast script called a
    great many times; the roll-up recovers exactly that information. Reporting
    both over one population is what lets them be read together.

    A plan with no folded-in global logs (live mode before finalize, pre-fold
    archives) yields all-zero counts, an empty ``cost_rollup`` and
    ``logs_present: false``.
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
    # Every timed call, kept for the cumulative roll-up below. The ceiling
    # consumes the same durations and discards all but the >= 30s ones, which is
    # precisely the information loss the roll-up exists to recover.
    folded_durations: list[tuple[str, float]] = []

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
                notation_match = _NOTATION_RE.search(rest)
                if notation_match:
                    folded_durations.append((notation_match.group(1), seconds * 1000.0))

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
        # The cumulative complement to ``slow_call_count``, over the SAME lines.
        # Same population is what makes the two readable together.
        'cost_rollup': summarize_script_cost(folded_durations, 'folded_global_logs'),
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

    footprint = resolve_footprint(plan_dir, args.plan_id if args.mode == 'live' else None)
    findings: list[dict[str, str]] = []
    if footprint and artifact_entries == 0:
        findings.append(
            {
                'severity': 'error',
                'message': (f'ARTIFACT entries missing: footprint={len(footprint)} but artifact_entries=0'),
            }
        )

    # Per-task ARTIFACT emission as a POPULATION statement (D4). The plan-level
    # ``artifact_entries == 0`` floor above cannot see per-task partiality — it is
    # satisfied by a single artifact even when most completed tasks emitted none.
    # Stating ``N of M completed tasks emitted`` makes that partiality legible so a
    # consumer cannot read a partial count as a total. The population is ALWAYS
    # published (below); the WARNING fires only for unambiguous partiality —
    # ``0 < N < M`` — where the per-task emitting path is demonstrably in use yet
    # incomplete. ``N == 0`` is left to the plan-level floor and the published
    # population (a plan may simply not use per-task emission), and ``N == M`` is
    # complete. The finding always carries both numbers, never a bare non-zero
    # assertion.
    artifact_emission = artifact_emission_population(work, plan_dir)
    if 0 < artifact_emission['tasks_with_artifacts'] < artifact_emission['completed_tasks']:
        missing_count = (
            artifact_emission['completed_tasks'] - artifact_emission['tasks_with_artifacts']
        )
        findings.append(
            {
                'severity': 'warning',
                'message': (
                    f'ARTIFACT_EMISSION_PARTIAL: {artifact_emission["tasks_with_artifacts"]} of '
                    f'{artifact_emission["completed_tasks"]} completed task(s) emitted >= 1 '
                    f'[ARTIFACT] line ({missing_count} emitted none). A completed task with an '
                    'empty diff legitimately emits nothing; a broad gap indicates the emitting '
                    'path was bypassed. See logging-gap-analysis.md § ARTIFACT_EMISSION.'
                ),
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

    # Build time from the change-ledger (the build-time ORACLE): the total spans
    # every build system and every phase, with the pass/error/timeout/killed ratio
    # (killed SEPARATE) and the suspect-zero rule applied. The plan_efficiency
    # aspect READS `total_build_seconds` from this block into its `totals`.
    plan_ledger_key = _LEDGER_DATE_PREFIX_RE.sub(
        '', args.plan_id or Path(args.archived_plan_path or '').name
    )
    build_time = summarize_build_ledger(plan_ledger_key)

    return {
        'status': 'success',
        'aspect': 'log_analysis',
        'plan_id': args.plan_id or Path(args.archived_plan_path or '').name,
        'build_time': build_time,
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
        'artifact_emission': artifact_emission,
        'phases_seen': extract_phases(work + decision),
        'script_duration_p50_ms': round(percentile(duration_values, 50.0), 3),
        'script_duration_p95_ms': round(percentile(duration_values, 95.0), 3),
        'script_duration_max_ms': round(max(duration_values) if duration_values else 0.0, 3),
        'slowest_scripts': [{'notation': notation, 'duration_ms': round(ms, 3)} for notation, ms in slowest],
        # Cumulative cost over the SAME lines the percentiles and
        # ``slowest_scripts`` summarise per-call. ``slowest_scripts`` ranks by
        # the largest SINGLE call; this ranks by total time owned, so a script
        # that never appears in ``slowest_scripts`` can top this list.
        'script_cost_rollup': summarize_script_cost(durations, 'plan_script_execution_log'),
        'top_tags': top_n(tag_counter, 5),
        'top_error_tags': top_n(error_tags, 5),
        'phase5_logging_gaps': phase5_logging_gaps,
        'dispatch_boundaries': dispatch_boundaries,
        # Cost as a function of context POSITION, derived from the same
        # dispatch-boundary rows. Reports the dimension with its population;
        # asserts no figure.
        'context_position_cost': summarize_context_position_cost(dispatch_boundaries),
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
    main()
