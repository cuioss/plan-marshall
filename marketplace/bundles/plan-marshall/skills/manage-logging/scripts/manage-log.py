#!/usr/bin/env python3
"""
CLI script for unified logging operations.

Usage:
    Write:
        python3 manage-log.py work --plan-id <plan_id> --level INFO --message "msg"
        python3 manage-log.py decision --plan-id <plan_id> --level INFO --message "msg"
        python3 manage-log.py script --plan-id <plan_id> --level INFO --message "msg"

    Separator:
        python3 manage-log.py separator --plan-id <plan_id> [--type work]

    Read:
        python3 manage-log.py read --plan-id <plan_id> --type work [--limit N] [--phase PHASE]
        python3 manage-log.py read --plan-id <plan_id> --type decision [--limit N] [--phase PHASE]
        python3 manage-log.py read --plan-id <plan_id> --type script [--limit N]

Arguments (write):
    --plan-id  - Plan identifier (required)
    --level    - Log level: INFO, WARN, ERROR (required)
    --message  - Log message (required)

Arguments (read):
    --plan-id  - Plan identifier (required)
    --type     - Log type: 'script', 'work', or 'decision' (required)
    --limit    - Max entries to return (optional, default: all)
    --phase    - Filter by phase (optional, work/decision logs only)

Examples:
    # Write operations
    python3 manage-log.py script --plan-id my-plan --level INFO --message "pm-workflow:manage-task:manage-task add (0.15s)"
    python3 manage-log.py work --plan-id my-plan --level INFO --message "[ARTIFACT] Created deliverable: auth module"
    python3 manage-log.py decision --plan-id my-plan --level INFO --message "(skill-name) Detected domain: java"

    # Read operations
    python3 manage-log.py read --plan-id my-plan --type work
    python3 manage-log.py read --plan-id my-plan --type decision
    python3 manage-log.py read --plan-id my-plan --type work --limit 5
    python3 manage-log.py read --plan-id my-plan --type decision --phase 1-init
"""

import argparse
import sys

# Direct imports from same directory (local imports)
from plan_logging import get_log_path, list_recent_work, log_entry, log_separator, read_decision_log, read_work_log

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


def handle_read(args: argparse.Namespace) -> None:
    """Handle read subcommand."""
    plan_id = args.plan_id
    log_type = args.type
    limit = args.limit
    phase = args.phase

    # Work and decision logs support full parsing
    if log_type == 'work':
        if limit:
            result = list_recent_work(plan_id, limit=limit)
        else:
            result = read_work_log(plan_id, phase=phase)
        result['log_type'] = 'work'
    elif log_type == 'decision':
        result = read_decision_log(plan_id, phase=phase)
        if limit and result.get('entries'):
            result['entries'] = result['entries'][-limit:]
            result['showing'] = len(result['entries'])
        result['log_type'] = 'decision'
    else:
        # Script logs - read raw file content
        log_file = get_log_path(plan_id, 'script')
        if log_file.exists():
            content = log_file.read_text(encoding='utf-8')
            file_lines = content.strip().split('\n') if content.strip() else []

            # Apply limit if specified
            if limit and file_lines:
                file_lines = file_lines[-limit:]

            result = {
                'status': 'success',
                'plan_id': plan_id,
                'log_type': 'script',
                'total_entries': len(file_lines),
                'raw_content': '\n'.join(file_lines),
            }
        else:
            result = {
                'status': 'success',
                'plan_id': plan_id,
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


def handle_separator(args: argparse.Namespace) -> None:
    """Handle separator subcommand."""
    log_separator(args.type, args.plan_id)


def handle_write(args: argparse.Namespace) -> None:
    """Handle write subcommand."""
    log_type = args.log_type
    plan_id = args.plan_id
    level = args.level
    message = args.message

    # Log entry
    try:
        log_entry(log_type, plan_id, level, message)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


def _add_write_args(parser: argparse.ArgumentParser) -> None:
    """Add common write arguments to a subparser."""
    parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    parser.add_argument('--level', required=True, choices=VALID_LEVELS, help='Log level')
    parser.add_argument('--message', required=True, help='Log message')


def main():
    parser = argparse.ArgumentParser(
        description='Unified logging operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Write subcommands: work, decision, script
    for log_type in VALID_TYPES:
        if log_type == 'read':
            continue
        write_parser = subparsers.add_parser(log_type, help=f'Write a {log_type} log entry')
        _add_write_args(write_parser)
        write_parser.set_defaults(log_type=log_type)

    # Separator subcommand
    sep_parser = subparsers.add_parser('separator', help='Add visual separator (blank line) to log')
    sep_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    sep_parser.add_argument('--type', default='work', choices=VALID_TYPES, help='Log type (default: work)')

    # Read subcommand
    read_parser = subparsers.add_parser('read', help='Read log entries')
    read_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    read_parser.add_argument('--type', required=True, choices=VALID_TYPES, help='Log type')
    read_parser.add_argument('--limit', type=int, help='Max entries to return')
    read_parser.add_argument('--phase', help='Filter by phase (work/decision logs only)')

    args = parser.parse_args()

    if args.command == 'read':
        handle_read(args)
    elif args.command == 'separator':
        handle_separator(args)
    else:
        handle_write(args)


if __name__ == '__main__':
    main()
