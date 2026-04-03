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
    python3 manage-log.py script --plan-id my-plan --level INFO --message "plan-marshall:manage-tasks:manage-tasks add (0.15s)"
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
from constants import VALID_LOG_LEVELS, VALID_LOG_TYPES  # type: ignore[import-not-found]
from input_validation import add_plan_id_arg  # type: ignore[import-not-found]
from plan_logging import get_log_path, list_recent_work, log_entry, log_separator, read_decision_log, read_work_log
from file_ops import output_toon, safe_main

VALID_TYPES = VALID_LOG_TYPES
VALID_LEVELS = VALID_LOG_LEVELS


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
        output_toon(result)
        sys.exit(1)
    else:
        output_toon(result)


def handle_separator(args: argparse.Namespace) -> None:
    """Handle separator subcommand."""
    log_separator(args.type, args.plan_id)


def handle_write(args: argparse.Namespace) -> int | None:
    """Handle write subcommand."""
    log_type = args.log_type
    plan_id = args.plan_id
    level = args.level
    message = args.message

    # Log entry
    try:
        log_entry(log_type, plan_id, level, message)
    except Exception as e:
        output_toon({'status': 'error', 'error': 'write_failed', 'message': str(e)})
        return 1


def _add_write_args(parser: argparse.ArgumentParser) -> None:
    """Add common write arguments to a subparser."""
    add_plan_id_arg(parser)
    parser.add_argument('--level', required=True, choices=VALID_LEVELS, help='Log level')
    parser.add_argument('--message', required=True, help='Log message')


@safe_main
def main() -> int:
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
    add_plan_id_arg(sep_parser)
    sep_parser.add_argument('--type', default='work', choices=VALID_TYPES, help='Log type (default: work)')

    # Read subcommand
    read_parser = subparsers.add_parser('read', help='Read log entries')
    add_plan_id_arg(read_parser)
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
    return 0


if __name__ == '__main__':
    main()
