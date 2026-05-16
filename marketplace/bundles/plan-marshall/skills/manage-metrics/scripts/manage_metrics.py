#!/usr/bin/env python3
"""
CLI script for plan metrics collection and reporting.

Usage:
    Start phase timing:
        python3 manage_metrics.py start-phase --plan-id <id> --phase <phase>

    End phase timing:
        python3 manage_metrics.py end-phase --plan-id <id> --phase <phase> [--total-tokens N] [--duration-ms N] [--tool-uses N]

    Generate metrics.md:
        python3 manage_metrics.py generate --plan-id <id>

    Atomic phase boundary (end-phase + start-phase + generate):
        python3 manage_metrics.py phase-boundary --plan-id <id> \
            --prev-phase <prev> --next-phase <next> \
            [--total-tokens N] [--duration-ms N] [--tool-uses N]

    Accumulate per-phase subagent usage on disk:
        python3 manage_metrics.py accumulate-agent-usage --plan-id <id> --phase <phase> \
            [--total-tokens N] [--tool-uses N] [--duration-ms N]

    Enrich from JSONL transcript (per-phase subagent <usage>):
        python3 manage_metrics.py enrich --plan-id <id> --session-id <sid>
"""

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from constants import FILE_STATUS, FILE_WORK_METRICS, PHASES  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
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
from input_validation import (  # type: ignore[import-not-found]
    add_phase_arg,
    add_plan_id_arg,
    add_session_id_arg,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)

METRICS_FILE = FILE_WORK_METRICS
METRICS_MD = 'metrics.md'
PHASE_NAMES = list(PHASES)
ACCUMULATOR_FILE_TEMPLATE = 'work/metrics-accumulator-{phase}.toon'
DISPATCH_BOUNDARY_FILE_TEMPLATE = 'work/metrics-dispatch-boundaries-{phase}.toon'
ANCHOR_DEFAULT_PATH = '.plan/temp/refactor-execution-context-anchor/anchors.toon'
ANCHOR_DEFAULT_THRESHOLD_PERCENT = 20.0
DISPATCH_TERMINATION_CAUSES = (
    'voluntary_checkpoint',
    'task_complete_returned_verbatim',
    'harness_cancellation',
    'error',
    'clean_exit_queue_empty',
)
USAGE_TAG_RE = re.compile(r'<usage>([\s\S]*?)</usage>', re.MULTILINE)
USAGE_FIELD_RE = re.compile(r'^\s*(total_tokens|tool_uses|duration_ms)\s*:\s*(\d+)', re.MULTILINE)


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
        if key not in {'total_tokens', 'tool_uses', 'duration_ms', 'samples'}:
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
        f'samples: {totals["samples"]}',
        f'updated: {now_utc_iso()}',
    ]
    atomic_write_file(path, '\n'.join(lines) + '\n')


def _resolve_token_field(arg_value: int | None, accumulator: dict[str, int], key: str) -> int | None:
    """Explicit flag wins; fall back to accumulator value when flag is absent."""
    if arg_value is not None:
        return arg_value
    if key in accumulator:
        return accumulator[key]
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


def cmd_end_phase(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {'status': 'error', 'error': 'invalid_phase', 'message': f'Invalid phase: {phase}'}

    data = read_metrics_raw(plan_id)
    now = now_utc_iso()

    if phase not in data['phases']:
        data['phases'][phase] = {}

    phase_data = data['phases'][phase]
    phase_data['end_time'] = now

    # Compute duration from start/end if available
    start_str = phase_data.get('start_time')
    if start_str:
        try:
            start_dt = datetime.fromisoformat(str(start_str))
            end_dt = datetime.fromisoformat(now)
            duration_s = (end_dt - start_dt).total_seconds()
            phase_data['duration_seconds'] = round(duration_s, 1)
        except (ValueError, TypeError):
            pass

    # Read on-disk accumulator as fallback when explicit flags are absent.
    accumulator = _read_accumulator(plan_id, phase)
    duration_ms = _resolve_token_field(args.duration_ms, accumulator, 'duration_ms')
    total_tokens = _resolve_token_field(args.total_tokens, accumulator, 'total_tokens')
    tool_uses = _resolve_token_field(args.tool_uses, accumulator, 'tool_uses')

    if duration_ms is not None:
        phase_data['agent_duration_ms'] = duration_ms
        phase_data['agent_duration_seconds'] = round(duration_ms / 1000.0, 1)

    if total_tokens is not None:
        phase_data['total_tokens'] = total_tokens

    if tool_uses is not None:
        phase_data['tool_uses'] = tool_uses

    data['updated'] = now
    write_metrics(plan_id, data)

    result = {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'end_time': now,
    }
    if 'duration_seconds' in phase_data:
        result['duration_seconds'] = phase_data['duration_seconds']
    if total_tokens is not None:
        result['total_tokens'] = total_tokens
    if accumulator and args.total_tokens is None:
        result['accumulator_used'] = True

    return result


def cmd_generate(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)

    data = read_metrics_raw(plan_id)
    phases = data.get('phases', {})

    if not phases:
        return {'status': 'error', 'error': 'no_data', 'message': 'No metrics data found'}

    # Build metrics.md content
    lines = []
    lines.append(f'# Metrics: {plan_id}')
    lines.append('')
    lines.append(f'Generated: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}')
    lines.append('')

    # Phase breakdown table
    lines.append('## Phase Breakdown')
    lines.append('')
    lines.append('| Phase | Duration | Tokens | Tool Uses |')
    lines.append('|-------|----------|--------|-----------|')

    # Collect breakdown rows (phases that exist) preserving canonical phase order.
    breakdown_rows = [(name, phases[name]) for name in PHASE_NAMES if name in phases]
    breakdown_n = len(breakdown_rows)

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

    def _duration_cell(phase: dict) -> tuple[str, float | None]:
        """Return (rendered_cell, value_for_total).

        Per-cell rule: prefer phase.duration_seconds; fall back to phase.agent_duration_seconds
        formatted as '{value}s (agent)'; render '-' when both are absent.
        Total aggregates whatever value contributed to the per-cell render.
        """
        wall = _numeric(phase.get('duration_seconds'))
        if wall is not None:
            return format_duration(float(wall)), float(wall)
        agent = _numeric(phase.get('agent_duration_seconds'))
        if agent is not None:
            return f'{agent}s (agent)', float(agent)
        return '-', None

    # Per-column value subsets (for Total aggregation and partial-marker decisions).
    duration_values: list[float] = []
    tokens_values: list[int] = []
    tool_uses_values: list[int] = []

    for phase_name, phase in breakdown_rows:
        duration_str, duration_val = _duration_cell(phase)
        if duration_val is not None:
            duration_values.append(duration_val)

        tokens = _numeric(phase.get('total_tokens'))
        tokens_str = f'{int(tokens):,}' if tokens is not None else '-'
        if tokens is not None:
            tokens_values.append(int(tokens))

        tool_uses = _numeric(phase.get('tool_uses'))
        tool_uses_str = str(int(tool_uses)) if tool_uses is not None else '-'
        if tool_uses is not None:
            tool_uses_values.append(int(tool_uses))

        lines.append(f'| {phase_name} | {duration_str} | {tokens_str} | {tool_uses_str} |')

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

    total_duration_str = _total_str(duration_values, lambda n: format_duration(float(n)), is_duration=True)
    total_tokens_str = _total_str(tokens_values, lambda n: f'{n:,}')
    total_tool_uses_str = _total_str(tool_uses_values, str)

    lines.append(
        f'| **Total** | **{total_duration_str}** | **{total_tokens_str}** | **{total_tool_uses_str}** |'
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

        duration = phase.get('duration_seconds')
        if duration:
            lines.append(f'- **Wall-clock duration**: {format_duration(float(duration))}')

        agent_dur = phase.get('agent_duration_seconds')
        if agent_dur:
            lines.append(f'- **Agent duration**: {format_duration(float(agent_dur))}')

        tokens = phase.get('total_tokens')
        if tokens:
            lines.append(f'- **Total tokens**: {int(tokens):,}')

        tool_uses = phase.get('tool_uses')
        if tool_uses:
            lines.append(f'- **Tool uses**: {int(tool_uses)}')

        lines.append('')

    md_content = '\n'.join(lines)
    md_path = get_plan_dir(plan_id) / METRICS_MD
    atomic_write_file(md_path, md_content)

    total_duration = sum(duration_values)
    total_tokens = sum(tokens_values)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': METRICS_MD,
        'phases_recorded': len(phases),
        'total_duration_seconds': round(total_duration, 1),
        'total_tokens': total_tokens,
        'total_duration_formatted': format_duration(total_duration),
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
    """Print the '## Phase Breakdown' section from metrics.md to stdout.

    On success, writes the section verbatim to stdout (no trailing TOON) and
    returns a result dict carrying the ``_print_only`` sentinel so ``main``
    skips the standard TOON emission. On error (missing metrics.md, missing
    section), returns a normal error TOON via the standard emit path.
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
    sys.stdout.write(section)
    sys.stdout.flush()
    return {
        '_print_only': True,
        'status': 'success',
        'plan_id': plan_id,
        'bytes_written': len(section.encode('utf-8')),
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

    # Step 1: end the previous phase (mirrors cmd_end_phase semantics).
    data = read_metrics_raw(plan_id)
    end_now = now_utc_iso()

    if prev_phase not in data['phases']:
        data['phases'][prev_phase] = {}
    prev_data = data['phases'][prev_phase]
    prev_data['end_time'] = end_now

    # 1-init structural backfill: when transitioning out of 1-init for the
    # first time the phase row never went through cmd_start_phase, so
    # start_time is absent. Source it from status.json.created so the
    # duration-computation path below catches the backfill and writes
    # duration_seconds in the same call.
    if prev_phase == '1-init' and not prev_data.get('start_time'):
        created_ts = _read_status_created(plan_id)
        if created_ts is not None:
            prev_data['start_time'] = created_ts

    start_str = prev_data.get('start_time')
    if start_str:
        try:
            start_dt = datetime.fromisoformat(str(start_str))
            end_dt = datetime.fromisoformat(end_now)
            duration_s = (end_dt - start_dt).total_seconds()
            prev_data['duration_seconds'] = round(duration_s, 1)
        except (ValueError, TypeError):
            pass

    accumulator = _read_accumulator(plan_id, prev_phase)
    duration_ms = _resolve_token_field(args.duration_ms, accumulator, 'duration_ms')
    total_tokens = _resolve_token_field(args.total_tokens, accumulator, 'total_tokens')
    tool_uses = _resolve_token_field(args.tool_uses, accumulator, 'tool_uses')

    if duration_ms is not None:
        prev_data['agent_duration_ms'] = duration_ms
        prev_data['agent_duration_seconds'] = round(duration_ms / 1000.0, 1)
    if total_tokens is not None:
        prev_data['total_tokens'] = total_tokens
    if tool_uses is not None:
        prev_data['tool_uses'] = tool_uses

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
    }
    if 'duration_seconds' in prev_data:
        result['prev_duration_seconds'] = prev_data['duration_seconds']
    if total_tokens is not None:
        result['prev_total_tokens'] = total_tokens
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


def cmd_accumulate_agent_usage(args: argparse.Namespace) -> dict:
    """Persist running per-phase totals of subagent <usage> data.

    Reads `.plan/plans/{plan_id}/work/metrics-accumulator-{phase}.toon`
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

    existing = _read_accumulator(plan_id, phase)
    totals = {
        'total_tokens': int(existing.get('total_tokens', 0)),
        'tool_uses': int(existing.get('tool_uses', 0)),
        'duration_ms': int(existing.get('duration_ms', 0)),
        'samples': int(existing.get('samples', 0)),
    }
    if args.total_tokens is not None:
        totals['total_tokens'] += args.total_tokens
    if args.tool_uses is not None:
        totals['tool_uses'] += args.tool_uses
    if args.duration_ms is not None:
        totals['duration_ms'] += args.duration_ms
    totals['samples'] += 1

    _write_accumulator(plan_id, phase, totals)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'total_tokens': totals['total_tokens'],
        'tool_uses': totals['tool_uses'],
        'duration_ms': totals['duration_ms'],
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
    `[OUTCOME]`-coverage gaps caused by agent-initiated re-dispatch — see
    lesson 2026-05-08-14-001.

    The file uses the same column layout for every row so plan-retrospective
    fact extractors can ingest it without a schema lookup. Each row is a
    single line in the form ``<timestamp>,<termination_cause>,
    <total_tokens>,<tool_uses>,<duration_ms>``. The file's first line is a
    TOON-tabular header declaring the column order.
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

    # Guard at script side: refuse to record a dispatch boundary when the
    # plan directory does not exist (and was never initialised by phase-1).
    # Without this guard the `path.parent.mkdir(parents=True, ...)` below
    # silently creates an orphan plan tree just to hold the boundaries file.
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

    path = _dispatch_boundary_path(plan_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = now_utc_iso()
    row = f'{timestamp},{cause},{total_tokens},{tool_uses},{duration_ms}'

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
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
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


def _attribute_subagent_usage(
    timestamp_iso: str | None,
    windows: list[tuple[str, datetime, datetime]],
    body: str,
    per_phase: dict[str, dict[str, int]],
) -> bool:
    """Parse a `<usage>` body and add its totals to the matching phase row.

    Returns True when the totals were attributed, False when no phase window
    contained the timestamp (out-of-window agent calls are ignored).
    """
    if not timestamp_iso:
        return False
    try:
        ts = datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return False

    matching_phase: str | None = None
    # Iterate latest-first so a timestamp that lands exactly on a phase
    # boundary (end_time of phase N == start_time of phase N+1) is attributed
    # to the newer phase. This matches the semantic intent of phase
    # transitions as instantaneous handoffs.
    for phase_name, start_dt, end_dt in reversed(windows):
        if start_dt <= ts <= end_dt:
            matching_phase = phase_name
            break
    if matching_phase is None:
        return False

    fields = {match.group(1): int(match.group(2)) for match in USAGE_FIELD_RE.finditer(body)}
    bucket = per_phase.setdefault(
        matching_phase,
        {'total_tokens': 0, 'tool_uses': 0, 'duration_ms': 0, 'samples': 0},
    )
    bucket['total_tokens'] += fields.get('total_tokens', 0)
    bucket['tool_uses'] += fields.get('tool_uses', 0)
    bucket['duration_ms'] += fields.get('duration_ms', 0)
    bucket['samples'] += 1
    return True


def _extract_text_payload(content: object) -> str:
    """Best-effort flattening of a tool_result content payload to a single string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get('text') or item.get('content')
                if isinstance(text, str):
                    chunks.append(text)
        return '\n'.join(chunks)
    return ''


def _parse_anchor_file(path: Path) -> tuple[dict[str, dict[str, int]], dict, str | None]:
    """Parse the anchor TOON file.

    Returns:
        (per_plan_phase_totals, metadata, error). On parse failure
        ``error`` is a human-readable message and the other return
        values are empty.

    The anchor file's authoritative shape is described in
    ``.plan/temp/refactor-execution-context-anchor/anchors.toon``:

    - One ``anchors[N]`` row per source plan (informational; only
      ``plan_id`` and ``description`` are used).
    - A ``phases:`` block keyed by plan_id mapping each phase to the
      anchor ``total_tokens`` (or ``-1`` for "(not recorded)").
    - A ``threshold:`` block with ``warn_percent``.

    The parser is intentionally narrow — only the per-phase totals and
    the threshold are needed for ``compare-anchor`` to produce its
    table.
    """
    if not path.exists():
        return {}, {}, f'anchor file not found: {path}'
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        return {}, {}, f'cannot read anchor file: {exc}'

    per_plan: dict[str, dict[str, int]] = {}
    metadata: dict = {}
    in_phases = False
    in_threshold = False
    current_plan_id: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        leading = len(line) - len(line.lstrip(' '))
        stripped = line.lstrip(' ')

        if stripped.startswith('phases:'):
            in_phases = True
            in_threshold = False
            current_plan_id = None
            continue
        if stripped.startswith('threshold:'):
            in_threshold = True
            in_phases = False
            current_plan_id = None
            continue
        if stripped.startswith('anchors['):
            in_phases = False
            in_threshold = False
            continue

        if in_phases:
            if leading == 2 and stripped.endswith(':'):
                current_plan_id = stripped[:-1].strip()
                per_plan.setdefault(current_plan_id, {})
                continue
            if leading == 4 and current_plan_id and ':' in stripped:
                phase_key, _, raw_val = stripped.partition(':')
                phase_key = phase_key.strip()
                raw_val = raw_val.strip()
                try:
                    per_plan[current_plan_id][phase_key] = int(raw_val)
                except ValueError:
                    return (
                        {},
                        {},
                        (
                            f"malformed token count '{raw_val}' for phase "
                            f"'{phase_key}' in plan '{current_plan_id}' "
                            f'(anchor file {path})'
                        ),
                    )
            continue

        if in_threshold:
            if leading == 2 and ':' in stripped:
                key, _, raw_val = stripped.partition(':')
                key = key.strip()
                raw_val = raw_val.strip()
                try:
                    metadata[key] = float(raw_val) if '.' in raw_val else int(raw_val)
                except ValueError:
                    metadata[key] = raw_val
            continue

    return per_plan, metadata, None


def _classify_delta(anchor: int, post: int, threshold_percent: float) -> tuple[float, str]:
    """Compute the percentage delta and the per-phase verdict label.

    Returns ``(percent_delta, verdict)`` where ``verdict`` is one of:

    - ``ok``         — delta is within threshold (no breach).
    - ``warn``       — growth exceeded threshold (regression gate fires).
    - ``improved``   — strictly negative delta (cheaper than anchor).
    - ``unmeasured`` — anchor or post value is missing (``-1``).
    """
    if anchor == -1 or post == -1:
        return 0.0, 'unmeasured'
    if anchor == 0:
        # Anchor recorded as zero is anomalous; treat as unmeasured.
        return 0.0, 'unmeasured'
    pct = (post - anchor) / anchor * 100.0
    if pct < 0.0:
        return pct, 'improved'
    if pct > threshold_percent:
        return pct, 'warn'
    return pct, 'ok'


def cmd_compare_anchor(args: argparse.Namespace) -> dict:
    """Compare per-phase ``total_tokens`` against anchor data.

    Loads the anchor TOON file (default
    ``.plan/temp/refactor-execution-context-anchor/anchors.toon``) and
    the live plan's ``work/metrics.toon``, computes per-phase deltas,
    and emits a TOON table. Driven by the Phase 4d dispatch-cost
    regression gate documented in
    ``.plan/local/refactor-agents-reviewed/07-rollout.md`` § 4.4.

    Inputs:
        ``--plan-id``        Live plan whose ``work/metrics.toon`` is
                             the post-refactor measurement set.
        ``--anchor-plan``    Anchor plan_id to compare against. Must be
                             present in the anchor file. Required.
        ``--anchor-file``    Override the default anchor file path.
        ``--threshold-percent``  Override the warn threshold (default
                             from the anchor file's ``threshold.warn_percent``
                             entry, or ``20`` when absent).

    Behaviour:
        - Anchor or live cell missing → ``verdict: unmeasured`` (no
          regression gate fire — one-sided measurement).
        - Live cell > anchor by more than ``threshold_percent`` →
          ``verdict: warn``; the gate has fired and the failing
          dispatch must be re-bundled or scripted.
        - Strict-negative delta → ``verdict: improved``; otherwise
          ``ok``.

    Output (TOON):
        ``rows[N]{phase,anchor_tokens,post_tokens,delta_tokens,delta_percent,verdict}``
        Plus aggregate fields ``gate_status``, ``warn_count``,
        ``unmeasured_count``, ``threshold_percent``,
        ``anchor_plan``, ``anchor_file``.
    """
    plan_id = require_valid_plan_id(args)
    anchor_plan = args.anchor_plan
    anchor_path = Path(args.anchor_file or ANCHOR_DEFAULT_PATH)

    per_plan_anchors, metadata, parse_error = _parse_anchor_file(anchor_path)
    if parse_error:
        return {'status': 'error', 'error': 'anchor_unreadable', 'message': parse_error}

    if anchor_plan not in per_plan_anchors:
        available = sorted(per_plan_anchors.keys())
        return {
            'status': 'error',
            'error': 'anchor_plan_not_found',
            'message': (
                f"anchor plan '{anchor_plan}' not present in {anchor_path}; "
                f'available: {available}'
            ),
        }

    raw_threshold: object
    if args.threshold_percent is not None:
        raw_threshold = args.threshold_percent
        threshold_source = '--threshold-percent'
    else:
        raw_threshold = metadata.get('warn_percent', ANCHOR_DEFAULT_THRESHOLD_PERCENT)
        threshold_source = 'anchor file threshold.warn_percent'
    try:
        threshold = float(raw_threshold)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return {
            'status': 'error',
            'error': 'invalid_threshold',
            'message': (
                f"threshold '{raw_threshold}' from {threshold_source} is not a "
                f'valid number'
            ),
        }

    live = read_metrics_raw(plan_id)
    live_phases = live.get('phases', {})
    anchor_phases = per_plan_anchors[anchor_plan]

    rows: list[dict] = []
    warn_count = 0
    unmeasured_count = 0
    for phase_name in PHASE_NAMES:
        anchor_tokens = anchor_phases.get(phase_name, -1)
        live_row = live_phases.get(phase_name, {})
        post_raw = live_row.get('total_tokens', -1) if isinstance(live_row, dict) else -1
        try:
            post_tokens = int(post_raw)
        except (TypeError, ValueError):
            post_tokens = -1

        pct, verdict = _classify_delta(anchor_tokens, post_tokens, threshold)
        if verdict == 'warn':
            warn_count += 1
        elif verdict == 'unmeasured':
            unmeasured_count += 1
        delta_tokens = post_tokens - anchor_tokens if verdict != 'unmeasured' else 0
        rows.append(
            {
                'phase': phase_name,
                'anchor_tokens': anchor_tokens,
                'post_tokens': post_tokens,
                'delta_tokens': delta_tokens,
                'delta_percent': round(pct, 2),
                'verdict': verdict,
            }
        )

    gate_status = 'breach' if warn_count > 0 else 'pass'

    return {
        'status': 'success',
        'plan_id': plan_id,
        'anchor_plan': anchor_plan,
        'anchor_file': str(anchor_path),
        'threshold_percent': threshold,
        'rows': rows,
        'gate_status': gate_status,
        'warn_count': warn_count,
        'unmeasured_count': unmeasured_count,
    }


def cmd_enrich(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)
    session_id = args.session_id

    # Find JSONL transcript file
    projects_dir = Path.home() / '.claude' / 'projects'
    transcript_path = None

    if projects_dir.exists():
        for session_dir in projects_dir.rglob('*'):
            if session_dir.is_dir() and session_id in session_dir.name:
                for jsonl_file in session_dir.glob('*.jsonl'):
                    transcript_path = jsonl_file
                    break
            if transcript_path:
                break

    if not transcript_path and projects_dir.exists():
        # Try direct session file pattern
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                candidate = project_dir / f'{session_id}.jsonl'
                if candidate.exists():
                    transcript_path = candidate
                    break

    if not transcript_path:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'enriched': False,
            'message': f'JSONL transcript not found for session {session_id}',
        }

    # Parse JSONL for subagent <usage> attribution and main-context message count.
    message_count = 0
    windows = _phase_window_lookup(plan_id)
    per_phase_subagent: dict[str, dict[str, int]] = {}
    subagent_calls_attributed = 0
    main_phases_attributed_set: set[str] = set()

    try:
        with open(transcript_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, AttributeError):
                    continue

                msg = entry.get('message', {}) if isinstance(entry, dict) else {}
                usage = msg.get('usage', {}) if isinstance(msg, dict) else {}
                if isinstance(usage, dict) and usage:
                    if usage.get('total_tokens') or usage.get('input_tokens') or usage.get('output_tokens'):
                        message_count += 1
                        if windows:
                            timestamp = entry.get('timestamp') if isinstance(entry, dict) else None
                            if isinstance(timestamp, str):
                                try:
                                    ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                except (ValueError, TypeError):
                                    ts = None
                                if ts is not None:
                                    for phase_name, start_dt, end_dt in reversed(windows):
                                        if start_dt <= ts <= end_dt:
                                            main_phases_attributed_set.add(phase_name)
                                            break

                # Subagent <usage> attribution: walk tool_result blocks (and any
                # other text content as a safety net) for <usage>...</usage>.
                if not windows:
                    continue
                content = msg.get('content') if isinstance(msg, dict) else None
                payloads: list[str] = []
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get('type') == 'tool_result':
                            payloads.append(_extract_text_payload(item.get('content')))
                        elif item.get('type') == 'text':
                            text = item.get('text')
                            if isinstance(text, str):
                                payloads.append(text)
                elif isinstance(content, str):
                    payloads.append(content)

                timestamp = entry.get('timestamp') if isinstance(entry, dict) else None
                for payload in payloads:
                    if not payload or '<usage>' not in payload:
                        continue
                    for tag_match in USAGE_TAG_RE.finditer(payload):
                        if _attribute_subagent_usage(timestamp, windows, tag_match.group(1), per_phase_subagent):
                            subagent_calls_attributed += 1
    except OSError:
        return {
            'status': 'error',
            'error': 'read_failed',
            'message': f'Cannot read transcript: {transcript_path}',
        }

    # Subagent transcript walk: confirms transcripts were found and walked
    # (per-message subagent main-context attribution removed along with the
    # broken input/output token representation).
    subagent_transcripts_walked = 0
    if windows:
        from manage_session import resolve_subagent_transcripts  # type: ignore[import-not-found]

        for _sub_path in resolve_subagent_transcripts(session_id):
            subagent_transcripts_walked += 1

    # Update metrics with enriched per-phase subagent totals.
    data = read_metrics_raw(plan_id)
    data['session_message_count'] = message_count
    data['updated'] = now_utc_iso()

    if per_phase_subagent:
        phases_state = data.setdefault('phases', {})
        for phase_name, totals in per_phase_subagent.items():
            phase_row = phases_state.setdefault(phase_name, {})
            phase_row['subagent_total_tokens'] = totals['total_tokens']
            phase_row['subagent_tool_uses'] = totals['tool_uses']
            phase_row['subagent_duration_ms'] = totals['duration_ms']
            phase_row['subagent_samples'] = totals['samples']

    write_metrics(plan_id, data)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'enriched': True,
        'message_count': message_count,
        'subagent_phases_attributed': len(per_phase_subagent),
        'subagent_calls_attributed': subagent_calls_attributed,
        'main_phases_attributed': len(main_phases_attributed_set),
        'subagent_transcripts_walked': subagent_transcripts_walked,
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
    ep.set_defaults(func=cmd_end_phase)

    # generate
    gp = subparsers.add_parser('generate', help='Generate metrics.md from collected data', allow_abbrev=False)
    add_plan_id_arg(gp)
    gp.set_defaults(func=cmd_generate)

    # print-phase-breakdown
    pb_print = subparsers.add_parser(
        'print-phase-breakdown',
        help='Extract and print the ## Phase Breakdown section from metrics.md',
        description=(
            'Read metrics.md from the live plan directory, extract only the '
            '## Phase Breakdown section (table from heading to the next ## '
            'heading or EOF), and print it verbatim to stdout. On success, '
            'TOON status output is suppressed so stdout contains only the '
            'section content (the new finalize-step skill captures it for '
            'the renderer). On error (metrics.md missing, section missing), '
            'a standard error TOON is emitted.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(pb_print)
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
    pb.set_defaults(func=cmd_phase_boundary)

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
    acc.set_defaults(func=cmd_accumulate_agent_usage)

    # record-dispatch-boundary
    rdb = subparsers.add_parser(
        'record-dispatch-boundary',
        help='Record one tabular row per phase Task dispatch termination',
        description=(
            'Append a TOON row to work/metrics-dispatch-boundaries-{phase}.toon '
            'capturing the termination cause of a phase Task dispatch '
            '(voluntary_checkpoint | task_complete_returned_verbatim | '
            'harness_cancellation | error | clean_exit_queue_empty) and the '
            "dispatched agent's <usage> totals at the time of return. "
            '``clean_exit_queue_empty`` is the canonical value the '
            'orchestrator MUST use for a successful loop-exit (queue '
            'genuinely empty, verified by ``manage-tasks loop-exit-guard``); '
            'the recorder no longer accepts the legacy fallback value '
            '``unknown`` — missing or unrecognised causes are script errors. '
            'The orchestrator invokes this on every phase Task return so '
            'plan-retrospective can correlate agent-initiated re-dispatch '
            'events with [OUTCOME]-log coverage gaps (lesson '
            '2026-05-08-14-001).'
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
    rdb.set_defaults(func=cmd_record_dispatch_boundary)

    # enrich
    enr = subparsers.add_parser('enrich', help='Enrich metrics from JSONL transcript', allow_abbrev=False)
    add_plan_id_arg(enr)
    add_session_id_arg(enr)
    enr.set_defaults(func=cmd_enrich)

    # compare-anchor
    cmp = subparsers.add_parser(
        'compare-anchor',
        help='Compare per-phase total_tokens against anchor data (dispatch-cost regression gate)',
        description=(
            'Load the anchor TOON file and the live plan metrics.toon, compute '
            'per-phase deltas, and emit a TOON table. Drives the Phase 4d '
            'dispatch-cost regression gate from the agents → execution-context '
            'refactor rollout (07-rollout.md § 4.4). A per-phase growth > '
            "--threshold-percent (default 20) fires gate_status: breach; the "
            'failing dispatch must be re-bundled or scripted before merge. '
            "Cells missing in either set are reported as verdict: unmeasured "
            '(one-sided measurement — no gate fire).'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(cmp)
    cmp.add_argument(
        '--anchor-plan',
        required=True,
        help='Anchor plan_id to compare against (must be present in --anchor-file).',
    )
    cmp.add_argument(
        '--anchor-file',
        default=None,
        help=(
            f'Path to the anchor TOON file. Defaults to {ANCHOR_DEFAULT_PATH} (the '
            'refactor-execution-context anchor set).'
        ),
    )
    cmp.add_argument(
        '--threshold-percent',
        type=float,
        default=None,
        help=(
            'Override the regression-gate threshold (percent growth that fires '
            'verdict: warn). Defaults to the anchor file\'s threshold.warn_percent '
            f'entry, or {ANCHOR_DEFAULT_THRESHOLD_PERCENT} when absent.'
        ),
    )
    cmp.set_defaults(func=cmd_compare_anchor)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    if not result.pop('_print_only', False):
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
