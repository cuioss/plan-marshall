#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    --plan-id  - Plan identifier (OPTIONAL). When omitted, the entry is written
                 to the dated global log under .plan/logs/ (the first-class
                 global/no-plan path used by plan-less callers such as
                 marshall-steward). When supplied and resolving to an
                 initialized plan, the entry is plan-scoped.
    --level    - Log level: INFO, WARNING, ERROR (required)
    --message  - Log message (required)

Global / no-plan logging:
    Omitting --plan-id writes to .plan/logs/{work,decision,script-execution}-{date}.log.
    marshall-steward uses this path for its STEWARD audit trail with the stable
    message prefix "[STEWARD] (plan-marshall:marshall-steward) …" — one entry per
    AskUserQuestion answer and per auto-decision:

        python3 manage-log.py decision --level INFO \\
            --message "[STEWARD] (plan-marshall:marshall-steward) Selected balanced effort preset"

Arguments (read):
    --plan-id  - Plan identifier (required)
    --type     - Log type: 'script', 'work', or 'decision' (required)
    --limit    - Max entries to return (optional, default: all)
    --phase    - Filter by phase (optional, work/decision logs only)

Examples:
    # Write operations
    python3 manage-log.py script --plan-id EXAMPLE-PLAN --level INFO --message "plan-marshall:manage-tasks:manage-tasks commit-add (0.15s)"
    python3 manage-log.py work --plan-id EXAMPLE-PLAN --level INFO --message "[ARTIFACT] Created deliverable: auth module"
    python3 manage-log.py decision --plan-id EXAMPLE-PLAN --level INFO --message "(skill-name) Detected domain: java"

    # Read operations
    python3 manage-log.py read --plan-id EXAMPLE-PLAN --type work
    python3 manage-log.py read --plan-id EXAMPLE-PLAN --type decision
    python3 manage-log.py read --plan-id EXAMPLE-PLAN --type work --limit 5
    python3 manage-log.py read --plan-id EXAMPLE-PLAN --type decision --phase 1-init
"""

from __future__ import annotations

import argparse
from typing import Any

# Direct imports from same directory (local imports)
from constants import VALID_LOG_LEVELS, VALID_LOG_TYPES
from file_ops import output_toon, safe_main
from input_validation import (
    add_phase_arg,
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from plan_logging import get_log_path, list_recent_work, log_entry, log_separator, read_decision_log, read_work_log

VALID_TYPES = VALID_LOG_TYPES
VALID_LEVELS = VALID_LOG_LEVELS


def handle_read(args: argparse.Namespace) -> dict[str, Any]:
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

    return result


def handle_separator(args: argparse.Namespace) -> dict[str, Any] | None:
    """Handle separator subcommand."""
    log_separator(args.type, args.plan_id)
    return None


def handle_write(args: argparse.Namespace) -> dict[str, Any] | None:
    """Handle write subcommand."""
    log_type = args.log_type
    plan_id = args.plan_id
    level = args.level
    message = args.message

    # Log entry — log_entry is best-effort and never raises into the caller
    # (it swallows all exceptions internally), so no guard is needed here.
    log_entry(log_type, plan_id, level, message)
    return None


def _add_write_args(parser: argparse.ArgumentParser) -> None:
    """Add common write arguments to a subparser.

    ``--plan-id`` is OPTIONAL on write subcommands (``work`` / ``decision`` /
    ``script``): when omitted, the entry is written to the dated global log
    under ``.plan/logs/`` (``work-{date}.log`` / ``decision-{date}.log`` /
    ``script-execution-{date}.log``) instead of a plan-scoped log. This is the
    first-class global/no-plan logging path — plan-less callers such as
    ``marshall-steward`` (which runs before any plan exists) write their
    ``[STEWARD] (plan-marshall:marshall-steward) …`` audit trail through this
    path rather than fabricating a plan id. When ``--plan-id`` IS supplied and
    resolves to an initialized plan, the entry is plan-scoped as before.
    """
    add_plan_id_arg(parser, required=False)
    parser.add_argument('--level', required=True, choices=VALID_LEVELS, help='Log level')
    parser.add_argument('--message', required=True, help='Log message')


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Unified logging operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Write subcommands: work, decision, script
    for log_type in VALID_TYPES:
        if log_type == 'read':
            continue
        write_parser = subparsers.add_parser(log_type, help=f'Write a {log_type} log entry', allow_abbrev=False)
        _add_write_args(write_parser)
        write_parser.set_defaults(log_type=log_type)

    # Separator subcommand
    sep_parser = subparsers.add_parser('separator', help='Add visual separator (blank line) to log', allow_abbrev=False)
    add_plan_id_arg(sep_parser)
    sep_parser.add_argument('--type', default='work', choices=VALID_TYPES, help='Log type (default: work)')

    # Read subcommand
    read_parser = subparsers.add_parser('read', help='Read log entries', allow_abbrev=False)
    add_plan_id_arg(read_parser)
    read_parser.add_argument('--type', required=True, choices=VALID_TYPES, help='Log type')
    read_parser.add_argument('--limit', type=int, help='Max entries to return')
    add_phase_arg(read_parser, required=False)

    args = parse_args_with_toon_errors(parser)

    result: dict[str, Any] | None = None
    if args.command == 'read':
        result = handle_read(args)
    elif args.command == 'separator':
        result = handle_separator(args)
    else:
        result = handle_write(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
