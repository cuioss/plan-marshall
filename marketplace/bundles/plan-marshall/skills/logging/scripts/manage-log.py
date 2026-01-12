#!/usr/bin/env python3
"""
CLI script for unified logging operations.

Usage:
    Write (positional):
        python3 manage-log.py {type} {plan_id} {level} "{message}"

    Read:
        python3 manage-log.py read --plan-id {plan_id} --type {work|script} [--limit N] [--phase PHASE]

Arguments (write):
    type      - Log type: 'script' or 'work'
    plan_id   - Plan identifier
    level     - Log level: INFO, WARN, ERROR
    message   - Log message

Arguments (read):
    --plan-id - Plan identifier (required)
    --type    - Log type: 'script' or 'work' (required)
    --limit   - Max entries to return (optional, default: all)
    --phase   - Filter by phase (optional, work logs only)

Examples:
    # Write operations
    python3 manage-log.py script my-plan INFO "pm-workflow:manage-task:manage-task add (0.15s)"
    python3 manage-log.py work my-plan INFO "Created deliverable: auth module"

    # Read operations
    python3 manage-log.py read --plan-id my-plan --type work
    python3 manage-log.py read --plan-id my-plan --type work --limit 5
    python3 manage-log.py read --plan-id my-plan --type work --phase init
"""

import sys
from pathlib import Path

# Direct imports from same directory (local imports)
from plan_logging import log_entry, read_work_log, list_recent_work, get_log_path

VALID_TYPES = ('script', 'work')
VALID_LEVELS = ('INFO', 'WARN', 'ERROR')


def format_toon_output(result: dict) -> str:
    """Format result dict as TOON output."""
    lines = []

    # Status line first
    lines.append(f"status: {result.get('status', 'success')}")

    # Plan ID
    if 'plan_id' in result:
        lines.append(f"plan_id: {result['plan_id']}")

    # Error info
    if result.get('status') == 'error':
        if 'error' in result:
            lines.append(f"error: {result['error']}")
        if 'message' in result:
            lines.append(f"message: {result['message']}")
        return '\n'.join(lines)

    # Success fields
    if 'log_type' in result:
        lines.append(f"log_type: {result['log_type']}")

    if 'total_entries' in result:
        lines.append(f"total_entries: {result['total_entries']}")

    if 'showing' in result:
        lines.append(f"showing: {result['showing']}")

    # Entries (structured work log)
    entries = result.get('entries', [])
    if entries:
        lines.append("")
        lines.append("entries:")
        for entry in entries:
            lines.append(f"  - timestamp: {entry.get('timestamp', '')}")
            lines.append(f"    level: {entry.get('level', '')}")
            if entry.get('category'):
                lines.append(f"    category: {entry.get('category', '')}")
            lines.append(f"    message: {entry.get('message', '')}")
            if entry.get('phase'):
                lines.append(f"    phase: {entry.get('phase', '')}")
            if entry.get('detail'):
                lines.append(f"    detail: {entry.get('detail', '')}")

    # Raw content (script execution logs)
    raw_content = result.get('raw_content')
    if raw_content:
        lines.append("")
        lines.append("content:")
        for line in raw_content.split('\n'):
            if line.strip():
                lines.append(f"  {line}")

    return '\n'.join(lines)


def parse_read_args(args: list) -> dict:
    """Parse named arguments for read command."""
    result = {
        'plan_id': None,
        'log_type': None,
        'limit': None,
        'phase': None
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


def handle_read(args: list) -> None:
    """Handle read subcommand."""
    parsed = parse_read_args(args)

    # Validate required args
    if not parsed['plan_id']:
        print("status: error", file=sys.stderr)
        print("error: missing_argument", file=sys.stderr)
        print("message: --plan-id is required", file=sys.stderr)
        sys.exit(1)

    if not parsed['log_type']:
        print("status: error", file=sys.stderr)
        print("error: missing_argument", file=sys.stderr)
        print("message: --type is required (work or script)", file=sys.stderr)
        sys.exit(1)

    if parsed['log_type'] not in VALID_TYPES:
        print("status: error", file=sys.stderr)
        print(f"error: invalid_type", file=sys.stderr)
        print(f"message: type must be one of {VALID_TYPES}", file=sys.stderr)
        sys.exit(1)

    # Currently only work logs support full parsing
    if parsed['log_type'] == 'work':
        if parsed['limit']:
            result = list_recent_work(parsed['plan_id'], limit=parsed['limit'])
        else:
            result = read_work_log(parsed['plan_id'], phase=parsed['phase'])

        result['log_type'] = 'work'
    else:
        # Script logs - read raw file content for now
        log_file = get_log_path(parsed['plan_id'], 'script')
        if log_file.exists():
            content = log_file.read_text(encoding='utf-8')
            lines = content.strip().split('\n') if content.strip() else []

            # Apply limit if specified
            if parsed['limit'] and lines:
                lines = lines[-parsed['limit']:]

            result = {
                'status': 'success',
                'plan_id': parsed['plan_id'],
                'log_type': 'script',
                'total_entries': len(lines),
                'raw_content': '\n'.join(lines)
            }
        else:
            result = {
                'status': 'success',
                'plan_id': parsed['plan_id'],
                'log_type': 'script',
                'total_entries': 0,
                'raw_content': ''
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
        print(f"Usage: {sys.argv[0]} {{type}} {{plan_id}} {{level}} \"{{message}}\"", file=sys.stderr)
        sys.exit(1)

    log_type, plan_id, level, message = args

    # Validate type
    if log_type not in VALID_TYPES:
        print(f"Error: type must be one of {VALID_TYPES}", file=sys.stderr)
        sys.exit(1)

    # Validate level
    if level not in VALID_LEVELS:
        print(f"Error: level must be one of {VALID_LEVELS}", file=sys.stderr)
        sys.exit(1)

    # Log entry
    try:
        log_entry(log_type, plan_id, level, message)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} read --plan-id {{id}} --type {{work|script}}", file=sys.stderr)
        print(f"       {sys.argv[0]} {{type}} {{plan_id}} {{level}} \"{{message}}\"", file=sys.stderr)
        sys.exit(1)

    # Check if first arg is 'read' subcommand
    if sys.argv[1] == 'read':
        handle_read(sys.argv[2:])
    else:
        # Legacy positional write
        handle_write(sys.argv[1:])


if __name__ == '__main__':
    main()
