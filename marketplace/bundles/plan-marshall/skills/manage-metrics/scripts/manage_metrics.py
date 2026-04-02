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
import sys
from datetime import UTC, datetime
from pathlib import Path

from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]
from input_validation import is_valid_plan_id  # type: ignore[import-not-found]
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

METRICS_FILE = 'work/metrics.toon'
METRICS_MD = 'metrics.md'
PHASE_NAMES = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']


def get_plan_dir(plan_id: str) -> Path:
    return base_path('plans', plan_id)


def read_metrics(plan_id: str) -> dict:
    metrics_path = get_plan_dir(plan_id) / METRICS_FILE
    if not metrics_path.exists():
        return {'phases': {}}
    content = metrics_path.read_text(encoding='utf-8')
    return parse_toon(content) if content.strip() else {'phases': {}}


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


def cmd_start_phase(args: argparse.Namespace) -> None:
    plan_id = args.plan_id
    phase = args.phase

    if not is_valid_plan_id(plan_id):
        print(serialize_toon({'status': 'error', 'message': f'Invalid plan_id: {plan_id}'}))
        return

    if phase not in PHASE_NAMES:
        print(serialize_toon({'status': 'error', 'message': f'Invalid phase: {phase}. Must be one of: {", ".join(PHASE_NAMES)}'}))
        return

    data = read_metrics_raw(plan_id)
    now = datetime.now(UTC).isoformat()

    if phase not in data['phases']:
        data['phases'][phase] = {}

    data['phases'][phase]['start_time'] = now
    data['updated'] = now

    write_metrics(plan_id, data)

    print(serialize_toon({
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'start_time': now,
    }))


def cmd_end_phase(args: argparse.Namespace) -> None:
    plan_id = args.plan_id
    phase = args.phase

    if not is_valid_plan_id(plan_id):
        print(serialize_toon({'status': 'error', 'message': f'Invalid plan_id: {plan_id}'}))
        return

    if phase not in PHASE_NAMES:
        print(serialize_toon({'status': 'error', 'message': f'Invalid phase: {phase}'}))
        return

    data = read_metrics_raw(plan_id)
    now = datetime.now(UTC).isoformat()

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

    print(serialize_toon(result))


def cmd_generate(args: argparse.Namespace) -> None:
    plan_id = args.plan_id

    if not is_valid_plan_id(plan_id):
        print(serialize_toon({'status': 'error', 'message': f'Invalid plan_id: {plan_id}'}))
        return

    data = read_metrics_raw(plan_id)
    phases = data.get('phases', {})

    if not phases:
        print(serialize_toon({'status': 'error', 'message': 'No metrics data found'}))
        return

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

        duration = phase.get('duration_seconds', 0)
        if isinstance(duration, str):
            try:
                duration = float(duration)
            except (ValueError, TypeError):
                duration = 0.0
        total_duration += duration

        tokens = phase.get('total_tokens', 0)
        if isinstance(tokens, str):
            try:
                tokens = int(tokens)
            except (ValueError, TypeError):
                tokens = 0
        total_tokens += tokens

        tool_uses = phase.get('tool_uses', 0)
        if isinstance(tool_uses, str):
            try:
                tool_uses = int(tool_uses)
            except (ValueError, TypeError):
                tool_uses = 0
        total_tool_uses += tool_uses

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

    print(serialize_toon({
        'status': 'success',
        'plan_id': plan_id,
        'file': METRICS_MD,
        'phases_recorded': len(phases),
        'total_duration_seconds': round(total_duration, 1),
        'total_tokens': total_tokens,
    }))


def cmd_enrich(args: argparse.Namespace) -> None:
    plan_id = args.plan_id
    session_id = args.session_id

    if not is_valid_plan_id(plan_id):
        print(serialize_toon({'status': 'error', 'message': f'Invalid plan_id: {plan_id}'}))
        return

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
        print(serialize_toon({
            'status': 'success',
            'plan_id': plan_id,
            'enriched': False,
            'message': f'JSONL transcript not found for session {session_id}',
        }))
        return

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
        print(serialize_toon({
            'status': 'error',
            'message': f'Cannot read transcript: {transcript_path}',
        }))
        return

    # Update metrics with enriched data
    data = read_metrics_raw(plan_id)
    data['session_input_tokens'] = total_input
    data['session_output_tokens'] = total_output
    data['session_total_tokens'] = total_input + total_output
    data['session_message_count'] = message_count
    data['updated'] = datetime.now(UTC).isoformat()

    write_metrics(plan_id, data)

    print(serialize_toon({
        'status': 'success',
        'plan_id': plan_id,
        'enriched': True,
        'input_tokens': total_input,
        'output_tokens': total_output,
        'total_tokens': total_input + total_output,
        'message_count': message_count,
    }))


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


def main() -> None:
    parser = argparse.ArgumentParser(description='Plan metrics collection and reporting')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # start-phase
    sp = subparsers.add_parser('start-phase', help='Record phase start timestamp')
    sp.add_argument('--plan-id', required=True, help='Plan identifier')
    sp.add_argument('--phase', required=True, help='Phase name (e.g., 1-init)')
    sp.set_defaults(func=cmd_start_phase)

    # end-phase
    ep = subparsers.add_parser('end-phase', help='Record phase end timestamp and optional token data')
    ep.add_argument('--plan-id', required=True, help='Plan identifier')
    ep.add_argument('--phase', required=True, help='Phase name')
    ep.add_argument('--total-tokens', type=int, default=None, help='Total tokens from Task agent <usage>')
    ep.add_argument('--duration-ms', type=int, default=None, help='Duration in ms from Task agent <usage>')
    ep.add_argument('--tool-uses', type=int, default=None, help='Tool use count from Task agent <usage>')
    ep.set_defaults(func=cmd_end_phase)

    # generate
    gp = subparsers.add_parser('generate', help='Generate metrics.md from collected data')
    gp.add_argument('--plan-id', required=True, help='Plan identifier')
    gp.set_defaults(func=cmd_generate)

    # enrich
    enr = subparsers.add_parser('enrich', help='Enrich metrics from JSONL transcript')
    enr.add_argument('--plan-id', required=True, help='Plan identifier')
    enr.add_argument('--session-id', required=True, help='Session ID for transcript lookup')
    enr.set_defaults(func=cmd_enrich)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(serialize_toon({'status': 'error', 'error': 'unexpected', 'message': str(e)}), file=sys.stderr)
        sys.exit(1)
