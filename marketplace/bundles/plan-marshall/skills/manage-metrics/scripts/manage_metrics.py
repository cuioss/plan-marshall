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

    Enrich from JSONL transcript:
        python3 manage_metrics.py enrich --plan-id <id> --session-id <sid>
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from constants import PHASES  # type: ignore[import-not-found]
from file_ops import atomic_write_file, get_plan_dir, now_utc_iso, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import add_plan_id_arg, require_valid_plan_id  # type: ignore[import-not-found]

METRICS_FILE = 'work/metrics.toon'
METRICS_MD = 'metrics.md'
PHASE_NAMES = list(PHASES)


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


def cmd_start_phase(args: argparse.Namespace) -> int:
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        output_toon({'status': 'error', 'error': 'invalid_phase', 'message': f'Invalid phase: {phase}. Must be one of: {", ".join(PHASE_NAMES)}'})
        return 1

    data = read_metrics_raw(plan_id)
    now = now_utc_iso()

    if phase not in data['phases']:
        data['phases'][phase] = {}

    data['phases'][phase]['start_time'] = now
    data['updated'] = now

    write_metrics(plan_id, data)

    output_toon({
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'start_time': now,
    })
    return 0


def cmd_end_phase(args: argparse.Namespace) -> int:
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        output_toon({'status': 'error', 'error': 'invalid_phase', 'message': f'Invalid phase: {phase}'})
        return 1

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

    # Override with Task agent duration if provided
    if args.duration_ms is not None:
        phase_data['agent_duration_ms'] = args.duration_ms
        phase_data['agent_duration_seconds'] = round(args.duration_ms / 1000.0, 1)

    # Token data from Task agent <usage> tags
    if args.total_tokens is not None:
        phase_data['total_tokens'] = args.total_tokens

    if args.tool_uses is not None:
        phase_data['tool_uses'] = args.tool_uses

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
    if args.total_tokens is not None:
        result['total_tokens'] = args.total_tokens

    output_toon(result)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    plan_id = require_valid_plan_id(args)

    data = read_metrics_raw(plan_id)
    phases = data.get('phases', {})

    if not phases:
        output_toon({'status': 'error', 'error': 'no_data', 'message': 'No metrics data found'})
        return 1

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

    total_duration = 0.0
    total_tokens = 0
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

        tool_uses = _coerce_numeric(phase.get('tool_uses', 0))
        if not isinstance(tool_uses, (int, float)):
            tool_uses = 0
        total_tool_uses += int(tool_uses)

        duration_str = format_duration(duration) if duration else '-'
        tokens_str = f'{tokens:,}' if tokens else '-'
        tool_uses_str = str(tool_uses) if tool_uses else '-'

        lines.append(f'| {phase_name} | {duration_str} | {tokens_str} | {tool_uses_str} |')

    # Totals row
    lines.append(f'| **Total** | **{format_duration(total_duration)}** | **{total_tokens:,}** | **{total_tool_uses}** |')
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

    output_toon({
        'status': 'success',
        'plan_id': plan_id,
        'file': METRICS_MD,
        'phases_recorded': len(phases),
        'total_duration_seconds': round(total_duration, 1),
        'total_tokens': total_tokens,
    })
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
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
        output_toon({
            'status': 'success',
            'plan_id': plan_id,
            'enriched': False,
            'message': f'JSONL transcript not found for session {session_id}',
        })
        return 0

    # Parse JSONL for token usage
    total_input = 0
    total_output = 0
    message_count = 0

    try:
        with open(transcript_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    msg = entry.get('message', {})
                    usage = msg.get('usage', {})
                    if usage:
                        total_input += usage.get('input_tokens', 0)
                        total_output += usage.get('output_tokens', 0)
                        if usage.get('input_tokens') or usage.get('output_tokens'):
                            message_count += 1
                except (json.JSONDecodeError, AttributeError):
                    continue
    except OSError:
        output_toon({
            'status': 'error',
            'error': 'read_failed',
            'message': f'Cannot read transcript: {transcript_path}',
        })
        return 1

    # Update metrics with enriched data
    data = read_metrics_raw(plan_id)
    data['session_input_tokens'] = total_input
    data['session_output_tokens'] = total_output
    data['session_total_tokens'] = total_input + total_output
    data['session_message_count'] = message_count
    data['updated'] = now_utc_iso()

    write_metrics(plan_id, data)

    output_toon({
        'status': 'success',
        'plan_id': plan_id,
        'enriched': True,
        'input_tokens': total_input,
        'output_tokens': total_output,
        'total_tokens': total_input + total_output,
        'message_count': message_count,
    })
    return 0


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f'{seconds:.1f}s'
    minutes = int(seconds // 60)
    remaining = seconds % 60
    if minutes < 60:
        return f'{minutes}m {remaining:.0f}s'
    hours = int(minutes // 60)
    remaining_min = minutes % 60
    return f'{hours}h {remaining_min}m'


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Plan metrics collection and reporting')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # start-phase
    sp = subparsers.add_parser('start-phase', help='Record phase start timestamp')
    add_plan_id_arg(sp)
    sp.add_argument('--phase', required=True, help='Phase name (e.g., 1-init)')
    sp.set_defaults(func=cmd_start_phase)

    # end-phase
    ep = subparsers.add_parser('end-phase', help='Record phase end timestamp and optional token data')
    add_plan_id_arg(ep)
    ep.add_argument('--phase', required=True, help='Phase name')
    ep.add_argument('--total-tokens', type=int, default=None, help='Total tokens from Task agent <usage>')
    ep.add_argument('--duration-ms', type=int, default=None, help='Duration in ms from Task agent <usage>')
    ep.add_argument('--tool-uses', type=int, default=None, help='Tool use count from Task agent <usage>')
    ep.set_defaults(func=cmd_end_phase)

    # generate
    gp = subparsers.add_parser('generate', help='Generate metrics.md from collected data')
    add_plan_id_arg(gp)
    gp.set_defaults(func=cmd_generate)

    # enrich
    enr = subparsers.add_parser('enrich', help='Enrich metrics from JSONL transcript')
    add_plan_id_arg(enr)
    enr.add_argument('--session-id', required=True, help='Session ID for transcript lookup')
    enr.set_defaults(func=cmd_enrich)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    main()
