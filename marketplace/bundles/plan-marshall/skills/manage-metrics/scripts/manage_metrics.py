#!/usr/bin/env python3
"""
CLI script for plan metrics collection and reporting.

Usage:
    Start phase timing:
        python3 manage_metrics.py start-phase --plan-id <id> --phase <phase>

    End phase timing:
        python3 manage_metrics.py end-phase --plan-id <id> --phase <phase> [--total-tokens N] [--input-tokens N] [--output-tokens N] [--duration-ms N] [--tool-uses N]

    Generate metrics.md:
        python3 manage_metrics.py generate --plan-id <id>

    Atomic phase boundary (end-phase + start-phase + generate):
        python3 manage_metrics.py phase-boundary --plan-id <id> \
            --prev-phase <prev> --next-phase <next> \
            [--total-tokens N] [--duration-ms N] [--tool-uses N]

    Accumulate per-phase subagent usage on disk:
        python3 manage_metrics.py accumulate-agent-usage --plan-id <id> --phase <phase> \
            [--total-tokens N] [--tool-uses N] [--duration-ms N]

    Enrich from JSONL transcript (main-context tokens + per-phase subagent <usage>):
        python3 manage_metrics.py enrich --plan-id <id> --session-id <sid>
"""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from constants import FILE_WORK_METRICS, PHASES  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    format_duration,
    get_plan_dir,
    now_utc_iso,
    output_toon,
    safe_main,
)
from input_validation import add_plan_id_arg, require_valid_plan_id  # type: ignore[import-not-found]

METRICS_FILE = FILE_WORK_METRICS
METRICS_MD = 'metrics.md'
PHASE_NAMES = list(PHASES)
ACCUMULATOR_FILE_TEMPLATE = 'work/metrics-accumulator-{phase}.toon'
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

    if args.input_tokens is not None:
        phase_data['input_tokens'] = args.input_tokens

    if args.output_tokens is not None:
        phase_data['output_tokens'] = args.output_tokens

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
    lines.append('| Phase | Duration | Tokens | Input | Output | Tool Uses |')
    lines.append('|-------|----------|--------|-------|--------|-----------|')

    total_duration = 0.0
    total_tokens = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_tool_uses = 0

    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]

        duration = _coerce_numeric(phase.get('duration_seconds', 0))
        if not isinstance(duration, (int, float)):
            duration = 0.0
        total_duration += duration

        tokens = _coerce_numeric(phase.get('total_tokens', 0))
        if not isinstance(tokens, (int, float)):
            tokens = 0
        total_tokens += int(tokens)

        input_tokens = _coerce_numeric(phase.get('input_tokens', 0))
        if not isinstance(input_tokens, (int, float)):
            input_tokens = 0
        total_input_tokens += int(input_tokens)

        output_tokens = _coerce_numeric(phase.get('output_tokens', 0))
        if not isinstance(output_tokens, (int, float)):
            output_tokens = 0
        total_output_tokens += int(output_tokens)

        tool_uses = _coerce_numeric(phase.get('tool_uses', 0))
        if not isinstance(tool_uses, (int, float)):
            tool_uses = 0
        total_tool_uses += int(tool_uses)

        duration_str = format_duration(duration) if duration else '-'
        tokens_str = f'{tokens:,}' if tokens else '-'
        input_str = f'{input_tokens:,}' if input_tokens else '-'
        output_str = f'{output_tokens:,}' if output_tokens else '-'
        tool_uses_str = str(tool_uses) if tool_uses else '-'

        lines.append(f'| {phase_name} | {duration_str} | {tokens_str} | {input_str} | {output_str} | {tool_uses_str} |')

    # Totals row
    lines.append(
        f'| **Total** | **{format_duration(total_duration)}** | **{total_tokens:,}** | **{total_input_tokens:,}** | **{total_output_tokens:,}** | **{total_tool_uses}** |'
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

        input_tok = phase.get('input_tokens')
        if input_tok:
            lines.append(f'- **Input tokens**: {int(input_tok):,}')

        output_tok = phase.get('output_tokens')
        if output_tok:
            lines.append(f'- **Output tokens**: {int(output_tok):,}')

        tool_uses = phase.get('tool_uses')
        if tool_uses:
            lines.append(f'- **Tool uses**: {int(tool_uses)}')

        lines.append('')

    md_content = '\n'.join(lines)
    md_path = get_plan_dir(plan_id) / METRICS_MD
    atomic_write_file(md_path, md_content)

    result = {
        'status': 'success',
        'plan_id': plan_id,
        'file': METRICS_MD,
        'phases_recorded': len(phases),
        'total_duration_seconds': round(total_duration, 1),
        'total_tokens': total_tokens,
    }
    if total_input_tokens:
        result['total_input_tokens'] = total_input_tokens
    if total_output_tokens:
        result['total_output_tokens'] = total_output_tokens
    return result


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

    fields = {
        match.group(1): int(match.group(2))
        for match in USAGE_FIELD_RE.finditer(body)
    }
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

    # Parse JSONL for token usage and subagent <usage> attribution
    total_input = 0
    total_output = 0
    message_count = 0
    windows = _phase_window_lookup(plan_id)
    per_phase_subagent: dict[str, dict[str, int]] = {}
    subagent_calls_attributed = 0

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
                    total_input += usage.get('input_tokens', 0) or 0
                    total_output += usage.get('output_tokens', 0) or 0
                    if usage.get('input_tokens') or usage.get('output_tokens'):
                        message_count += 1

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
                        if _attribute_subagent_usage(
                            timestamp, windows, tag_match.group(1), per_phase_subagent
                        ):
                            subagent_calls_attributed += 1
    except OSError:
        return {
            'status': 'error',
            'error': 'read_failed',
            'message': f'Cannot read transcript: {transcript_path}',
        }

    # Update metrics with enriched data (main-context + per-phase subagent totals)
    data = read_metrics_raw(plan_id)
    data['session_input_tokens'] = total_input
    data['session_output_tokens'] = total_output
    data['session_total_tokens'] = total_input + total_output
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
        'input_tokens': total_input,
        'output_tokens': total_output,
        'total_tokens': total_input + total_output,
        'message_count': message_count,
        'subagent_phases_attributed': len(per_phase_subagent),
        'subagent_calls_attributed': subagent_calls_attributed,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Plan metrics collection and reporting', allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # start-phase
    sp = subparsers.add_parser('start-phase', help='Record phase start timestamp', allow_abbrev=False)
    add_plan_id_arg(sp)
    sp.add_argument('--phase', required=True, help='Phase name (e.g., 1-init)')
    sp.set_defaults(func=cmd_start_phase)

    # end-phase
    ep = subparsers.add_parser(
        'end-phase', help='Record phase end timestamp and optional token data', allow_abbrev=False
    )
    add_plan_id_arg(ep)
    ep.add_argument('--phase', required=True, help='Phase name')
    ep.add_argument('--total-tokens', type=int, default=None, help='Total tokens from Task agent <usage>')
    ep.add_argument('--input-tokens', type=int, default=None, help='Input tokens from Task agent <usage>')
    ep.add_argument('--output-tokens', type=int, default=None, help='Output tokens from Task agent <usage>')
    ep.add_argument('--duration-ms', type=int, default=None, help='Duration in ms from Task agent <usage>')
    ep.add_argument('--tool-uses', type=int, default=None, help='Tool use count from Task agent <usage>')
    ep.set_defaults(func=cmd_end_phase)

    # generate
    gp = subparsers.add_parser(
        'generate', help='Generate metrics.md from collected data', allow_abbrev=False
    )
    add_plan_id_arg(gp)
    gp.set_defaults(func=cmd_generate)

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
    pb.add_argument(
        '--total-tokens', type=int, default=None, help='Total tokens forwarded to end-phase (optional)'
    )
    pb.add_argument(
        '--duration-ms', type=int, default=None, help='Agent duration (ms) forwarded to end-phase (optional)'
    )
    pb.add_argument(
        '--tool-uses', type=int, default=None, help='Tool use count forwarded to end-phase (optional)'
    )
    pb.set_defaults(func=cmd_phase_boundary)

    # accumulate-agent-usage
    acc = subparsers.add_parser(
        'accumulate-agent-usage',
        help='Persist running per-phase totals of subagent <usage> data',
        description=(
            'Add the supplied --total-tokens / --tool-uses / --duration-ms '
            "values to the per-phase accumulator file at "
            'work/metrics-accumulator-{phase}.toon, incrementing the samples '
            'counter. Initialises the file when absent and is idempotent across '
            'successive calls. cmd_end_phase / cmd_phase_boundary read this '
            'file as a fallback when their corresponding flags are omitted.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(acc)
    acc.add_argument('--phase', required=True, help='Phase name being accumulated (e.g. 5-execute)')
    acc.add_argument(
        '--total-tokens', type=int, default=None, help='Subagent total_tokens to add to the running total'
    )
    acc.add_argument(
        '--tool-uses', type=int, default=None, help='Subagent tool_uses to add to the running total'
    )
    acc.add_argument(
        '--duration-ms', type=int, default=None, help='Subagent duration_ms to add to the running total'
    )
    acc.set_defaults(func=cmd_accumulate_agent_usage)

    # enrich
    enr = subparsers.add_parser(
        'enrich', help='Enrich metrics from JSONL transcript', allow_abbrev=False
    )
    add_plan_id_arg(enr)
    enr.add_argument('--session-id', required=True, help='Session ID for transcript lookup')
    enr.set_defaults(func=cmd_enrich)

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
