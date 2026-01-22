#!/usr/bin/env python3
"""
CLI script for unified logging operations.

Usage:
    Write (positional):
        python3 manage-log.py {type} {plan_id} {level} "{message}"

    Read:
        python3 manage-log.py read --plan-id {plan_id} --type {work|script|decision} [--limit N] [--phase PHASE]

    Read Findings:
        python3 manage-log.py read-findings {plan_id} [--stage STAGE] [--certainty CERTAINTY] [--status STATUS]

Arguments (write):
    type      - Log type: 'script', 'work', or 'decision'
    plan_id   - Plan identifier
    level     - Log level: INFO, WARN, ERROR
    message   - Log message

Arguments (read):
    --plan-id - Plan identifier (required)
    --type    - Log type: 'script', 'work', or 'decision' (required)
    --limit   - Max entries to return (optional, default: all)
    --phase   - Filter by phase (optional, work/decision logs only)

Arguments (read-findings):
    plan_id       - Plan identifier (positional, required)
    --stage       - Filter by stage: 'analysis' or 'q-gate' (optional)
    --certainty   - Filter by certainty: CERTAIN_INCLUDE, CERTAIN_EXCLUDE, UNCERTAIN (optional)
    --status      - Filter by Q-Gate status: CONFIRMED, FILTERED (optional)

Examples:
    # Write operations
    python3 manage-log.py script my-plan INFO "pm-workflow:manage-task:manage-task add (0.15s)"
    python3 manage-log.py work my-plan INFO "[ARTIFACT] Created deliverable: auth module"
    python3 manage-log.py decision my-plan INFO "(skill-name) Detected domain: java"

    # Read operations
    python3 manage-log.py read --plan-id my-plan --type work
    python3 manage-log.py read --plan-id my-plan --type decision
    python3 manage-log.py read --plan-id my-plan --type work --limit 5
    python3 manage-log.py read --plan-id my-plan --type decision --phase 1-init

    # Read findings (for uncertainty resolution flow)
    python3 manage-log.py read-findings my-plan --certainty UNCERTAIN
    python3 manage-log.py read-findings my-plan --stage analysis --certainty CERTAIN_INCLUDE
    python3 manage-log.py read-findings my-plan --stage q-gate --status CONFIRMED
"""

import sys

# Direct imports from same directory (local imports)
from plan_logging import get_log_path, list_recent_work, log_entry, read_decision_log, read_work_log

VALID_TYPES = ('script', 'work', 'decision')
VALID_LEVELS = ('INFO', 'WARN', 'ERROR')


def format_toon_output(result: dict) -> str:
    """Format result dict as TOON output."""
    lines = []

    # Status line first
    lines.append(f'status: {result.get("status", "success")}')

    # Plan ID
    if 'plan_id' in result:
        lines.append(f'plan_id: {result["plan_id"]}')

    # Error info
    if result.get('status') == 'error':
        if 'error' in result:
            lines.append(f'error: {result["error"]}')
        if 'message' in result:
            lines.append(f'message: {result["message"]}')
        return '\n'.join(lines)

    # Success fields
    if 'log_type' in result:
        lines.append(f'log_type: {result["log_type"]}')

    if 'total_entries' in result:
        lines.append(f'total_entries: {result["total_entries"]}')

    if 'showing' in result:
        lines.append(f'showing: {result["showing"]}')

    # Entries (structured work log)
    entries = result.get('entries', [])
    if entries:
        lines.append('')
        lines.append('entries:')
        for entry in entries:
            lines.append(f'  - timestamp: {entry.get("timestamp", "")}')
            lines.append(f'    level: {entry.get("level", "")}')
            if entry.get('hash_id'):
                lines.append(f'    hash_id: {entry.get("hash_id", "")}')
            lines.append(f'    message: {entry.get("message", "")}')
            if entry.get('phase'):
                lines.append(f'    phase: {entry.get("phase", "")}')
            if entry.get('detail'):
                lines.append(f'    detail: {entry.get("detail", "")}')

    # Raw content (script execution logs)
    raw_content = result.get('raw_content')
    if raw_content:
        lines.append('')
        lines.append('content:')
        for line in raw_content.split('\n'):
            if line.strip():
                lines.append(f'  {line}')

    return '\n'.join(lines)


def parse_read_args(args: list) -> dict:
    """Parse named arguments for read command."""
    result: dict[str, str | int | None] = {'plan_id': None, 'log_type': None, 'limit': None, 'phase': None}

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == '--plan-id' and i + 1 < len(args):
            result['plan_id'] = args[i + 1]
            i += 2
        elif arg.startswith('--plan-id='):
            result['plan_id'] = arg.split('=', 1)[1]
            i += 1
        elif arg == '--type' and i + 1 < len(args):
            result['log_type'] = args[i + 1]
            i += 2
        elif arg.startswith('--type='):
            result['log_type'] = arg.split('=', 1)[1]
            i += 1
        elif arg == '--limit' and i + 1 < len(args):
            result['limit'] = int(args[i + 1])
            i += 2
        elif arg.startswith('--limit='):
            result['limit'] = int(arg.split('=', 1)[1])
            i += 1
        elif arg == '--phase' and i + 1 < len(args):
            result['phase'] = args[i + 1]
            i += 2
        elif arg.startswith('--phase='):
            result['phase'] = arg.split('=', 1)[1]
            i += 1
        else:
            i += 1

    return result


def parse_findings_args(args: list) -> dict:
    """Parse named arguments for read-findings command."""
    result: dict[str, str | None] = {
        'plan_id': None,
        'stage': None,
        'certainty': None,
        'status': None,
    }

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == '--plan-id' and i + 1 < len(args):
            result['plan_id'] = args[i + 1]
            i += 2
        elif arg.startswith('--plan-id='):
            result['plan_id'] = arg.split('=', 1)[1]
            i += 1
        elif arg == '--stage' and i + 1 < len(args):
            result['stage'] = args[i + 1]
            i += 2
        elif arg.startswith('--stage='):
            result['stage'] = arg.split('=', 1)[1]
            i += 1
        elif arg == '--certainty' and i + 1 < len(args):
            result['certainty'] = args[i + 1]
            i += 2
        elif arg.startswith('--certainty='):
            result['certainty'] = arg.split('=', 1)[1]
            i += 1
        elif arg == '--status' and i + 1 < len(args):
            result['status'] = args[i + 1]
            i += 2
        elif arg.startswith('--status='):
            result['status'] = arg.split('=', 1)[1]
            i += 1
        else:
            i += 1

    return result


def handle_read_findings(args: list) -> None:
    """Handle read-findings subcommand.

    Reads findings from decision.log with filtering by stage, certainty, and status.
    Hash IDs are automatically present in every log entry (in the standard header position).
    Finding messages follow format: ({agent}) {file_path}: {CERTAINTY} ({CONFIDENCE}%)
    """
    import re

    parsed = parse_findings_args(args)

    if not parsed['plan_id']:
        print('status: error', file=sys.stderr)
        print('error: missing_argument', file=sys.stderr)
        print('message: --plan-id is required', file=sys.stderr)
        sys.exit(1)

    # Read decision log
    result = read_decision_log(parsed['plan_id'], phase=None)

    if result.get('status') == 'error':
        print(format_toon_output(result), file=sys.stderr)
        sys.exit(1)

    entries = result.get('entries', [])

    # Pattern for finding messages (hash_id comes from parsed entry, not message)
    # Message format: ({agent}) {file_path}: {CERTAINTY} ({CONFIDENCE}%)
    finding_pattern = re.compile(
        r'^\(([^)]+)\)\s*([^:]+):\s*(CERTAIN_INCLUDE|CERTAIN_EXCLUDE|UNCERTAIN)\s*\((\d+)%\)'
    )

    findings = []
    for entry in entries:
        message = entry.get('message', '')
        detail = entry.get('detail', '')
        hash_id = entry.get('hash_id', '')

        match = finding_pattern.match(message)
        if match:
            agent_name, file_path, certainty, confidence = match.groups()
            finding = {
                'hash_id': hash_id,
                'agent': agent_name,
                'file_path': file_path.strip(),
                'certainty': certainty,
                'confidence': int(confidence),
                'detail': detail,
            }
            findings.append(finding)

    # Apply filters
    filtered = findings

    if parsed['certainty']:
        filtered = [f for f in filtered if f['certainty'] == parsed['certainty']]

    if parsed['status']:
        # status maps: CONFIRMED/FILTERED for Q-Gate results
        # For analysis stage, we might filter by certainty directly
        pass  # Status filtering reserved for Q-Gate stage

    # Prepare output
    output = {
        'status': 'success',
        'plan_id': parsed['plan_id'],
        'total_findings': len(findings),
        'filtered_count': len(filtered),
        'filters_applied': {
            k: v for k, v in [
                ('stage', parsed['stage']),
                ('certainty', parsed['certainty']),
                ('status', parsed['status']),
            ] if v
        },
        'findings': filtered,
    }

    # Format output
    lines = [
        f'status: {output["status"]}',
        f'plan_id: {output["plan_id"]}',
        f'total_findings: {output["total_findings"]}',
        f'filtered_count: {output["filtered_count"]}',
    ]

    if output['filters_applied']:
        lines.append('filters_applied:')
        for k, v in output['filters_applied'].items():
            lines.append(f'  {k}: {v}')

    if filtered:
        lines.append('')
        lines.append(f'findings[{len(filtered)}]{{hash_id,file_path,certainty,confidence}}:')
        for f in filtered:
            lines.append(f'  {f["hash_id"]},{f["file_path"]},{f["certainty"]},{f["confidence"]}')

        # Also output file paths for easy consumption
        lines.append('')
        lines.append('file_paths:')
        for f in filtered:
            lines.append(f'  - {f["file_path"]}')

    print('\n'.join(lines))


def handle_read(args: list) -> None:
    """Handle read subcommand."""
    parsed = parse_read_args(args)

    # Validate required args
    if not parsed['plan_id']:
        print('status: error', file=sys.stderr)
        print('error: missing_argument', file=sys.stderr)
        print('message: --plan-id is required', file=sys.stderr)
        sys.exit(1)

    if not parsed['log_type']:
        print('status: error', file=sys.stderr)
        print('error: missing_argument', file=sys.stderr)
        print('message: --type is required (work or script)', file=sys.stderr)
        sys.exit(1)

    if parsed['log_type'] not in VALID_TYPES:
        print('status: error', file=sys.stderr)
        print('error: invalid_type', file=sys.stderr)
        print(f'message: type must be one of {VALID_TYPES}', file=sys.stderr)
        sys.exit(1)

    # Work and decision logs support full parsing
    if parsed['log_type'] == 'work':
        if parsed['limit']:
            result = list_recent_work(parsed['plan_id'], limit=parsed['limit'])
        else:
            result = read_work_log(parsed['plan_id'], phase=parsed['phase'])
        result['log_type'] = 'work'
    elif parsed['log_type'] == 'decision':
        result = read_decision_log(parsed['plan_id'], phase=parsed['phase'])
        if parsed['limit'] and result.get('entries'):
            result['entries'] = result['entries'][-parsed['limit'] :]
            result['showing'] = len(result['entries'])
        result['log_type'] = 'decision'
    else:
        # Script logs - read raw file content for now
        log_file = get_log_path(parsed['plan_id'], 'script')
        if log_file.exists():
            content = log_file.read_text(encoding='utf-8')
            lines = content.strip().split('\n') if content.strip() else []

            # Apply limit if specified
            if parsed['limit'] and lines:
                lines = lines[-parsed['limit'] :]

            result = {
                'status': 'success',
                'plan_id': parsed['plan_id'],
                'log_type': 'script',
                'total_entries': len(lines),
                'raw_content': '\n'.join(lines),
            }
        else:
            result = {
                'status': 'success',
                'plan_id': parsed['plan_id'],
                'log_type': 'script',
                'total_entries': 0,
                'raw_content': '',
            }

    # Output
    if result.get('status') == 'error':
        print(format_toon_output(result), file=sys.stderr)
        sys.exit(1)
    else:
        print(format_toon_output(result))


def handle_write(args: list) -> None:
    """Handle write operation (positional args)."""
    if len(args) != 4:
        print(f'Usage: {sys.argv[0]} {{type}} {{plan_id}} {{level}} "{{message}}"', file=sys.stderr)
        sys.exit(1)

    log_type, plan_id, level, message = args

    # Validate type
    if log_type not in VALID_TYPES:
        print(f'Error: type must be one of {VALID_TYPES}', file=sys.stderr)
        sys.exit(1)

    # Validate level
    if level not in VALID_LEVELS:
        print(f'Error: level must be one of {VALID_LEVELS}', file=sys.stderr)
        sys.exit(1)

    # Log entry
    try:
        log_entry(log_type, plan_id, level, message)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} read --plan-id {{id}} --type {{work|script|decision}}', file=sys.stderr)
        print(f'       {sys.argv[0]} read-findings {{plan_id}} [--stage {{analysis|q-gate}}] [--certainty {{CERTAIN_INCLUDE|CERTAIN_EXCLUDE|UNCERTAIN}}]', file=sys.stderr)
        print(f'       {sys.argv[0]} {{type}} {{plan_id}} {{level}} "{{message}}"', file=sys.stderr)
        sys.exit(1)

    # Check if first arg is a subcommand
    if sys.argv[1] == 'read':
        handle_read(sys.argv[2:])
    elif sys.argv[1] == 'read-findings':
        handle_read_findings(sys.argv[2:])
    else:
        # Legacy positional write
        handle_write(sys.argv[1:])


if __name__ == '__main__':
    main()
