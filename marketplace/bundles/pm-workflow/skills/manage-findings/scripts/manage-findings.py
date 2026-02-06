#!/usr/bin/env python3
"""
CLI for unified finding and Q-Gate storage.

Usage:
    python3 manage-findings.py add --plan-id <plan_id> --type <type> --title <title> --detail <detail> [options]
    python3 manage-findings.py query --plan-id <plan_id> [options]
    python3 manage-findings.py get --plan-id <plan_id> --hash-id <hash_id>
    python3 manage-findings.py resolve --plan-id <plan_id> --hash-id <hash_id> --resolution <resolution> [options]
    python3 manage-findings.py promote --plan-id <plan_id> --hash-id <hash_id> --promoted-to <promoted_to>

    python3 manage-findings.py qgate add --plan-id <plan_id> --phase <phase> --source <source> --type <type> --title <title> --detail <detail> [options]
    python3 manage-findings.py qgate query --plan-id <plan_id> --phase <phase> [options]
    python3 manage-findings.py qgate resolve --plan-id <plan_id> --hash-id <hash_id> --resolution <resolution> --phase <phase> [options]
    python3 manage-findings.py qgate clear --plan-id <plan_id> --phase <phase>

All commands output TOON format.
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from findings_store import (
    FINDING_TYPES,
    QGATE_PHASES,
    QGATE_SOURCES,
    RESOLUTIONS,
    SEVERITIES,
    add_finding,
    add_qgate_finding,
    clear_qgate_findings,
    format_output,
    get_finding,
    promote_finding,
    query_findings,
    query_qgate_findings,
    resolve_finding,
    resolve_qgate_finding,
)


def cmd_add(args: argparse.Namespace) -> int:
    """Handle: add"""
    result = add_finding(
        plan_id=args.plan_id,
        finding_type=args.type,
        title=args.title,
        detail=args.detail,
        file_path=args.file_path,
        line=args.line,
        component=args.component,
        module=args.module,
        rule=args.rule,
        severity=args.severity,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_query(args: argparse.Namespace) -> int:
    """Handle: query"""
    promoted = None
    if args.promoted is not None:
        promoted = args.promoted.lower() in ('true', '1', 'yes')

    result = query_findings(
        plan_id=args.plan_id,
        finding_type=args.type,
        resolution=args.resolution,
        promoted=promoted,
        file_pattern=args.file_pattern,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_get(args: argparse.Namespace) -> int:
    """Handle: get"""
    result = get_finding(args.plan_id, args.hash_id)
    if result:
        print(format_output(result))
        return 0 if result.get('status') == 'success' else 1
    print(format_output({'status': 'error', 'message': f'Finding not found: {args.hash_id}'}))
    return 1


def cmd_resolve(args: argparse.Namespace) -> int:
    """Handle: resolve"""
    result = resolve_finding(
        plan_id=args.plan_id,
        hash_id=args.hash_id,
        resolution=args.resolution,
        detail=args.detail,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_promote(args: argparse.Namespace) -> int:
    """Handle: promote"""
    result = promote_finding(
        plan_id=args.plan_id,
        hash_id=args.hash_id,
        promoted_to=args.promoted_to,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_qgate_add(args: argparse.Namespace) -> int:
    """Handle: qgate add"""
    result = add_qgate_finding(
        plan_id=args.plan_id,
        phase=args.phase,
        source=args.source,
        finding_type=args.type,
        title=args.title,
        detail=args.detail,
        file_path=args.file_path,
        component=args.component,
        severity=args.severity,
        iteration=args.iteration,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_qgate_query(args: argparse.Namespace) -> int:
    """Handle: qgate query"""
    result = query_qgate_findings(
        plan_id=args.plan_id,
        phase=args.phase,
        resolution=args.resolution,
        source=args.source,
        iteration=args.iteration,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_qgate_resolve(args: argparse.Namespace) -> int:
    """Handle: qgate resolve"""
    result = resolve_qgate_finding(
        plan_id=args.plan_id,
        phase=args.phase,
        hash_id=args.hash_id,
        resolution=args.resolution,
        detail=args.detail,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_qgate_clear(args: argparse.Namespace) -> int:
    """Handle: qgate clear"""
    result = clear_qgate_findings(
        plan_id=args.plan_id,
        phase=args.phase,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Unified finding and Q-Gate storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # --- Plan-scoped finding commands ---

    # add
    add_parser = subparsers.add_parser('add', help='Add a finding')
    add_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    add_parser.add_argument('--type', required=True, choices=FINDING_TYPES, dest='type', help='Finding type')
    add_parser.add_argument('--title', required=True, dest='title', help='Short title')
    add_parser.add_argument('--detail', required=True, help='Detailed description')
    add_parser.add_argument('--file-path', help='File path (for code-related)')
    add_parser.add_argument('--line', type=int, help='Line number')
    add_parser.add_argument('--component', help='Component reference')
    add_parser.add_argument('--module', help='Module name (for architecture)')
    add_parser.add_argument('--rule', help='Rule ID (for lint/sonar)')
    add_parser.add_argument('--severity', choices=SEVERITIES, help='Severity level')
    add_parser.set_defaults(func=cmd_add)

    # query
    query_parser = subparsers.add_parser('query', help='Query findings')
    query_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    query_parser.add_argument('--type', help='Filter by type (comma-separated)')
    query_parser.add_argument('--resolution', choices=RESOLUTIONS, help='Filter by resolution')
    query_parser.add_argument('--promoted', help='Filter by promoted (true/false)')
    query_parser.add_argument('--file-pattern', help='Glob pattern for file_path')
    query_parser.set_defaults(func=cmd_query)

    # get
    get_parser = subparsers.add_parser('get', help='Get single finding')
    get_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    get_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Finding hash ID')
    get_parser.set_defaults(func=cmd_get)

    # resolve
    resolve_parser = subparsers.add_parser('resolve', help='Resolve a finding')
    resolve_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    resolve_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Finding hash ID')
    resolve_parser.add_argument('--resolution', required=True, choices=RESOLUTIONS, dest='resolution', help='Resolution status')
    resolve_parser.add_argument('--detail', help='Resolution detail')
    resolve_parser.set_defaults(func=cmd_resolve)

    # promote
    promote_parser = subparsers.add_parser('promote', help='Promote a finding')
    promote_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    promote_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Finding hash ID')
    promote_parser.add_argument('--promoted-to', required=True, dest='promoted_to', help='Target ID or "architecture"')
    promote_parser.set_defaults(func=cmd_promote)

    # --- Q-Gate commands ---
    qgate_parser = subparsers.add_parser('qgate', help='Manage per-phase Q-Gate findings')
    qgate_sub = qgate_parser.add_subparsers(dest='action', required=True)

    # qgate add
    q_add_parser = qgate_sub.add_parser('add', help='Add a Q-Gate finding')
    q_add_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    q_add_parser.add_argument('--phase', required=True, choices=QGATE_PHASES, help='Phase name')
    q_add_parser.add_argument('--source', required=True, choices=QGATE_SOURCES, help='Finding source')
    q_add_parser.add_argument('--type', required=True, choices=FINDING_TYPES, help='Finding type')
    q_add_parser.add_argument('--title', required=True, help='Short title')
    q_add_parser.add_argument('--detail', required=True, help='Detailed description')
    q_add_parser.add_argument('--file-path', help='File path (optional)')
    q_add_parser.add_argument('--component', help='Component reference (optional)')
    q_add_parser.add_argument('--severity', choices=SEVERITIES, help='Severity level')
    q_add_parser.add_argument('--iteration', type=int, help='Phase iteration number')
    q_add_parser.set_defaults(func=cmd_qgate_add)

    # qgate query
    q_query_parser = qgate_sub.add_parser('query', help='Query Q-Gate findings')
    q_query_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    q_query_parser.add_argument('--phase', required=True, choices=QGATE_PHASES, help='Phase name')
    q_query_parser.add_argument('--resolution', choices=RESOLUTIONS, help='Filter by resolution')
    q_query_parser.add_argument('--source', choices=QGATE_SOURCES, help='Filter by source')
    q_query_parser.add_argument('--iteration', type=int, help='Filter by iteration')
    q_query_parser.set_defaults(func=cmd_qgate_query)

    # qgate resolve
    q_resolve_parser = qgate_sub.add_parser('resolve', help='Resolve a Q-Gate finding')
    q_resolve_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    q_resolve_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Finding hash ID')
    q_resolve_parser.add_argument('--resolution', required=True, choices=RESOLUTIONS, dest='resolution', help='Resolution status')
    q_resolve_parser.add_argument('--phase', required=True, choices=QGATE_PHASES, help='Phase name')
    q_resolve_parser.add_argument('--detail', help='Resolution detail')
    q_resolve_parser.set_defaults(func=cmd_qgate_resolve)

    # qgate clear
    q_clear_parser = qgate_sub.add_parser('clear', help='Clear Q-Gate findings for a phase')
    q_clear_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    q_clear_parser.add_argument('--phase', required=True, choices=QGATE_PHASES, help='Phase name')
    q_clear_parser.set_defaults(func=cmd_qgate_clear)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        result: int = args.func(args)
        return result

    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
