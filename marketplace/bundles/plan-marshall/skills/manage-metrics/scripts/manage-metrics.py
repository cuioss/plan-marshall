#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
CLI script for plan metrics collection and reporting.

Usage:
    Start phase timing:
        python3 manage-metrics.py start-phase --plan-id <id> --phase <phase>

    End phase timing:
        python3 manage-metrics.py end-phase --plan-id <id> --phase <phase> [--total-tokens N] [--duration-ms N] [--tool-uses N]

    Generate metrics.md:
        python3 manage-metrics.py generate --plan-id <id>

    Atomic phase boundary (end-phase + start-phase + generate):
        python3 manage-metrics.py phase-boundary --plan-id <id> \
            --prev-phase <prev> --next-phase <next> \
            [--total-tokens N] [--duration-ms N] [--tool-uses N]

    Accumulate per-phase subagent usage on disk:
        python3 manage-metrics.py accumulate-agent-usage --plan-id <id> --phase <phase> \
            [--total-tokens N] [--tool-uses N] [--duration-ms N] [--retrospective-tokens N]

    Enrich from JSONL transcript (per-phase subagent <usage>):
        python3 manage-metrics.py enrich --plan-id <id> --session-id <sid>
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from constants import FILE_STATUS, FILE_WORK_METRICS, PHASES
from file_ops import (
    PlanNotFoundError,
    atomic_write_file,
    format_duration,
    format_tokens_short,
    get_plan_dir,
    now_utc_iso,
    output_toon,
    require_plan_exists,
    safe_main,
)
from input_validation import (
    add_phase_arg,
    add_plan_id_arg,
    add_session_id_arg,
    is_valid_relative_path,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)
from toon_parser import parse_toon

METRICS_FILE = FILE_WORK_METRICS
METRICS_MD = 'metrics.md'
PHASE_BREAKDOWN_DEFAULT_OUTPUT = 'work/phase-breakdown-output.txt'
PHASE_NAMES = list(PHASES)
ACCUMULATOR_FILE_TEMPLATE = 'work/metrics-accumulator-{phase}.toon'
DISPATCH_BOUNDARY_FILE_TEMPLATE = 'work/metrics-dispatch-boundaries-{phase}.toon'
DISPATCH_TERMINATION_CAUSES = (
    'voluntary_checkpoint',
    'task_complete_returned_verbatim',
    'budget_yield',
    'harness_cancellation',
    'error',
    'clean_exit_queue_empty',
    'step_complete',
    'blocked_user_review',
    'blocked_session_restart',
    'task_batch_complete',
    'agent_returned',
)

# ---------------------------------------------------------------------------
# Token population discriminator
# ---------------------------------------------------------------------------
#
# ``total_tokens`` is named for a TOTAL, not for a population, yet the figure it
# carries is filled from two different measurements: a dispatched phase's
# ``<usage>`` envelopes, and — on a phase that dispatched nothing — the inline
# main-context sum that ``cmd_enrich`` folds in. The fold is deliberate and
# stays: it is what keeps an inline phase countable in the breakdown (the report
# reads n=6/6, not n=5/6) and what keeps every downstream zero-token predicate
# off a phase that really did cost something. What must NOT stay implicit is
# that the folded figure measures a DIFFERENT population than the field's name
# implies.
#
# ``total_tokens_population`` is that discriminator, persisted by ``cmd_enrich``
# on every phase row it touches so no render site and no consumer has to infer
# the population from a field name that does not state one.
POPULATION_DISPATCHED = 'dispatched'
POPULATION_INLINE = 'inline'
POPULATION_MIXED = 'mixed'
TOKEN_POPULATIONS = (POPULATION_DISPATCHED, POPULATION_INLINE, POPULATION_MIXED)

# Phase Breakdown ``Tokens`` cell suffix per population. ``dispatched`` renders
# bare and is declared as the column's default by the annotation under the
# table: marking every ordinary row would bury the rows that actually differ.
_POPULATION_CELL_SUFFIX = {
    POPULATION_INLINE: ' (inline)',
    POPULATION_MIXED: ' (mixed)',
}

# Phase Details ``Total tokens`` bullet qualifier per population. Every rendered
# total names its own population, so the bullet stays legible without reading
# the breakdown annotation first.
_POPULATION_BULLET_NOTE = {
    POPULATION_DISPATCHED: (
        "dispatched-subagent population — summed from the dispatched leaves' `<usage>` envelopes"
    ),
    POPULATION_INLINE: (
        'main-context-window population — this phase dispatched nothing, so enrich folded its '
        'inline main-context spend into this field; the same figure is recorded under its own '
        'population-honest name as inline_main_context_tokens'
    ),
    POPULATION_MIXED: (
        'dispatched-subagent population — this phase ALSO ran inline main-context steps, recorded '
        'separately as inline_main_context_tokens and NOT included here; the two populations are '
        'measured by different methods and are not additively comparable'
    ),
}


def _token_population(phase_row: dict) -> str:
    """Return the population this phase row's ``total_tokens`` figure measures.

    An un-enriched row carries no discriminator, and without ``enrich`` the only
    source ``total_tokens`` can have had is dispatched ``<usage>`` / the
    accumulator — so an ABSENT value reads as ``dispatched``. An unrecognised
    value reads the same way rather than rendering a marker no reader can
    interpret.
    """
    value = phase_row.get('total_tokens_population')
    return value if value in TOKEN_POPULATIONS else POPULATION_DISPATCHED


# ---------------------------------------------------------------------------
# Dispatched-population reconciliation
# ---------------------------------------------------------------------------
#
# THREE fields measure the same dispatched-subagent population by three
# independent routes, and they routinely disagree:
#
#   total_tokens           forwarded `<usage>` / the per-phase accumulator
#   dispatch_boundary_total sum of the per-dispatch boundary rows
#   subagent_total_tokens   enrich's post-hoc transcript walk
#
# Because they count the SAME leaves, they are reconciled by max(), never summed
# — a sum double-counts every leaf. The maximum recovers whichever route
# under-counted (#565: a leaf whose boundary row fired but whose accumulator fold
# was missed).
#
# The rule is applied SYMMETRICALLY to all three or to none. Comparing only two
# of them let the third exceed the rendered figure with the report never saying
# so. Two eligibility rules keep the comparison honest:
#
#   * A measure that cannot state its own coverage may not win. Only
#     `dispatch_boundary_total` can under-cover (its file may hold fewer rows
#     than the phase had dispatches), so it is refused the maximum when it is
#     PARTIAL.
#   * A measure of a DIFFERENT population may not enter at all. On an `inline`
#     row `total_tokens` carries a main-context measurement (see
#     `_token_population`), so it is excluded — putting it in a
#     dispatched-population max would be the very mislabel the discriminator
#     exists to prevent.
_DISPATCHED_MEASURE_FIELDS = (
    'total_tokens',
    'dispatch_boundary_total',
    'subagent_total_tokens',
)


def _boundary_measure_is_partial(phase_row: dict) -> bool | None:
    """Does ``dispatch_boundary_total`` under-cover the phase's dispatches?

    Compares the boundary file's row count against ``subagent_samples`` — the
    count of dispatch returns ``enrich``'s transcript walk attributed to the same
    window. Fewer boundary rows than dispatches means the sum covers only part of
    the population it claims to measure.

    Returns ``None`` when the coverage is UNDECIDABLE: a row carrying no
    ``subagent_samples`` was never walked by ``enrich``, so there is no reference
    count to compare against. Undecidable is deliberately NOT partial — treating
    it as partial would refuse the maximum on every un-enriched plan and lose the
    accumulator-under-count recovery the reconciliation exists for.
    """
    samples = phase_row.get('subagent_samples')
    if not isinstance(samples, int):
        return None
    rows = phase_row.get('dispatch_boundary_rows_recorded')
    if not isinstance(rows, int):
        return None
    return rows < samples


def _eligible_dispatched_measures(phase_row: dict) -> list[tuple[str, int]]:
    """Return the dispatched-population measures eligible for the maximum.

    Preserves ``_DISPATCHED_MEASURE_FIELDS`` order so an exact tie resolves
    deterministically to the earliest-declared measure.
    """
    population = _token_population(phase_row)
    boundary_partial = _boundary_measure_is_partial(phase_row)

    eligible: list[tuple[str, int]] = []
    for field in _DISPATCHED_MEASURE_FIELDS:
        value = _coerce_numeric(phase_row.get(field))
        if not isinstance(value, (int, float)) or not value:
            continue
        if field == 'total_tokens' and population == POPULATION_INLINE:
            continue
        if field == 'dispatch_boundary_total' and boundary_partial:
            continue
        eligible.append((field, int(value)))
    return eligible


def _reconcile_dispatched_measures(phase_row: dict) -> tuple[str, int] | None:
    """Return the ``(field, value)`` of the largest eligible dispatched measure.

    ``None`` when no measure is eligible — the inline-only row, whose single
    token figure belongs to another population and is rendered on its own.
    """
    eligible = _eligible_dispatched_measures(phase_row)
    if not eligible:
        return None
    return max(eligible, key=lambda item: item[1])


def _accumulator_path(plan_id: str, phase: str) -> Path:
    return get_plan_dir(plan_id) / ACCUMULATOR_FILE_TEMPLATE.format(phase=phase)


def _read_accumulator(plan_id: str, phase: str) -> dict[str, int]:
    """Read per-phase subagent-usage accumulator. Returns empty dict if absent or unparsable."""
    path = _accumulator_path(plan_id, phase)
    if not path.exists():
        return {}
    result: dict[str, int] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or ':' not in stripped:
            continue
        key, _, raw_val = stripped.partition(':')
        key = key.strip()
        if key not in {'total_tokens', 'tool_uses', 'duration_ms', 'samples', 'retrospective_tokens'}:
            continue
        try:
            result[key] = int(raw_val.strip())
        except ValueError:
            continue
    return result


def _write_accumulator(plan_id: str, phase: str, totals: dict[str, int]) -> None:
    path = _accumulator_path(plan_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f'plan_id: {plan_id}',
        f'phase: {phase}',
        f'total_tokens: {totals["total_tokens"]}',
        f'tool_uses: {totals["tool_uses"]}',
        f'duration_ms: {totals["duration_ms"]}',
        f'retrospective_tokens: {totals["retrospective_tokens"]}',
        f'samples: {totals["samples"]}',
        f'updated: {now_utc_iso()}',
    ]
    atomic_write_file(path, '\n'.join(lines) + '\n')


def _read_dispatch_boundary_totals(plan_id: str, phase: str) -> tuple[int, int]:
    """Sum the ``total_tokens`` column across a phase's dispatch-boundaries file.

    The dispatch-boundaries file (``work/metrics-dispatch-boundaries-{phase}.toon``)
    records one row per phase Task-dispatch termination, each carrying the
    dispatched agent's ``<usage>`` totals at return (see the writer in
    ``cmd_record_dispatch_boundary``). This reader sums the ``total_tokens``
    column — position 2 in the documented row schema
    ``rows[]{timestamp,termination_cause,total_tokens,...}`` — across every data
    row. The two header lines (``plan_id:`` / ``phase:``), the ``rows[]`` schema
    line, and any malformed / short row are skipped.

    Returns ``(total, rows_counted)``. The row count is returned alongside the
    sum because the sum ALONE cannot state its own coverage: a boundary file
    holding three of a phase's five dispatches sums to a smaller-but-honest-looking
    figure, and without the count nothing downstream can tell that measure apart
    from a complete one. ``rows_counted`` is what lets the reconciliation mark the
    measure PARTIAL and refuse it the maximum.

    Returns ``(0, 0)`` when the file is absent, empty, or carries no parseable
    row — the caller (``cmd_generate``) treats that as a clean no-op, so a plan
    that never recorded a dispatch boundary reconciles to nothing.

    Args:
        plan_id: Plan identifier.
        phase: Canonical phase name whose boundaries file is summed.

    Returns:
        ``(summed total_tokens, number of data rows summed)``.
    """
    path = _dispatch_boundary_path(plan_id, phase)
    if not path.exists():
        return 0, 0
    total = 0
    rows = 0
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(('plan_id:', 'phase:', 'rows[]')):
            continue
        columns = stripped.split(',')
        if len(columns) < 3:
            continue
        try:
            total += int(columns[2].strip())
        except ValueError:
            continue
        rows += 1
    return total, rows


def _resolve_token_field(
    arg_value: int | None, accumulator: dict[str, int], key: str
) -> tuple[int | None, str | None]:
    """Resolve a usage field to its value AND its provenance.

    Explicit flag wins; fall back to the accumulator value when the flag is
    absent. The provenance half is what makes correct accumulation expressible
    at the write site, because the two sources carry different arithmetic:

    - ``'flag'`` — an explicit ``--total-tokens``-style value is a **per-close
      delta**. On a phase re-entry it must be ADDED to whatever the row already
      holds (see ``_apply_provenance``).
    - ``'accumulator'`` — the on-disk per-phase accumulator is **already
      cumulative** (``cmd_accumulate_agent_usage`` only ever sums and no verb
      resets it), so it must be ASSIGNED unchanged. Adding it would double-count
      every re-close.

    Returns:
        ``(value, source)`` where ``source`` is ``'flag'`` or ``'accumulator'``;
        ``(None, None)`` when neither source carries the field, which the write
        sites treat as "leave the row untouched" (never write a ``0``).
    """
    if arg_value is not None:
        return arg_value, 'flag'
    if key in accumulator:
        return accumulator[key], 'accumulator'
    return None, None


def _row_int(phase_data: dict, key: str) -> int:
    """Return a phase row's integer field, treating absent / non-numeric as 0."""
    value = phase_data.get(key)
    return int(value) if isinstance(value, (int, float)) else 0


def _apply_provenance(phase_data: dict, row_key: str, value: int, source: str | None) -> int:
    """Combine a resolved usage value with the row's existing value by provenance.

    The accumulate-on-re-entry rule for the token/tool fields: a ``'flag'``-sourced
    value is a per-close delta and is added to what the row already holds (absent
    treated as 0); any other provenance (``'accumulator'``) is already the
    cumulative total and is returned unchanged. Callers assign the result.
    """
    if source == 'flag':
        return _row_int(phase_data, row_key) + value
    return value


def _increment_close_count(phase_data: dict) -> None:
    """Record one more close of this phase row (absent ⇒ 0).

    ``close_count > 1`` is the inference-free re-entry marker: it is written at
    the write site on every close, so it never has to be inferred from timestamp
    ordering the way ``cmd_generate``'s ``boundary_monotonicity`` detector does.
    """
    phase_data['close_count'] = _row_int(phase_data, 'close_count') + 1


def _guard_plan_exists(plan_id: str) -> dict | None:
    """Return a ``plan_not_found`` error dict when the plan dir is uninitialised.

    Plan-scoped writers in this module reach the plan directory through
    ``get_plan_dir`` and then ``mkdir(parents=True, ...)`` (directly or via
    ``atomic_write_file``). Without this guard a stray ``--plan-id`` for a plan
    that phase-1 never initialised silently creates an orphan plan tree just to
    hold a metrics artifact. Calling ``require_plan_exists`` first turns that
    silent side effect into a structured error.

    Returns ``None`` when the plan exists (caller proceeds); returns the error
    dict to be emitted verbatim when it does not. The error shape mirrors
    ``cmd_record_dispatch_boundary`` so every writer reports the same contract.
    """
    try:
        require_plan_exists(plan_id)
    except PlanNotFoundError as exc:
        return {
            'status': 'error',
            'error': 'plan_not_found',
            'message': str(exc),
            'plan_id': plan_id,
            'plan_dir': str(exc.plan_dir),
        }
    return None


def _coerce_numeric(value: object) -> int | float | str:
    """Try to coerce a value to int, then float, falling back to the original value."""
    if not isinstance(value, str):
        return value  # type: ignore[return-value]
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    return value


# get_plan_dir imported from file_ops


def write_metrics(plan_id: str, data: dict) -> None:
    metrics_path = get_plan_dir(plan_id) / METRICS_FILE
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f'plan_id: {plan_id}')
    if 'updated' in data:
        lines.append(f'updated: {data["updated"]}')
    # Preserve any other top-level keys round-tripped from read_metrics_raw.
    # read_metrics_raw accepts arbitrary top-level keys (lines before the first
    # [phase] block); write_metrics must emit them back so cmd_generate's
    # read -> mutate -> write loop stays lossless over the full key set.
    for extra_key, extra_val in data.items():
        if extra_key in ('plan_id', 'updated', 'phases'):
            continue
        lines.append(f'{extra_key}: {extra_val}')
    lines.append('')

    phases = data.get('phases', {})
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        lines.append(f'[{phase_name}]')
        for key, val in phase.items():
            lines.append(f'  {key}: {val}')
        lines.append('')

    atomic_write_file(metrics_path, '\n'.join(lines) + '\n')


def read_metrics_raw(plan_id: str) -> dict:
    """Read metrics from custom TOON-like format."""
    metrics_path = get_plan_dir(plan_id) / METRICS_FILE
    if not metrics_path.exists():
        return {'phases': {}}

    content = metrics_path.read_text(encoding='utf-8')
    if not content.strip():
        return {'phases': {}}

    data: dict[str, object] = {'phases': {}}
    current_phase: str | None = None
    phases: dict[str, dict[str, object]] = {}

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('[') and stripped.endswith(']'):
            current_phase = stripped[1:-1]
            phases[current_phase] = {}
        elif current_phase and ':' in stripped:
            key, _, raw_val = stripped.partition(':')
            parsed_val: object = raw_val.strip()
            # Try numeric conversion
            try:
                parsed_val = int(raw_val.strip())
            except (ValueError, TypeError):
                try:
                    parsed_val = float(raw_val.strip())
                except (ValueError, TypeError):
                    pass
            phases[current_phase][key.strip()] = parsed_val
        elif not current_phase and ':' in stripped:
            key, _, raw_val = stripped.partition(':')
            data[key.strip()] = raw_val.strip()

    data['phases'] = phases

    return data


def cmd_start_phase(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid phase: {phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    data = read_metrics_raw(plan_id)
    now = now_utc_iso()

    if phase not in data['phases']:
        data['phases'][phase] = {}

    data['phases'][phase]['start_time'] = now
    data['updated'] = now

    write_metrics(plan_id, data)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'start_time': now,
    }


def _clamp_worked_to_wall(phase_data: dict, duration_ms: int) -> int:
    """Bound the agent's worked window to the phase's recorded wall-clock span.

    No single agent can work longer than the phase's own wall-clock span, yet the
    1-init bootstrap ordering (`status.json.created` written *after* the init
    agent began working) can forward a `duration_ms` that exceeds the
    `created → end_time` wall-clock window, persisting a structurally-impossible
    ``agent_duration_seconds > duration_seconds`` row. When ``duration_seconds`` is
    present, clamp the worked value to it so the per-phase ``Worked <= Reported
    (wall)`` invariant always holds; otherwise return the value unchanged. The
    clamp only ever bounds — it never inflates a worked value below the wall span.

    Re-entry carries no carve-out here: this function bounds whatever value it is
    handed against whatever ``duration_seconds`` the row holds. On a re-entered
    phase the caller hands it the **summed** worked value and the row already
    holds the **accumulated** wall span, so the invariant survives accumulation
    without any special case. That ordering is the caller's obligation — clamping
    a per-close delta and adding the clamped result to an already-clamped value
    can sum past the accumulated wall span; see ``cmd_end_phase`` /
    ``cmd_phase_boundary``, which accumulate first and clamp the sum.
    """
    wall_seconds = phase_data.get('duration_seconds')
    if isinstance(wall_seconds, (int, float)):
        return min(duration_ms, int(round(float(wall_seconds) * 1000.0)))
    return duration_ms


def _accumulate_duration_seconds(phase_data: dict, prior_end_time: object, end_now: str) -> None:
    """Add this close's active wall span onto the row's ``duration_seconds``.

    ``duration_seconds`` carries no flag-vs-accumulator provenance — both writers
    compute it inline — so it is an unconditional add of a per-close **active
    span** rather than a provenance-keyed decision. The span runs from
    ``max(start_time, prior_end_time)`` to ``end_now``, which makes all three
    close shapes correct with one rule:

    - **First close** — ``prior_end_time`` is absent, so the anchor is
      ``start_time`` and the existing value is 0: byte-identical to a plain
      ``end_time - start_time`` assignment.
    - **Loop-back re-entry** — ``start_phase`` re-stamped a later ``start_time``,
      so it wins the ``max`` and only the new entry's span is added.
    - **Bare second close** (no intervening ``start-phase``) — the stale
      ``start_time`` loses to ``prior_end_time``, so only the genuinely-new span
      is added instead of double-counting the first entry.

    The accumulated value is the phase's total *active* wall time; it therefore
    deliberately does not satisfy ``duration_seconds == end_time - start_time`` on
    a re-entered row (``start_time`` stays re-entry-scoped). Unparseable
    timestamps leave the field untouched rather than writing a partial value.

    Args:
        phase_data: The phase row, mutated in place.
        prior_end_time: The row's ``end_time`` as captured BEFORE this close
            overwrote it, or a falsy value on a first close.
        end_now: This close's ``end_time`` ISO timestamp.
    """
    start_str = phase_data.get('start_time')
    if not start_str:
        return
    try:
        anchor_dt = datetime.fromisoformat(str(start_str))
        end_dt = datetime.fromisoformat(end_now)
        if prior_end_time:
            prior_dt = datetime.fromisoformat(str(prior_end_time))
            anchor_dt = max(anchor_dt, prior_dt)
        span_s = (end_dt - anchor_dt).total_seconds()
    except (ValueError, TypeError):
        return
    existing = phase_data.get('duration_seconds')
    base = float(existing) if isinstance(existing, (int, float)) else 0.0
    phase_data['duration_seconds'] = round(base + span_s, 1)


def _reconcile_accumulator_into_phase(phase_data: dict, accumulator: dict[str, int]) -> None:
    """Fold a phase's durable accumulator totals into its metrics row in place.

    The per-phase accumulator (``work/metrics-accumulator-{phase}.toon``) is the
    durable snapshot written after every subagent return. When a phase row was
    never closed by ``end-phase`` / ``phase-boundary`` — the terminal-phase gap
    where ``6-finalize`` accrued tokens but ``record-metrics`` never ran to fold
    them in — its accumulated totals would otherwise be dropped from the
    generated report. This helper backfills the row from the accumulator so the
    snapshot survives.

    Explicit-wins precedence: a field already present on the row (recorded by
    ``end-phase`` / ``phase-boundary``) is NEVER overwritten — only absent
    fields are backfilled, and only from a truthy accumulator value. Closed rows
    are therefore byte-identical to before. The accumulator's ``duration_ms`` is
    folded as ``agent_duration_ms`` (mirroring ``cmd_end_phase``): it is clamped
    to the phase wall-clock span and the derived ``agent_duration_seconds`` is
    written alongside it.
    """
    if not accumulator:
        return

    acc_tokens = accumulator.get('total_tokens')
    if acc_tokens and 'total_tokens' not in phase_data:
        phase_data['total_tokens'] = acc_tokens

    acc_tool_uses = accumulator.get('tool_uses')
    if acc_tool_uses and 'tool_uses' not in phase_data:
        phase_data['tool_uses'] = acc_tool_uses

    acc_duration_ms = accumulator.get('duration_ms')
    if acc_duration_ms and 'agent_duration_ms' not in phase_data:
        clamped = _clamp_worked_to_wall(phase_data, acc_duration_ms)
        phase_data['agent_duration_ms'] = clamped
        phase_data['agent_duration_seconds'] = round(clamped / 1000.0, 1)


def _close_phase_accumulating(
    phase_data: dict, plan_id: str, phase: str, args: argparse.Namespace, now: str
) -> dict[str, object]:
    """Close one phase row for one call, accumulating per-close totals onto it.

    Shared by ``cmd_end_phase`` and the phase-closing half of
    ``cmd_phase_boundary`` — both close a phase under the identical
    accumulate-on-re-entry contract. A phase can legitimately close more than
    once (a finalize loop-back re-enters an earlier phase under the same phase
    key), so this writer ACCUMULATES rather than replaces. Three distinct rules
    apply, because the fields do not share one arithmetic:

    - **Rule A (provenance-keyed)** for ``total_tokens``, ``tool_uses``,
      ``retrospective_tokens``, and the resolved worked ``duration_ms``: a
      ``'flag'``-sourced value is a per-close delta and is added to the row; an
      ``'accumulator'``-sourced value is already cumulative and is assigned. An
      unresolved field leaves the row untouched — never writes a ``0``.
    - **Rule B** for ``duration_seconds``: an unconditional add of this close's
      active span, anchored at ``max(start_time, prior_end_time)`` — see
      ``_accumulate_duration_seconds``.
    - **Rule C** for ``agent_duration_ms``: accumulate first, then clamp the SUM
      against the accumulated wall span, which keeps ``Worked <= Reported
      (wall)`` intact with no re-entry carve-out inside
      ``_clamp_worked_to_wall``.

    ``close_count`` is incremented on every close, making ``close_count > 1`` the
    inference-free re-entry marker ``cmd_generate`` renders. Mutates
    ``phase_data`` in place; the caller stamps its own result dict from the
    mutated row plus the returned pre-provenance values.

    Returns:
        A dict with ``total_tokens`` / ``retrospective_tokens`` (the
        pre-provenance resolved values, ``None``/falsy when unresolved — callers
        use these to decide whether to surface the row's accumulated value in
        their own result) and ``accumulator`` (the on-disk accumulator dict,
        used to decide ``accumulator_used``).
    """
    # Capture the row's prior end_time BEFORE the unconditional stamp below
    # overwrites it — it is the active-span anchor for a close that follows an
    # earlier close with no intervening start-phase (see
    # _accumulate_duration_seconds).
    prior_end_time = phase_data.get('end_time')
    # Stamp end_time unconditionally: it is the sole "recorded" marker
    # cmd_generate reads. An inline phase closes here with the usage flags
    # omitted (no agent <usage> envelope) and is still a fully recorded,
    # timestamps-only row — never listed under unrecorded_phases.
    phase_data['end_time'] = now

    # Rule B: add this close's active wall span onto duration_seconds. Must run
    # BEFORE the clamp below, which reads the accumulated span as its ceiling.
    _accumulate_duration_seconds(phase_data, prior_end_time, now)
    _increment_close_count(phase_data)

    # Read on-disk accumulator as fallback when explicit flags are absent.
    accumulator = _read_accumulator(plan_id, phase)
    duration_ms, duration_ms_source = _resolve_token_field(args.duration_ms, accumulator, 'duration_ms')
    total_tokens, total_tokens_source = _resolve_token_field(args.total_tokens, accumulator, 'total_tokens')
    tool_uses, tool_uses_source = _resolve_token_field(args.tool_uses, accumulator, 'tool_uses')

    # Rule C: accumulate the worked value first, then clamp the SUM against the
    # accumulated wall span — never clamp the delta and add it to an
    # already-clamped value, which can sum past that span.
    if duration_ms is not None:
        worked_total = _apply_provenance(phase_data, 'agent_duration_ms', duration_ms, duration_ms_source)
        worked_total = _clamp_worked_to_wall(phase_data, worked_total)
        phase_data['agent_duration_ms'] = worked_total
        phase_data['agent_duration_seconds'] = round(worked_total / 1000.0, 1)

    if total_tokens is not None:
        phase_data['total_tokens'] = _apply_provenance(
            phase_data, 'total_tokens', total_tokens, total_tokens_source
        )

    if tool_uses is not None:
        phase_data['tool_uses'] = _apply_provenance(phase_data, 'tool_uses', tool_uses, tool_uses_source)

    # Plan-retrospective spend attribution (default-absent): records the token
    # total attributable to the plan-retrospective dispatch within this phase
    # window. The retrospective dispatches under `--phase phase-6-finalize`, so
    # its spend is otherwise folded into the `[6-finalize]` total with no
    # separator. The audit's three metrics-related checks read this field to
    # exclude deliberate-analysis spend; plans archived before the producer
    # wiring landed simply lack it. The explicit `--retrospective-tokens` flag
    # is the override; absent it the value is read back from the accumulator
    # that the finalize retrospective step seeded via accumulate-agent-usage.
    retrospective_tokens, retrospective_tokens_source = _resolve_token_field(
        args.retrospective_tokens, accumulator, 'retrospective_tokens'
    )
    if retrospective_tokens:
        phase_data['retrospective_tokens'] = _apply_provenance(
            phase_data, 'retrospective_tokens', retrospective_tokens, retrospective_tokens_source
        )

    return {
        'total_tokens': total_tokens,
        'retrospective_tokens': retrospective_tokens,
        'accumulator': accumulator,
    }


def cmd_end_phase(args: argparse.Namespace) -> dict:
    """Close a phase, accumulating its per-close totals onto the existing row.

    See ``_close_phase_accumulating`` for the authoritative statement of the
    three accumulate-on-re-entry rules this delegates to.
    """
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {'status': 'error', 'error': 'invalid_phase', 'message': f'Invalid phase: {phase}'}

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    data = read_metrics_raw(plan_id)
    now = now_utc_iso()

    if phase not in data['phases']:
        data['phases'][phase] = {}

    phase_data = data['phases'][phase]
    closed = _close_phase_accumulating(phase_data, plan_id, phase, args, now)
    total_tokens = closed['total_tokens']
    retrospective_tokens = closed['retrospective_tokens']
    accumulator = closed['accumulator']

    data['updated'] = now
    write_metrics(plan_id, data)

    result = {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'end_time': now,
        'close_count': phase_data['close_count'],
    }
    if 'duration_seconds' in phase_data:
        result['duration_seconds'] = phase_data['duration_seconds']
    if total_tokens is not None:
        result['total_tokens'] = phase_data['total_tokens']
    if retrospective_tokens:
        result['retrospective_tokens'] = phase_data['retrospective_tokens']
    if accumulator and args.total_tokens is None:
        result['accumulator_used'] = True

    return result


def _wall_clock_ms(phase: dict) -> int | None:
    """Return the wall-clock duration of a phase in milliseconds, or None.

    Prefers the persisted ``duration_seconds`` field; when absent, derives the
    span from ``start_time``/``end_time`` ISO timestamps. Returns None when no
    wall-clock signal is available.

    The timestamp-derived branch is a **first-entry-only approximation**, NOT an
    equivalent definition of the persisted field. ``duration_seconds`` accumulates
    every close's active span while ``start_time`` stays re-entry-scoped, so on a
    ``close_count > 1`` row the two disagree by the gap spent in another phase.
    The approximation is nonetheless safe here because it fires only when
    ``duration_seconds`` is absent, and an accumulated row always carries it — so
    the two branches can never disagree about the same row.
    """
    duration_seconds = phase.get('duration_seconds')
    if isinstance(duration_seconds, (int, float)):
        return int(round(float(duration_seconds) * 1000.0))
    start_str = phase.get('start_time')
    end_str = phase.get('end_time')
    if start_str and end_str:
        try:
            start_dt = datetime.fromisoformat(str(start_str).strip().replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(str(end_str).strip().replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
        return int(round((end_dt - start_dt).total_seconds() * 1000.0))
    return None


def _worked_ms(phase: dict) -> int:
    """Return worked time in ms: max(agent_duration_ms, subagent_duration_ms).

    Missing operands are treated as 0. Worked time is the effort actually spent
    on this phase. When a main-context (orchestrating) turn dispatches a
    subagent, the subagent's wall span overlaps with the orchestrator's own
    wall span — the orchestrator is awaiting the subagent return, not doing
    independent compute. Summing the two values double-counts that overlap and
    can produce `Worked > Reported (wall)`, which breaks the per-phase
    Worked <= wall invariant.

    The non-double-counting definition: take the maximum of the two attribution
    sources. When only one is present, that value wins. When both are present,
    the longer span subsumes the shorter overlap. The result is bounded above
    by the per-phase wall clock for any phase whose subagent dispatches stay
    within the phase window, so the Idle = max(0, wall - worked) residual is
    non-negative and meaningful.
    """
    agent = phase.get('agent_duration_ms')
    subagent = phase.get('subagent_duration_ms')
    agent_ms = int(agent) if isinstance(agent, (int, float)) else 0
    subagent_ms = int(subagent) if isinstance(subagent, (int, float)) else 0
    return max(agent_ms, subagent_ms)


def _parse_iso(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp string to a datetime, tolerating a ``Z`` suffix.

    Returns ``None`` for a missing / non-string / unparseable value so callers can
    skip a phase whose boundary timestamp was never recorded.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def cmd_generate(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    data = read_metrics_raw(plan_id)
    phases = data.get('phases', {})

    if not phases:
        return {'status': 'error', 'error': 'no_data', 'message': 'No metrics data found'}

    # Reconcile each canonical phase against its durable on-disk accumulator
    # BEFORE deriving idle and rendering. A phase row that was never closed by
    # end-phase / phase-boundary (e.g. a 6-finalize interrupted, looped-back, or
    # never reaching record-metrics) still surfaces its accrued tokens because
    # the accumulator is the durable snapshot of record. Explicit-wins
    # precedence: rows already closed by end-phase / phase-boundary are left
    # byte-identical — only absent fields are backfilled.
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        _reconcile_accumulator_into_phase(phases[phase_name], _read_accumulator(plan_id, phase_name))

    # Persist each phase's dispatch-boundary sum AND the number of rows it summed.
    # Both are DISTINCT fields — the raw total_tokens is left byte-identical
    # (explicit-wins, never overwritten). The render below picks the largest
    # ELIGIBLE measure across all three competing measures of the dispatched
    # population; see the `_reconcile_dispatched_measures` block for the symmetric
    # rule and the two eligibility conditions. No-op when the boundary file is
    # absent (no rows, sum 0).
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        boundary_sum, boundary_rows = _read_dispatch_boundary_totals(plan_id, phase_name)
        if boundary_rows:
            # The row count persists whenever the file held rows, INCLUDING the
            # case where they sum to zero: the sum alone cannot state its own
            # coverage, and a measure that cannot state its coverage is the one
            # this field exists to make legible.
            phases[phase_name]['dispatch_boundary_rows_recorded'] = boundary_rows
        if boundary_sum:
            phases[phase_name]['dispatch_boundary_total'] = boundary_sum

    # Render-time boundary monotonicity detector. A finalize loop-back re-enters
    # an earlier phase (e.g. 5-execute) under its own phase key, so a LATER
    # phase's start_time can precede an EARLIER phase's already-closed end_time.
    # Walking the canonical PHASE_NAMES order, flag any phase whose start_time
    # precedes the maximum end_time seen so far in the sequence. This is a
    # READ-ONLY detector — it surfaces the anomaly (a top-level
    # `boundary_monotonicity` warning listing the phases plus a per-phase
    # `boundary_non_monotonic` annotation) and guards the idle residual below,
    # but NEVER mutates the recorded start_time / end_time boundary fields. It
    # does not touch the #812 `end_time`-keyed partial verdict.
    #
    # This detector is a timestamp-ordering signal only, and it names the LATER
    # phase rather than the re-entered one (the re-entered phase's fresh
    # start_time is what pushes the following phase's already-closed window out of
    # order). `close_count`, written at the write site, is the authoritative
    # re-entry marker — see the re_entered_phases detection below.
    non_monotonic_phases: list[str] = []
    prior_end_dt: datetime | None = None
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        start_dt = _parse_iso(phase.get('start_time'))
        end_dt = _parse_iso(phase.get('end_time'))
        if start_dt is not None and prior_end_dt is not None and start_dt < prior_end_dt:
            non_monotonic_phases.append(phase_name)
            phase['boundary_non_monotonic'] = 'true'
        if end_dt is not None and (prior_end_dt is None or end_dt > prior_end_dt):
            prior_end_dt = end_dt
    if non_monotonic_phases:
        data['boundary_monotonicity'] = ','.join(non_monotonic_phases)

    # Re-entry marker, read straight off the write site's close_count. Unlike the
    # timestamp detector above this needs no inference and names the phase that
    # was actually re-entered, so a reader can tell which row's totals are the
    # sum across multiple closes.
    re_entered_phases = [
        name for name in PHASE_NAMES if name in phases and _row_int(phases[name], 'close_count') > 1
    ]
    if re_entered_phases:
        data['re_entered_phases'] = ','.join(re_entered_phases)

    # Persist the per-phase idle residual back into metrics.toon before
    # rendering: idle = max(0, wall_clock - worked). Derived deterministically
    # from already-persisted fields via session-boundary inference — no new API.
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        wall_ms = _wall_clock_ms(phase)
        if wall_ms is None:
            continue
        if phase_name in non_monotonic_phases:
            # Guard: a re-entered (non-monotonic) phase's wall span overlaps an
            # earlier phase's already-closed window, so the idle residual derived
            # from it is corrupt. Zero it rather than emit a meaningless figure;
            # the boundary_monotonicity warning surfaces the anomaly instead.
            phase['idle_duration_ms'] = 0
            continue
        idle_ms = max(0, wall_ms - _worked_ms(phase))
        phase['idle_duration_ms'] = idle_ms

    # First-class partiality verdict over the canonical six-phase baseline.
    # A canonical phase is "recorded" iff its metrics.toon row carries an
    # end_time (the boundary-close marker, consistent with cmd_boundary_status's
    # missing-boundary definition); a phase with no row at all is unrecorded
    # too. `partial` is true whenever any canonical phase lacks that marker —
    # the floor-not-truth signal a consumer reads to tell an under-count (e.g. a
    # 6-finalize whose terminal close never folded the accumulator in) from a
    # genuinely complete report. Persist both as top-level keys in metrics.toon
    # (round-tripped via read_metrics_raw's arbitrary-top-level-key path):
    # `partial` as a true/false token and `unrecorded_phases` comma-joined.
    unrecorded_phases = [name for name in PHASE_NAMES if not phases.get(name, {}).get('end_time')]
    partial = len(unrecorded_phases) > 0
    data['partial'] = 'true' if partial else 'false'
    data['unrecorded_phases'] = ','.join(unrecorded_phases)

    write_metrics(plan_id, data)

    # Build metrics.md content
    lines = []
    lines.append(f'# Metrics: {plan_id}')
    lines.append('')
    lines.append(f'Generated: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}')
    lines.append('')

    # Phase breakdown table
    lines.append('## Phase Breakdown')
    lines.append('')

    # First-class partiality marker: when a canonical phase lacks a recorded
    # boundary, surface the gap directly under the heading so a reader sees the
    # report is a floor, not a complete accounting.
    if partial:
        lines.append(f'> Partial: unrecorded phases — {", ".join(unrecorded_phases)}')
        lines.append('')

    # Re-entry marker: name every phase closed more than once, so a reader knows
    # which rows carry totals summed across multiple closes. This is the
    # authoritative re-entry signal (close_count is written at the write site);
    # the timestamp-derived warning below is a weaker inference that names the
    # later phase instead.
    if re_entered_phases:
        lines.append(
            f'> Re-entered phases: {", ".join(re_entered_phases)}. Totals for these '
            'phases are the sum across every close (close_count > 1).'
        )
        lines.append('')

    # Boundary-monotonicity warning: when a finalize loop-back re-entered an
    # earlier phase, a later phase's start_time precedes an earlier phase's
    # end_time. Surface it under the heading so a reader sees the idle residual
    # for those phases was guarded (zeroed) rather than derived from a corrupt
    # overlapping span.
    if non_monotonic_phases:
        lines.append(
            '> Boundary monotonicity warning: re-entered (non-monotonic) phase '
            f'boundaries detected — {", ".join(non_monotonic_phases)}. Idle residual '
            'guarded for these phases (a finalize loop-back re-enters an earlier phase).'
        )
        lines.append('')

    # Collect breakdown rows (phases that exist) preserving canonical phase order.
    # The completeness denominator is the canonical-six baseline (len(PHASE_NAMES)),
    # NOT the count of present rows: an entirely-absent phase must still make the
    # Total render as partial (n=k/6) rather than silently looking complete.
    breakdown_rows = [(name, phases[name]) for name in PHASE_NAMES if name in phases]
    breakdown_n = len(PHASE_NAMES)

    def _numeric(value: object) -> int | float | None:
        """Return value as int/float if it's a truthy number, else None.

        Symmetric per-cell rule: a per-phase cell is "present" iff the underlying
        raw value is a truthy numeric (zero or missing → absent → '-').
        """
        coerced = _coerce_numeric(value)
        if not isinstance(coerced, (int, float)):
            return None
        if not coerced:
            return None
        return coerced

    def _ms_cell(value_ms: int | None) -> tuple[str, float | None]:
        """Render a duration-in-ms value as a table cell.

        Returns (rendered_cell, value_for_total_in_seconds). A truthy numeric
        renders via format_duration; zero or None renders '-' and contributes
        nothing to the Total. This is the symmetric per-cell present/absent rule
        applied uniformly to the Worked, Reported (wall), and Idle columns.
        """
        if value_ms is None:
            return '-', None
        numeric = _numeric(value_ms)
        if numeric is None:
            return '-', None
        seconds = float(numeric) / 1000.0
        return format_duration(seconds), seconds

    # Per-column value subsets (for Total aggregation and partial-marker decisions).
    worked_values: list[float] = []
    wall_values: list[float] = []
    idle_values: list[float] = []
    tokens_values: list[int] = []
    tool_uses_values: list[int] = []
    # Phases whose Tokens cell renders a competing dispatched measure rather than
    # the recorded total_tokens. Each entry is (phase, winning_field, winning
    # value, the total_tokens it beat) so the annotation can name WHICH measure
    # won and by how much, instead of asserting an unqualified "same-population
    # max" the comparison may not have earned.
    reconciled_phases: list[tuple[str, str, int, int | None]] = []
    # Phases whose token record is NOT a plain dispatched measurement, collected
    # so the population annotation under the table can name them. `inline` rows
    # render a main-context-window figure in the dispatched column (the enrich
    # fold); `mixed` rows render a dispatched figure that omits inline spend the
    # row records separately.
    inline_population_phases: list[str] = []
    mixed_population_phases: list[str] = []

    # Two-pass build: first collect all rows as tuples, then pad to uniform per-column width.
    header_row: tuple[str, str, str, str, str, str] = (
        'Phase',
        'Worked',
        'Reported (wall)',
        'Idle',
        'Tokens',
        'Tool Uses',
    )
    data_rows: list[tuple[str, str, str, str, str, str]] = []

    for phase_name, phase in breakdown_rows:
        wall_ms = _wall_clock_ms(phase)
        worked_ms = _worked_ms(phase)
        idle_ms = phase.get('idle_duration_ms')
        idle_ms_int = int(idle_ms) if isinstance(idle_ms, (int, float)) else None

        worked_str, worked_val = _ms_cell(worked_ms)
        if worked_val is not None:
            worked_values.append(worked_val)

        wall_str, wall_val = _ms_cell(wall_ms)
        if wall_val is not None:
            wall_values.append(wall_val)

        idle_str, idle_val = _ms_cell(idle_ms_int)
        if idle_val is not None:
            idle_values.append(idle_val)

        # Symmetric same-population reconciliation across ALL THREE competing
        # measures of the dispatched population (never their sum — they count the
        # same leaves). The largest ELIGIBLE measure wins and feeds the Total via
        # tokens_values; a partial boundary measure and a cross-population
        # total_tokens are both ineligible. When the winner is not total_tokens,
        # the phase is recorded so the annotation below names which measure won.
        raw_tokens = _numeric(phase.get('total_tokens'))
        winner = _reconcile_dispatched_measures(phase)
        if winner is not None:
            winning_field, winning_value = winner
            if winning_field != 'total_tokens':
                reconciled_phases.append(
                    (phase_name, winning_field, winning_value,
                     int(raw_tokens) if raw_tokens is not None else None)
                )
            tokens_str = f'{winning_value:,}'
            tokens_values.append(winning_value)
        elif raw_tokens is not None:
            # No eligible dispatched measure. The row still carries a figure —
            # the inline phase's main-context total — which renders on its own
            # and is marked `(inline)` by the population suffix below.
            tokens_str = f'{int(raw_tokens):,}'
            tokens_values.append(int(raw_tokens))
        else:
            tokens_str = '-'

        # Declare the population at the point of render. The cell carries the
        # marker; the annotation under the table declares the unmarked default
        # and spells out what each marker means, so a reader never has to infer
        # the population from a column header that names a total, not a measured
        # population.
        population = _token_population(phase)
        if population == POPULATION_INLINE:
            inline_population_phases.append(phase_name)
        elif population == POPULATION_MIXED:
            mixed_population_phases.append(phase_name)
        if tokens_str != '-':
            tokens_str += _POPULATION_CELL_SUFFIX.get(population, '')

        tool_uses = _numeric(phase.get('tool_uses'))
        tool_uses_str = str(int(tool_uses)) if tool_uses is not None else '-'
        if tool_uses is not None:
            tool_uses_values.append(int(tool_uses))

        data_rows.append((phase_name, worked_str, wall_str, idle_str, tokens_str, tool_uses_str))

    def _total_str(values: list, formatter, *, is_duration: bool = False) -> str:
        """Apply the symmetric Total aggregation rule.

        - Empty subset → '-'.
        - Subset smaller than breakdown_n → '{sum_str} (n=k/N)'.
        - Subset equal to breakdown_n → plain sum.
        """
        k = len(values)
        if k == 0:
            return '-'
        if is_duration:
            total = sum(values)
            sum_str = format_duration(float(total))
        else:
            total = sum(int(v) for v in values)
            sum_str = formatter(total)
        if k < breakdown_n:
            return f'{sum_str} (n={k}/{breakdown_n})'
        return sum_str

    total_worked_str = _total_str(worked_values, lambda n: format_duration(float(n)), is_duration=True)
    total_wall_str = _total_str(wall_values, lambda n: format_duration(float(n)), is_duration=True)
    total_idle_str = _total_str(idle_values, lambda n: format_duration(float(n)), is_duration=True)
    total_tokens_str = _total_str(tokens_values, lambda n: f'{n:,}')
    total_tool_uses_str = _total_str(tool_uses_values, str)

    total_row: tuple[str, str, str, str, str, str] = (
        '**Total**',
        f'**{total_worked_str}**',
        f'**{total_wall_str}**',
        f'**{total_idle_str}**',
        f'**{total_tokens_str}**',
        f'**{total_tool_uses_str}**',
    )

    # Compute per-column widths across header, data rows, and the bold-marked Total row.
    all_rows: list[tuple[str, str, str, str, str, str]] = [header_row, *data_rows, total_row]
    column_count = len(header_row)
    widths = [max(len(row[c]) for row in all_rows) for c in range(column_count)]

    def _format_row(row: tuple[str, str, str, str, str, str]) -> str:
        return '| ' + ' | '.join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + ' |'

    separator_line = '|' + '|'.join('-' * (widths[i] + 2) for i in range(column_count)) + '|'

    lines.append(_format_row(header_row))
    lines.append(separator_line)
    for row in data_rows:
        lines.append(_format_row(row))
    lines.append(_format_row(total_row))
    lines.append('')

    # Reconciliation annotation: name the phases whose Tokens cell renders the
    # dispatch-boundary sum instead of the recorded total, stating the deliberate
    # under-count correction (same-population max) inline under the table.
    if reconciled_phases:
        details = ', '.join(
            f'{name} → {field} {value:,}'
            + (f' (> total_tokens {beaten:,})' if beaten is not None else ' (no recorded total_tokens)')
            for name, field, value, beaten in reconciled_phases
        )
        lines.append(
            '> Tokens reconciled across the competing measures of the dispatched '
            'population (largest eligible measure wins, never their sum, since all '
            'three count the same leaves; a partial measure is ineligible): '
            f'{details}'
        )
        lines.append('')

    # Population annotation: the Tokens column is NOT single-population, and the
    # Total row therefore is not a dispatched total. Say so where the figures are
    # rendered rather than leaving the reader to infer it from a field name.
    if inline_population_phases:
        lines.append(
            '> Tokens population: an unmarked cell is a dispatched-subagent measurement. '
            'Marked `(inline)` — the phase dispatched nothing, so the cell is the '
            'main-context-window measurement enrich folded into total_tokens (also recorded '
            f'under its own name as inline_main_context_tokens): {", ".join(inline_population_phases)}. '
            'The **Total** therefore sums more than one population and is not a dispatched total.'
        )
        lines.append('')
    if mixed_population_phases:
        lines.append(
            '> Marked `(mixed)` — the cell is the phase\'s dispatched-subagent total; the inline '
            'main-context spend measured in the same window is recorded separately as '
            'inline_main_context_tokens and is excluded from both the cell and the **Total**: '
            f'{", ".join(mixed_population_phases)}.'
        )
        lines.append('')

    # Phase details
    lines.append('## Phase Details')
    lines.append('')

    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        lines.append(f'### {phase_name}')
        lines.append('')

        start = phase.get('start_time', '-')
        end = phase.get('end_time', '-')
        lines.append(f'- **Start**: {start}')
        lines.append(f'- **End**: {end}')

        # Only a re-entered phase gets this bullet: a once-closed row carries no
        # reader-relevant close-count fact, and stating "1" on every phase would
        # bury the rows that actually accumulated.
        close_count = _row_int(phase, 'close_count')
        if close_count > 1:
            lines.append(
                f'- **Closes**: {close_count} (phase re-entered; the totals below are '
                'the sum across every close, and Start is the latest entry only)'
            )

        wall_ms = _wall_clock_ms(phase)
        if wall_ms:
            lines.append(f'- **Reported (wall-clock) duration**: {format_duration(wall_ms / 1000.0)}')

        worked_ms = _worked_ms(phase)
        if worked_ms:
            lines.append(f'- **Worked duration**: {format_duration(worked_ms / 1000.0)}')

        idle_ms = phase.get('idle_duration_ms')
        if isinstance(idle_ms, (int, float)) and idle_ms:
            lines.append(f'- **Idle duration**: {format_duration(float(idle_ms) / 1000.0)}')

        population = _token_population(phase)

        tokens = phase.get('total_tokens')
        if tokens:
            lines.append(
                f'- **Total tokens**: {int(tokens):,} ({_POPULATION_BULLET_NOTE[population]})'
            )

        boundary_total = phase.get('dispatch_boundary_total')
        if boundary_total:
            # The measure states its own coverage on every render. A boundary sum
            # that covers fewer dispatches than the phase had is a floor, and
            # saying so is the whole point of carrying rows_recorded — the prior
            # text asserted "same-population max" unconditionally, which a partial
            # measure has not earned.
            rows_recorded = phase.get('dispatch_boundary_rows_recorded')
            samples = phase.get('subagent_samples')
            boundary_partial = _boundary_measure_is_partial(phase)
            if boundary_partial is None:
                coverage = (
                    f'{rows_recorded} row(s) recorded, coverage undecidable — the phase '
                    'carries no subagent_samples to compare against'
                    if isinstance(rows_recorded, int)
                    else 'coverage undecidable'
                )
            elif boundary_partial:
                coverage = (
                    f'PARTIAL: {rows_recorded} of {samples} dispatch(es) recorded, so this '
                    'measure is a floor and is ineligible for the reconciliation maximum'
                )
            else:
                coverage = f'{rows_recorded} of {samples} dispatch(es) recorded — complete'
            won = any(
                name == phase_name and field == 'dispatch_boundary_total'
                for name, field, _v, _b in reconciled_phases
            )
            outcome = 'won the reconciliation maximum' if won else 'did not win the maximum'
            lines.append(
                f'- **Dispatch-boundary total**: {int(boundary_total):,} '
                f'(dispatched-subagent population; {coverage}; {outcome})'
            )

        inline_main_context = phase.get('inline_main_context_tokens')
        if inline_main_context:
            # The relationship to Total tokens differs by population, so the
            # bullet states which one applies. Claiming "surfaced alongside the
            # dispatched total, never replacing it" on an inline-only phase
            # would be false: there, this IS the figure Total tokens carries.
            if population == POPULATION_INLINE:
                relation = (
                    'this phase dispatched nothing, so this is the same figure Total tokens '
                    'carries, restated here under its own population-honest name'
                )
            else:
                relation = (
                    'surfaced alongside the dispatched Total tokens, which does not include it'
                )
            lines.append(
                f'- **Inline main-context tokens**: {int(inline_main_context):,} '
                '(main-context-window population, attributed via enrich phase-window usage — '
                f'input + output + cache_creation, excludes cache_read; {relation})'
            )

        tool_uses = phase.get('tool_uses')
        if tool_uses:
            lines.append(f'- **Tool uses**: {int(tool_uses)}')

        # Four-field usage view (sourced by `enrich` from subagent-transcript +
        # parent-window `message.usage` walks). Rendered per phase when present.
        _four_field_labels = (
            ('input_tokens', 'Input tokens'),
            ('output_tokens', 'Output tokens'),
            ('cache_read_input_tokens', 'Cache read input tokens'),
            ('cache_creation_input_tokens', 'Cache creation input tokens'),
        )
        for field, label in _four_field_labels:
            value = phase.get(field)
            if isinstance(value, (int, float)) and value:
                lines.append(f'- **{label}**: {int(value):,}')

        billing = phase.get('billing_weighted_total')
        if isinstance(billing, (int, float)) and billing:
            lines.append(
                f'- **Billing-weighted total**: {int(billing):,} '
                '(billing-cost figure, not a work-comparable measure — '
                'cache_read sums context re-reads across turns)'
            )

        # Exploration-share counters. RENDER-GUARD DIVERGENCE, deliberate: these
        # are guarded on PRESENCE (`field in phase`), not on the truthiness test
        # the four-field bullets above use. A stored 0 is a MEASURED zero here and
        # must render as `0`, while an absent counter (a runtime that declined the
        # transcript primitive) must render nothing — the truthiness guard would
        # collapse those two into the same blank output, destroying exactly the
        # distinction the persistence rule, the platform-runtime contract, and the
        # `exploration-share` corpus-exclusion rule are all built on. Do NOT
        # "harmonize" this back to the neighbouring truthiness form. The four-field
        # bullets keep theirs because for those fields zero and absent carry no
        # meaningful difference.
        for field in _EXPLORATION_COUNTER_FIELDS:
            if field in phase:
                label = field.replace('_', ' ').capitalize()
                lines.append(f'- **{label}**: {int(phase[field]):,}')

        lines.append('')

    md_content = '\n'.join(lines)
    md_path = get_plan_dir(plan_id) / METRICS_MD
    atomic_write_file(md_path, md_content)

    total_worked = sum(worked_values)
    total_wall = sum(wall_values)
    total_idle = sum(idle_values)
    total_tokens = sum(tokens_values)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': METRICS_MD,
        'phases_recorded': len(phases),
        'partial': partial,
        'unrecorded_phases': unrecorded_phases,
        'boundary_monotonicity': non_monotonic_phases,
        're_entered_phases': re_entered_phases,
        'total_worked_seconds': round(total_worked, 1),
        'total_wall_seconds': round(total_wall, 1),
        'total_idle_seconds': round(total_idle, 1),
        'total_tokens': total_tokens,
        'total_worked_formatted': format_duration(total_worked),
        'total_wall_formatted': format_duration(total_wall),
        'total_idle_formatted': format_duration(total_idle),
        'total_tokens_formatted': format_tokens_short(total_tokens),
    }


_PHASE_BREAKDOWN_HEADING_RE = re.compile(r'^## Phase Breakdown\s*$')
_NEXT_H2_RE = re.compile(r'^## ')


def _extract_phase_breakdown_section(content: str) -> str | None:
    """Return the '## Phase Breakdown' section verbatim from metrics.md content.

    The section spans from the heading line up to (but not including) the next
    ``## `` heading or end-of-file. A single trailing blank line is normalised
    so the output ends with exactly one newline.

    Args:
        content: Full metrics.md file contents.

    Returns:
        The section as a string ending in a single newline, or ``None`` when
        the heading is absent.
    """
    lines = content.splitlines(keepends=True)
    start_idx: int | None = None
    for i, line in enumerate(lines):
        if _PHASE_BREAKDOWN_HEADING_RE.match(line):
            start_idx = i
            break
    if start_idx is None:
        return None
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if _NEXT_H2_RE.match(lines[j]):
            end_idx = j
            break
    section = ''.join(lines[start_idx:end_idx]).rstrip() + '\n'
    return section


def cmd_print_phase_breakdown(args: argparse.Namespace) -> dict:
    """Extract the '## Phase Breakdown' section from metrics.md and persist it.

    Default (``--output-file`` absent): write the extracted section to a known
    plan-relative artifact path (default ``work/phase-breakdown-output.txt``)
    and return a TOON envelope ``{status, plan_id, file, bytes_written}``.

    Explicit relative path: write the section to the supplied plan-relative
    path (parent directories are created as needed) and return the same TOON
    envelope. Absolute paths are rejected.

    Legacy stdout mode (``--output-file -``): write the section verbatim to
    stdout (no trailing TOON) and return a result dict carrying the
    ``_print_only`` sentinel so ``main`` skips the standard TOON emission.

    On error (missing metrics.md, missing section, invalid output path), a
    normal error TOON is returned via the standard emit path.
    """
    plan_id = require_valid_plan_id(args)
    md_path = get_plan_dir(plan_id) / METRICS_MD
    if not md_path.exists():
        return {
            'status': 'error',
            'error': 'metrics_md_not_found',
            'plan_id': plan_id,
            'message': f'metrics.md not found at {md_path}',
        }
    content = md_path.read_text(encoding='utf-8')
    section = _extract_phase_breakdown_section(content)
    if section is None:
        return {
            'status': 'error',
            'error': 'phase_breakdown_section_not_found',
            'plan_id': plan_id,
            'message': '## Phase Breakdown heading not found in metrics.md',
        }

    output_file = getattr(args, 'output_file', None)
    section_bytes = section.encode('utf-8')

    if output_file == '-':
        # Legacy stdout-only mode.
        sys.stdout.write(section)
        sys.stdout.flush()
        return {
            '_print_only': True,
            'status': 'success',
            'plan_id': plan_id,
            'bytes_written': len(section_bytes),
        }

    # Direct file-write mode (default + explicit relative path).
    relative_path = output_file if output_file else PHASE_BREAKDOWN_DEFAULT_OUTPUT
    if not is_valid_relative_path(relative_path):
        return {
            'status': 'error',
            'error': 'output_file_must_be_relative',
            'plan_id': plan_id,
            'message': (
                f'--output-file must be a plan-relative path '
                f'(no absolute paths, no traversal): {relative_path}'
            ),
        }
    file_path = get_plan_dir(plan_id) / relative_path
    # Defense-in-depth: verify resolved path stays within plan dir (guards symlinks, OS quirks).
    plan_dir_resolved = get_plan_dir(plan_id).resolve()
    if not file_path.resolve().is_relative_to(plan_dir_resolved):
        return {
            'status': 'error',
            'error': 'output_file_must_be_relative',
            'plan_id': plan_id,
            'message': (
                f'--output-file must be a plan-relative path '
                f'(no absolute paths, no traversal): {relative_path}'
            ),
        }
    atomic_write_file(file_path, section)
    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': relative_path,
        'bytes_written': len(section_bytes),
    }


def _read_status_created(plan_id: str) -> str | None:
    """Return status.json.created (ISO timestamp) for the plan, or None on any failure.

    Used by cmd_phase_boundary to backfill 1-init.start_time at the first phase
    transition. Failure modes (missing status.json, malformed JSON, missing
    'created' key, non-string value) all return None — the renderer's
    agent-duration fallback still produces a meaningful Duration cell.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return None
    try:
        raw = status_path.read_text(encoding='utf-8')
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    created = data.get('created') if isinstance(data, dict) else None
    return created if isinstance(created, str) else None


def cmd_phase_boundary(args: argparse.Namespace) -> dict:
    """Atomically end the previous phase, start the next phase, and regenerate
    metrics.md in a single call.

    Equivalent to running, in order:
        end-phase   --phase {prev_phase} [--total-tokens N --duration-ms M --tool-uses K]
        start-phase --phase {next_phase}
        generate

    The fused call writes the same persisted state as the three-call sequence
    (work/metrics.toon and metrics.md). It is intended for orchestration
    boundaries where the caller knows the exact prev→next transition and
    wants a single script invocation instead of three.

    The optional token/duration/tool-uses flags are forwarded to the
    `end-phase` step. If the previous phase has not yet been started (no
    matching `start-phase`), it is recorded with end metadata only — same
    behaviour as the standalone `end-phase` command.

    Accumulate-on-re-entry: closing `--prev-phase` ADDS to that row rather than
    replacing it, so a finalize loop-back that re-enters an earlier phase keeps
    both entries' totals. The closing half delegates to
    `_close_phase_accumulating` — the shared writer `cmd_end_phase` also calls —
    see its docstring for the authoritative statement of the three
    accumulate-on-re-entry rules.

    Inline-phase recording mode: a phase that runs *inline* in the main
    orchestrator context (rather than as a dispatched `execution-context`
    leaf) produces no agent `<usage>` envelope, so the caller OMITS the
    `--total-tokens` / `--duration-ms` / `--tool-uses` flags. Omitting them is
    the sanctioned inline recording mode — NOT an incomplete call. The
    previous phase's `end_time` is stamped unconditionally below (independent
    of any usage flag), and `cmd_generate`'s partiality verdict keys a phase's
    "recorded" status solely off that `end_time` marker. A timestamps-only
    closed row is therefore treated as fully recorded: it is never listed under
    `unrecorded_phases` and never flips `partial` to true. This is the path the
    inline 1-init → 2-refine boundary and the recipe-inline (refine/outline)
    boundaries take; it preserves the #812 floor-not-truth semantics unchanged.
    """
    plan_id = require_valid_plan_id(args)
    prev_phase = args.prev_phase
    next_phase = args.next_phase

    if prev_phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid prev_phase: {prev_phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }
    if next_phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid next_phase: {next_phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    # Step 1: end the previous phase (mirrors cmd_end_phase semantics).
    data = read_metrics_raw(plan_id)
    end_now = now_utc_iso()

    if prev_phase not in data['phases']:
        data['phases'][prev_phase] = {}
    prev_data = data['phases'][prev_phase]

    # 1-init structural backfill: when transitioning out of 1-init for the
    # first time the phase row never went through cmd_start_phase, so
    # start_time is absent. Source it from status.json.created BEFORE closing
    # the row so the duration-computation path inside the shared closer catches
    # the backfill and writes duration_seconds in the same call.
    if prev_phase == '1-init' and not prev_data.get('start_time'):
        created_ts = _read_status_created(plan_id)
        if created_ts is not None:
            prev_data['start_time'] = created_ts

    closed = _close_phase_accumulating(prev_data, plan_id, prev_phase, args, end_now)
    total_tokens = closed['total_tokens']
    accumulator = closed['accumulator']

    # Step 2: start the next phase (mirrors cmd_start_phase semantics).
    start_now = now_utc_iso()
    if next_phase not in data['phases']:
        data['phases'][next_phase] = {}
    data['phases'][next_phase]['start_time'] = start_now
    data['updated'] = start_now

    write_metrics(plan_id, data)

    # Step 3: regenerate metrics.md from the current state.
    generate_result = cmd_generate(args)

    result = {
        'status': 'success',
        'plan_id': plan_id,
        'prev_phase': prev_phase,
        'next_phase': next_phase,
        'end_time': end_now,
        'start_time': start_now,
        'prev_close_count': prev_data['close_count'],
    }
    if 'duration_seconds' in prev_data:
        result['prev_duration_seconds'] = prev_data['duration_seconds']
    if total_tokens is not None:
        result['prev_total_tokens'] = prev_data['total_tokens']
    if accumulator and args.total_tokens is None:
        result['accumulator_used'] = True
    # Surface the generate side-effect outcome so callers can react if it
    # fell through to the no_data path (would only happen on a brand-new
    # plan where neither phase ever had a start_time recorded — should not
    # occur in normal phase boundary use).
    if generate_result.get('status') == 'success':
        result['metrics_file'] = generate_result.get('file', METRICS_MD)
        result['phases_recorded'] = generate_result.get('phases_recorded', 0)
    else:
        result['generate_status'] = generate_result.get('status', 'unknown')
        result['generate_message'] = generate_result.get('message', '')

    return result


def cmd_boundary_status(args: argparse.Namespace) -> dict:
    """Classify a metrics phase boundary as stamped / missing / not_applicable.

    Read-only resume-time detector. On cross-session re-entry the orchestrator
    calls this BEFORE dispatching the current phase to decide whether a missing
    `phase-boundary` must be stamped: if the prior session's phase skill
    self-transitioned the status, the resuming orchestrator's `manage-status
    transition` is a no-op and the paired `phase-boundary` call is skipped along
    with it, silently dropping a whole phase's token/duration attribution. This
    verb is the deterministic detection half of that reconciliation; it performs
    ZERO mutation of `work/metrics.toon`.

    Inputs:
        --next-phase  (required): the phase being entered on resume.
        --prev-phase  (optional): the phase that should have been closed before
            entering `--next-phase`. When omitted, only the "current phase has no
            start" condition is evaluated against `--next-phase`.

    Classification (computed from the persisted metrics.toon rows — the same
    `start_time` / `end_time` fields `end-phase` writes):
        - ``not_applicable``: a `--prev-phase` was supplied but that phase has no
            row at all (it never started) — there is no boundary to reconcile.
            When `--prev-phase` is omitted this classification never applies.
        - ``missing``: the boundary is half-stamped — the prev phase has a
            `start_time` but no `end_time`, OR the next phase has no `start_time`.
        - ``stamped``: the boundary is complete — when `--prev-phase` is supplied
            it has both `start_time` and `end_time` AND the next phase has a
            `start_time`; when `--prev-phase` is omitted the next phase has a
            `start_time`.

    Returns a TOON verdict carrying the classification, the offending field(s),
    and the prev/next phase names. The orchestrator prose reacts to `missing` by
    issuing an explicit `phase-boundary --prev-phase {prev} --next-phase {next}`
    call even though the status transition already happened.
    """
    plan_id = require_valid_plan_id(args)
    prev_phase = args.prev_phase
    next_phase = args.next_phase

    if next_phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid next_phase: {next_phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }
    if prev_phase is not None and prev_phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid prev_phase: {prev_phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    try:
        data = read_metrics_raw(plan_id)
    except OSError as exc:
        return {
            'status': 'error',
            'error': 'read_failed',
            'message': f'Failed to read metrics file: {exc}',
        }
    phases = data.get('phases', {})

    prev_data = phases.get(prev_phase) if prev_phase is not None else None
    next_data = phases.get(next_phase, {})

    next_has_start = bool(next_data.get('start_time'))

    # not_applicable: a prev phase was requested but it never started — nothing
    # to reconcile on the prev side.
    if prev_phase is not None and not prev_data:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'prev_phase': prev_phase,
            'next_phase': next_phase,
            'classification': 'not_applicable',
            'reason': 'prev phase has no metrics row (never started)',
        }

    # Collect the offending half-stamped fields.
    missing_fields: list[str] = []
    if prev_data is not None:
        if prev_data.get('start_time') and not prev_data.get('end_time'):
            missing_fields.append(f'{prev_phase}.end_time')
    if not next_has_start:
        missing_fields.append(f'{next_phase}.start_time')

    if missing_fields:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'prev_phase': prev_phase if prev_phase is not None else '-',
            'next_phase': next_phase,
            'classification': 'missing',
            'missing_fields': ','.join(missing_fields),
            'reason': 'half-stamped boundary — stamp the missing phase-boundary on resume',
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'prev_phase': prev_phase if prev_phase is not None else '-',
        'next_phase': next_phase,
        'classification': 'stamped',
        'reason': 'boundary fully recorded — proceed unchanged',
    }


def cmd_accumulate_agent_usage(args: argparse.Namespace) -> dict:
    """Persist running per-phase totals of subagent <usage> data.

    Reads `.plan/local/plans/{plan_id}/work/metrics-accumulator-{phase}.toon`
    (initialising it when absent), sums in any provided values, increments
    the `samples` counter, and writes the file back. Idempotent across
    successive calls — the only authoritative state is on disk.

    Designed to be invoked from `phase-5-execute` and `phase-6-finalize`
    SKILL.md immediately after every Task-agent return, in place of the
    fragile model-context-only `agent_usage_totals` discipline.
    """
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid phase: {phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    existing = _read_accumulator(plan_id, phase)
    totals = {
        'total_tokens': int(existing.get('total_tokens', 0)),
        'tool_uses': int(existing.get('tool_uses', 0)),
        'duration_ms': int(existing.get('duration_ms', 0)),
        'retrospective_tokens': int(existing.get('retrospective_tokens', 0)),
        'samples': int(existing.get('samples', 0)),
    }
    if args.total_tokens is not None:
        totals['total_tokens'] += args.total_tokens
    if args.tool_uses is not None:
        totals['tool_uses'] += args.tool_uses
    if args.duration_ms is not None:
        totals['duration_ms'] += args.duration_ms
    if args.retrospective_tokens is not None:
        totals['retrospective_tokens'] += args.retrospective_tokens
    totals['samples'] += 1

    _write_accumulator(plan_id, phase, totals)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'total_tokens': totals['total_tokens'],
        'tool_uses': totals['tool_uses'],
        'duration_ms': totals['duration_ms'],
        'retrospective_tokens': totals['retrospective_tokens'],
        'samples': totals['samples'],
        'accumulator_file': str(_accumulator_path(plan_id, phase).relative_to(get_plan_dir(plan_id))),
    }


def _dispatch_boundary_path(plan_id: str, phase: str) -> Path:
    return get_plan_dir(plan_id) / DISPATCH_BOUNDARY_FILE_TEMPLATE.format(phase=phase)


def cmd_record_dispatch_boundary(args: argparse.Namespace) -> dict:
    """Record one tabular row per phase Task dispatch termination.

    Appends a TOON row to ``work/metrics-dispatch-boundaries-{phase}.toon``
    capturing why a phase Task dispatch ended (voluntary checkpoint,
    bare task_complete return, harness cancellation, error, unknown) along
    with the dispatched agent's <usage> totals at the time of return. The
    accumulating file becomes the audit trail for diagnosing
    `[OUTCOME]`-coverage gaps caused by agent-initiated re-dispatch.

    The file uses the same column layout for every row so plan-retrospective
    fact extractors can ingest it without a schema lookup. Each row carries the
    legacy five columns (``<timestamp>,<termination_cause>,<total_tokens>,
    <tool_uses>,<duration_ms>``) followed by the four per-dispatch context-load
    columns appended at the END (``input_tokens``, ``output_tokens``,
    ``cache_read_input_tokens``, ``cache_creation_input_tokens``) — the
    per-DISPATCH counterpart to the per-PHASE four-field view ``enrich`` writes.
    Each context-load column defaults to 0 when its flag is omitted, mirroring
    the existing optional ``--total-tokens`` / ``--tool-uses`` / ``--duration-ms``
    fields. Appending at the END keeps the legacy five columns positionally
    unchanged so the existing plan-retrospective reader stays valid. The file's
    first line is a TOON-tabular header declaring the column order. The
    canonical column order / count / defaults are owned by
    ``standards/data-format.md`` (Per-Dispatch Context-Load Attribution section).
    """
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid phase: {phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    cause = args.termination_cause
    if cause not in DISPATCH_TERMINATION_CAUSES:
        return {
            'status': 'error',
            'error': 'invalid_termination_cause',
            'message': (
                f'Invalid termination_cause: {cause}. '
                f'Must be one of: {", ".join(DISPATCH_TERMINATION_CAUSES)}'
            ),
        }

    total_tokens = args.total_tokens if args.total_tokens is not None else 0
    tool_uses = args.tool_uses if args.tool_uses is not None else 0
    duration_ms = args.duration_ms if args.duration_ms is not None else 0
    # Four per-dispatch context-load columns (the four-field message.usage view at
    # dispatch termination). Each defaults to 0 when its flag is omitted, mirroring
    # the legacy optional fields above. Canonical column order / count / defaults
    # live in standards/data-format.md (Per-Dispatch Context-Load Attribution).
    input_tokens = getattr(args, 'input_tokens', 0) or 0
    output_tokens = getattr(args, 'output_tokens', 0) or 0
    cache_read_input_tokens = getattr(args, 'cache_read_input_tokens', 0) or 0
    cache_creation_input_tokens = getattr(args, 'cache_creation_input_tokens', 0) or 0

    # Guard at script side: refuse to record a dispatch boundary when the
    # plan directory does not exist (and was never initialised by phase-1).
    # Without this guard the `path.parent.mkdir(parents=True, ...)` below
    # silently creates an orphan plan tree just to hold the boundaries file.
    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    path = _dispatch_boundary_path(plan_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = now_utc_iso()
    # Legacy five columns first, then the four context-load columns appended at
    # the END so legacy readers stay positionally valid.
    row = (
        f'{timestamp},{cause},{total_tokens},{tool_uses},{duration_ms},'
        f'{input_tokens},{output_tokens},{cache_read_input_tokens},{cache_creation_input_tokens}'
    )

    if path.exists():
        existing = path.read_text(encoding='utf-8')
        if not existing.endswith('\n'):
            existing += '\n'
        new_content = existing + row + '\n'
    else:
        # Header documents the column contract for downstream readers.
        header = (
            f'plan_id: {plan_id}\n'
            f'phase: {phase}\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
            'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:\n'
        )
        new_content = header + row + '\n'

    atomic_write_file(path, new_content)

    # Count rows by counting the data lines (everything after the header lines).
    row_count = sum(
        1
        for line in new_content.splitlines()
        if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'termination_cause': cause,
        'total_tokens': total_tokens,
        'tool_uses': tool_uses,
        'duration_ms': duration_ms,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cache_read_input_tokens': cache_read_input_tokens,
        'cache_creation_input_tokens': cache_creation_input_tokens,
        'timestamp': timestamp,
        'rows_recorded': row_count,
        'dispatch_boundary_file': str(path.relative_to(get_plan_dir(plan_id))),
    }


def _phase_window_lookup(plan_id: str) -> list[tuple[str, datetime, datetime]]:
    """Return [(phase, start, end), ...] for phases with full timestamps."""
    data = read_metrics_raw(plan_id)
    windows: list[tuple[str, datetime, datetime]] = []
    for phase_name in PHASE_NAMES:
        phase_data = data.get('phases', {}).get(phase_name)
        if not phase_data:
            continue
        start_str = phase_data.get('start_time')
        end_str = phase_data.get('end_time')
        if not start_str or not end_str:
            continue
        try:
            start_dt = datetime.fromisoformat(str(start_str))
            end_dt = datetime.fromisoformat(str(end_str))
        except (ValueError, TypeError):
            continue
        windows.append((phase_name, start_dt, end_dt))
    return windows


def _run_normalized_tokens_op(
    session_id: str,
    windows: list[tuple[str, datetime, datetime]],
) -> tuple[dict[str, dict[str, int]] | None, dict[str, int], str | None]:
    """Invoke the platform-runtime ``metrics normalized-tokens`` op.

    The runtime owns the entire transcript engine (transcript discovery, JSONL
    parse, ``message.usage`` four-field parse, ``<usage>`` tag parse, cache-pricing
    weights). ``manage-metrics`` never parses a transcript itself — it hands the
    op the phase windows, lets the runtime write the per-phase normalized result
    to a JSON sidecar, then reads that file and persists the numbers.

    Returns ``(per_phase, counters, status)`` where:

    - ``per_phase`` maps each phase to its normalized bucket (or ``None`` on a
      ``no-op`` — no transcript — or any failure), and
    - ``counters`` carries the runtime's attribution counters (empty on no-op), and
    - ``status`` is the runtime op's TOON ``status`` field (``success`` / ``no-op``
      / ``error``) or ``None`` when the op could not be invoked.
    """
    serialized_windows = [[name, start.isoformat(), end.isoformat()] for name, start, end in windows]

    with tempfile.TemporaryDirectory(prefix='metrics-norm-tokens-') as tmpdir:
        windows_file = Path(tmpdir) / 'windows.json'
        output_file = Path(tmpdir) / 'normalized.json'
        windows_file.write_text(json.dumps(serialized_windows), encoding='utf-8')

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    '.plan/execute-script.py',
                    'plan-marshall:platform-runtime:platform_runtime',
                    'metrics',
                    'normalized-tokens',
                    '--session-id',
                    session_id,
                    '--windows-file',
                    str(windows_file),
                    '--output-file',
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return None, {}, None

        try:
            parsed = parse_toon(result.stdout)
        except (ValueError, KeyError):
            parsed = {}
        status = parsed.get('status')

        if status != 'success' or not output_file.is_file():
            return None, {}, status

        try:
            per_phase = json.loads(output_file.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None, {}, status
        if not isinstance(per_phase, dict):
            return None, {}, status

        counters = {
            key: int(parsed[key])
            for key in (
                'message_count',
                'subagent_phases_attributed',
                'subagent_calls_attributed',
                'subagent_transcripts_walked',
                'four_field_phases_attributed',
                # Run-level count of tool names outside the classifier's
                # population-derived domain — non-zero means a new tool name was
                # counted rather than dropped, and the classifier needs extending.
                'unclassified_tool_calls',
            )
            if isinstance(parsed.get(key), (int, str)) and str(parsed.get(key)).isdigit()
        }
        return per_phase, counters, status


_INLINE_MAIN_CONTEXT_FIELDS = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens')

# Exploration-share buckets, in report order. ``exploration + work + execute`` is
# the share denominator; ``orchestration`` and ``unclassified`` are carried so the
# buckets partition the observed tool-call population and the exclusion from the
# ratio stays auditable.
#
# SOURCE OF TRUTH is the platform-runtime contract — ``Runtime.metrics_normalized_
# tokens.__doc__``'s per-phase bucket declaration (mirrored in
# ``platform-runtime/standards/contract.md``). This tuple is a hand-mirror of that
# declaration because manage-metrics runs in a DIFFERENT process from the runtime
# producer and cannot import ``claude_runtime._TOOL_BUCKET_NAMES`` across that
# boundary. The mirror is held honest by the contract-drift test
# ``test_exploration_buckets_match_platform_runtime_contract`` in
# ``test/plan-marshall/manage-metrics/test_manage_metrics.py``, which parses the
# same contract docstring and fails loudly when a bucket is added on either side —
# so a new bucket cannot silently under-persist or under-render here.
_EXPLORATION_BUCKETS = ('exploration', 'work', 'execute', 'orchestration', 'unclassified')

# The per-phase counter fields the platform-runtime transcript engine supplies.
# Persisted and rendered on a PRESENCE test, never a truthiness test — see the
# render-guard divergence note at the per-phase render.
_EXPLORATION_COUNTER_FIELDS = tuple(
    f'{bucket}_{measure}'
    for bucket in _EXPLORATION_BUCKETS
    for measure in ('tool_calls', 'result_bytes')
)


def _inline_main_context_sum(phase_row: dict) -> int:
    """Sum a phase row's inline-attributable four-field usage.

    ``input_tokens + output_tokens + cache_creation_input_tokens`` —
    ``cache_read_input_tokens`` is EXCLUDED so the figure matches the
    dispatched-``<usage>`` total definition (fed via ``end-phase
    --total-tokens``, which also excludes cache reads). One derivation serves
    both signatures below: it is always written to
    ``inline_main_context_tokens``, and on the inline-only signature it is ALSO
    folded into ``total_tokens`` (which the row's
    ``total_tokens_population`` then labels ``inline``).
    """
    return sum(
        int(phase_row[field])
        for field in _INLINE_MAIN_CONTEXT_FIELDS
        if isinstance(phase_row.get(field), (int, float))
    )


def cmd_enrich(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)
    session_id = args.session_id

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    # Storage/aggregation role only: read this plan's own phase windows, hand them
    # to the platform-runtime transcript engine, and persist the normalized numbers
    # it returns. manage-metrics never parses a transcript itself.
    windows = _phase_window_lookup(plan_id)
    per_phase, counters, status = _run_normalized_tokens_op(session_id, windows)

    if per_phase is None:
        # no-op (no transcript on this target) or the op could not run — degrade
        # gracefully: nothing to enrich.
        return {
            'status': 'success',
            'plan_id': plan_id,
            'enriched': False,
            'message': f'No normalized-token data for session {session_id} (runtime status: {status})',
        }

    # Persist the runtime-computed per-phase normalized view. The runtime returns
    # both the four-field usage view (under the canonical message.usage keys) plus
    # the billing-weighted total, and the subagent <usage> attribution.
    data = read_metrics_raw(plan_id)
    data['session_message_count'] = counters.get('message_count', 0)
    data['updated'] = now_utc_iso()

    phases_state = data.setdefault('phases', {})

    for phase_name, bucket in per_phase.items():
        if not isinstance(bucket, dict):
            continue
        phase_row = phases_state.setdefault(phase_name, {})
        for field in (
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ):
            if field in bucket:
                phase_row[field] = bucket[field]
        if 'billing_weighted_total' in bucket:
            phase_row['billing_weighted_total'] = bucket['billing_weighted_total']
        if 'subagent_total_tokens' in bucket:
            phase_row['subagent_total_tokens'] = bucket['subagent_total_tokens']
            phase_row['subagent_tool_uses'] = bucket.get('subagent_tool_uses', 0)
            phase_row['subagent_duration_ms'] = bucket.get('subagent_duration_ms', 0)
            phase_row['subagent_samples'] = bucket.get('subagent_samples', 0)

        # Exploration-share counters, written on a PRESENCE test. A runtime that
        # declines the transcript primitive supplies no counter at all, and
        # defaulting an absent counter to 0 would assert a measurement that was
        # never taken — making "never measured" indistinguishable from "measured,
        # and it explored nothing". A MEASURED zero IS persisted, as 0.
        for field in _EXPLORATION_COUNTER_FIELDS:
            if field in bucket:
                phase_row[field] = bucket[field]

        # Attribute the phase's inline main-context spend, and RECORD which
        # population the row's total_tokens ends up measuring.
        #
        # A phase that ran inline in the main context (phase-1-init, and the
        # recipe-inline refine/outline phases) produces no agent `<usage>`
        # envelope and no accumulator, so its closing phase-boundary omitted
        # --total-tokens and the row carries no total_tokens — yet enrich has
        # just attributed the parent-window `message.usage` data to it. Folding
        # that sum into total_tokens is DELIBERATE and stays: it is what keeps
        # the phase countable in the breakdown (the report reads n=6/6, not
        # n=5/6) and what keeps every downstream zero-token predicate off a
        # phase that really did cost something.
        #
        # What the fold must not do is present a main-context measurement under
        # a field named for the dispatched population, so it is accompanied by
        # two records, written together and never apart:
        #   * inline_main_context_tokens — the same figure under its own
        #     population-honest name, written on BOTH the inline-only and the
        #     mixed signature, so the inline measurement is never readable ONLY
        #     through a dispatched-population field.
        #   * total_tokens_population — the discriminator every render site and
        #     every consumer reads to know which population total_tokens
        #     measures on THIS row.
        #
        # The sum is input_tokens + output_tokens + cache_creation_input_tokens
        # ONLY — cache_read_input_tokens is EXCLUDED so the figure matches the
        # dispatched-phase `<usage>` total definition, which is fed via
        # end-phase --total-tokens and also excludes cache reads. Including
        # cache_read (two orders of magnitude larger — plan-13 archive: 1-init
        # 11.16M dominated by 11.09M cache_read) would over-count the inline row
        # by ~100x versus comparable dispatched rows. The four raw usage fields
        # stay persisted on the row above for billing analysis; only the derived
        # figure narrows.
        #
        # Explicit-wins throughout: a total_tokens already set by a dispatched
        # phase's `<usage>` / accumulator is truthy here and is NEVER
        # overwritten. The #812 `end_time`-keyed partial verdict is untouched —
        # a timestamps-only inline close stays non-`partial`.
        inline_main_context = _inline_main_context_sum(phase_row)
        if not phase_row.get('total_tokens'):
            # Inline-only signature: no dispatched total exists to preserve.
            if inline_main_context:
                phase_row['total_tokens'] = inline_main_context
                phase_row['inline_main_context_tokens'] = inline_main_context
                phase_row['total_tokens_population'] = POPULATION_INLINE
            else:
                phase_row['total_tokens_population'] = POPULATION_DISPATCHED
        elif inline_main_context:
            # Mixed signature (the 6-finalize shape): dispatched steps AND
            # inline main-context steps both ran in this window. total_tokens
            # stays the dispatched measurement; the inline part is a separate
            # field of a different population, not an addend.
            phase_row['inline_main_context_tokens'] = inline_main_context
            phase_row['total_tokens_population'] = POPULATION_MIXED
        else:
            phase_row['total_tokens_population'] = POPULATION_DISPATCHED

    write_metrics(plan_id, data)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'enriched': True,
        'message_count': counters.get('message_count', 0),
        'subagent_phases_attributed': counters.get('subagent_phases_attributed', 0),
        'subagent_calls_attributed': counters.get('subagent_calls_attributed', 0),
        'subagent_transcripts_walked': counters.get('subagent_transcripts_walked', 0),
        'four_field_phases_attributed': counters.get('four_field_phases_attributed', 0),
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Plan metrics collection and reporting', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # start-phase
    sp = subparsers.add_parser('start-phase', help='Record phase start timestamp', allow_abbrev=False)
    add_plan_id_arg(sp)
    add_phase_arg(sp)
    sp.set_defaults(func=cmd_start_phase)

    # end-phase
    ep = subparsers.add_parser(
        'end-phase', help='Record phase end timestamp and optional token data', allow_abbrev=False
    )
    add_plan_id_arg(ep)
    add_phase_arg(ep)
    ep.add_argument('--total-tokens', type=int, default=None, help='Total tokens from Task agent <usage>')
    ep.add_argument('--duration-ms', type=int, default=None, help='Duration in ms from Task agent <usage>')
    ep.add_argument('--tool-uses', type=int, default=None, help='Tool use count from Task agent <usage>')
    ep.add_argument(
        '--retrospective-tokens',
        type=int,
        default=None,
        help='Tokens attributable to the plan-retrospective dispatch within this phase window (recorded as the retrospective_tokens sub-field; default-absent)',
    )
    ep.set_defaults(func=cmd_end_phase)

    # generate
    gp = subparsers.add_parser('generate', help='Generate metrics.md from collected data', allow_abbrev=False)
    add_plan_id_arg(gp)
    gp.set_defaults(func=cmd_generate)

    # print-phase-breakdown
    pb_print = subparsers.add_parser(
        'print-phase-breakdown',
        help='Extract the ## Phase Breakdown section from metrics.md and persist it',
        description=(
            'Read metrics.md from the live plan directory, extract only the '
            '## Phase Breakdown section (table from heading to the next ## '
            'heading or EOF), and persist it. Default behavior writes the '
            "section verbatim to the plan-relative artifact path "
            f"'{PHASE_BREAKDOWN_DEFAULT_OUTPUT}' and emits a TOON envelope "
            '{status, plan_id, file, bytes_written}. Pass an explicit '
            "--output-file PATH to override the artifact path (plan-relative "
            'only; absolute paths are rejected). Pass --output-file - to use '
            'legacy stdout-only mode: the section is written verbatim to '
            'stdout with no TOON envelope (handy for ad-hoc inspection). On '
            'error (metrics.md missing, section missing, invalid path), a '
            'standard error TOON is emitted.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(pb_print)
    pb_print.add_argument(
        '--output-file',
        dest='output_file',
        default=None,
        help=(
            'Plan-relative artifact path to write the extracted section to '
            f"(default: '{PHASE_BREAKDOWN_DEFAULT_OUTPUT}'). Use '-' for "
            'stdout-only mode (legacy behavior, no TOON envelope).'
        ),
    )
    pb_print.set_defaults(func=cmd_print_phase_breakdown)

    # phase-boundary (fused end-phase + start-phase + generate)
    pb = subparsers.add_parser(
        'phase-boundary',
        help='Atomically end the previous phase, start the next, and regenerate metrics.md',
        description=(
            'Fused phase-transition recorder. Equivalent to running '
            '`end-phase --phase {prev}` (with the optional --total-tokens / '
            '--duration-ms / --tool-uses flags), then `start-phase --phase '
            '{next}`, then `generate`. Persisted output (work/metrics.toon and '
            'metrics.md) is identical to the three-call sequence.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(pb)
    pb.add_argument('--prev-phase', required=True, help='Phase name being closed (e.g. 1-init)')
    pb.add_argument('--next-phase', required=True, help='Phase name being entered (e.g. 2-refine)')
    pb.add_argument('--total-tokens', type=int, default=None, help='Total tokens forwarded to end-phase (optional)')
    pb.add_argument(
        '--duration-ms', type=int, default=None, help='Agent duration (ms) forwarded to end-phase (optional)'
    )
    pb.add_argument('--tool-uses', type=int, default=None, help='Tool use count forwarded to end-phase (optional)')
    pb.add_argument(
        '--retrospective-tokens',
        type=int,
        default=None,
        help='Tokens attributable to the plan-retrospective dispatch within the closing phase window (recorded as the retrospective_tokens sub-field; default-absent)',
    )
    pb.set_defaults(func=cmd_phase_boundary)

    # boundary-status (read-only resume-time half-stamped-boundary detector)
    bs = subparsers.add_parser(
        'boundary-status',
        help='Classify a phase boundary as stamped / missing / not_applicable (read-only)',
        description=(
            'Read-only resume-time detector for a half-stamped metrics phase '
            'boundary. Reads work/metrics.toon and classifies the boundary into '
            '--next-phase as one of: stamped (prev has start+end AND next has a '
            'start), missing (prev has a start but no end, OR next has no start), '
            'or not_applicable (a --prev-phase was supplied but never started). '
            'Performs ZERO mutation — it is the detection half of resume-time '
            'boundary reconciliation. The orchestrator calls it on cross-session '
            'resume before dispatching the current phase; on a missing verdict it '
            'stamps the boundary via `phase-boundary` even when the status '
            'transition already happened. Supply --prev-phase + --next-phase for '
            'a full boundary check, or --next-phase alone to check only the '
            '"current phase has no start" condition.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(bs)
    bs.add_argument('--prev-phase', default=None, help='Phase that should have been closed (optional)')
    bs.add_argument('--next-phase', required=True, help='Phase being entered on resume')
    bs.set_defaults(func=cmd_boundary_status)

    # accumulate-agent-usage
    acc = subparsers.add_parser(
        'accumulate-agent-usage',
        help='Persist running per-phase totals of subagent <usage> data',
        description=(
            'Add the supplied --total-tokens / --tool-uses / --duration-ms '
            'values to the per-phase accumulator file at '
            'work/metrics-accumulator-{phase}.toon, incrementing the samples '
            'counter. Initialises the file when absent and is idempotent across '
            'successive calls. cmd_end_phase / cmd_phase_boundary read this '
            'file as a fallback when their corresponding flags are omitted.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(acc)
    add_phase_arg(acc)
    acc.add_argument('--total-tokens', type=int, default=None, help='Subagent total_tokens to add to the running total')
    acc.add_argument('--tool-uses', type=int, default=None, help='Subagent tool_uses to add to the running total')
    acc.add_argument('--duration-ms', type=int, default=None, help='Subagent duration_ms to add to the running total')
    acc.add_argument(
        '--retrospective-tokens',
        type=int,
        default=None,
        help=(
            'Tokens attributable to the plan-retrospective dispatch to add to the running '
            'retrospective_tokens total (forwarded only when the just-returned step is the '
            'opt-in retrospective step; cmd_end_phase / cmd_phase_boundary read it back as a fallback)'
        ),
    )
    acc.set_defaults(func=cmd_accumulate_agent_usage)

    # record-dispatch-boundary
    rdb = subparsers.add_parser(
        'record-dispatch-boundary',
        help='Record one tabular row per phase Task dispatch termination',
        description=(
            'Append a TOON row to work/metrics-dispatch-boundaries-{phase}.toon '
            'capturing the termination cause of a phase Task dispatch '
            '(voluntary_checkpoint | task_complete_returned_verbatim | '
            'budget_yield | harness_cancellation | error | '
            'clean_exit_queue_empty | step_complete | blocked_user_review | '
            'blocked_session_restart | task_batch_complete | agent_returned) '
            'and the '
            "dispatched agent's <usage> totals at the time of return. "
            '``clean_exit_queue_empty`` is the canonical value the '
            'orchestrator MUST use for a successful loop-exit (queue '
            'genuinely empty, verified by ``manage-tasks loop-exit-guard``); '
            'the recorder no longer accepts the legacy fallback value '
            '``unknown`` — missing or unrecognised causes are script errors. '
            'The orchestrator invokes this on every phase Task return so '
            'plan-retrospective can correlate agent-initiated re-dispatch '
            'events with [OUTCOME]-log coverage gaps.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(rdb)
    add_phase_arg(rdb)
    rdb.add_argument(
        '--termination-cause',
        required=True,
        choices=list(DISPATCH_TERMINATION_CAUSES),
        help='Why the phase Task dispatch terminated.',
    )
    rdb.add_argument(
        '--total-tokens',
        type=int,
        default=None,
        help="Subagent total_tokens at termination (from the agent's <usage>).",
    )
    rdb.add_argument(
        '--tool-uses',
        type=int,
        default=None,
        help="Subagent tool_uses at termination (from the agent's <usage>).",
    )
    rdb.add_argument(
        '--duration-ms',
        type=int,
        default=None,
        help="Subagent duration_ms at termination (from the agent's <usage>).",
    )
    rdb.add_argument(
        '--input-tokens',
        type=int,
        default=None,
        help="Dispatch context-load input_tokens at termination (message.usage; default 0).",
    )
    rdb.add_argument(
        '--output-tokens',
        type=int,
        default=None,
        help="Dispatch context-load output_tokens at termination (message.usage; default 0).",
    )
    rdb.add_argument(
        '--cache-read-input-tokens',
        type=int,
        default=None,
        help="Dispatch context-load cache_read_input_tokens at termination (message.usage; default 0).",
    )
    rdb.add_argument(
        '--cache-creation-input-tokens',
        type=int,
        default=None,
        help="Dispatch context-load cache_creation_input_tokens at termination (message.usage; default 0).",
    )
    rdb.set_defaults(func=cmd_record_dispatch_boundary)

    # enrich
    enr = subparsers.add_parser('enrich', help='Enrich metrics from JSONL transcript', allow_abbrev=False)
    add_plan_id_arg(enr)
    add_session_id_arg(enr)
    enr.set_defaults(func=cmd_enrich)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    if not result.pop('_print_only', False):
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
