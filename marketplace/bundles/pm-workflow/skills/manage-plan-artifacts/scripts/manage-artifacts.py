#!/usr/bin/env python3
"""
CLI for plan-level artifact management.

Usage:
    python3 manage-artifacts.py assessment add <plan_id> <file_path> <certainty> <confidence> [options]
    python3 manage-artifacts.py assessment query <plan_id> [options]
    python3 manage-artifacts.py assessment get <plan_id> <hash_id>

    python3 manage-artifacts.py finding add <plan_id> <type> <title> --detail <detail> [options]
    python3 manage-artifacts.py finding query <plan_id> [options]
    python3 manage-artifacts.py finding get <plan_id> <hash_id>
    python3 manage-artifacts.py finding resolve <plan_id> <hash_id> <resolution> [options]
    python3 manage-artifacts.py finding promote <plan_id> <hash_id> <promoted_to>

All commands output TOON format.
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from artifact_store import (
    CERTAINTY_VALUES,
    FINDING_TYPES,
    RESOLUTIONS,
    SEVERITIES,
    add_assessment,
    add_finding,
    format_output,
    get_assessment,
    get_finding,
    promote_finding,
    query_assessments,
    query_findings,
    resolve_finding,
)


def cmd_assessment_add(args: argparse.Namespace) -> int:
    """Handle: assessment add"""
    result = add_assessment(
        plan_id=args.plan_id,
        file_path=args.file_path,
        certainty=args.certainty,
        confidence=args.confidence,
        agent=args.agent,
        detail=args.detail,
        evidence=args.evidence,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_assessment_query(args: argparse.Namespace) -> int:
    """Handle: assessment query"""
    result = query_assessments(
        plan_id=args.plan_id,
        certainty=args.certainty,
        min_confidence=args.min_confidence,
        max_confidence=args.max_confidence,
        file_pattern=args.file_pattern,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_assessment_get(args: argparse.Namespace) -> int:
    """Handle: assessment get"""
    result = get_assessment(args.plan_id, args.hash_id)
    if result:
        print(format_output(result))
        return 0 if result.get('status') == 'success' else 1
    print(format_output({'status': 'error', 'message': f'Assessment not found: {args.hash_id}'}))
    return 1


def cmd_finding_add(args: argparse.Namespace) -> int:
    """Handle: finding add"""
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


def cmd_finding_query(args: argparse.Namespace) -> int:
    """Handle: finding query"""
    # Handle promoted flag
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


def cmd_finding_get(args: argparse.Namespace) -> int:
    """Handle: finding get"""
    result = get_finding(args.plan_id, args.hash_id)
    if result:
        print(format_output(result))
        return 0 if result.get('status') == 'success' else 1
    print(format_output({'status': 'error', 'message': f'Finding not found: {args.hash_id}'}))
    return 1


def cmd_finding_resolve(args: argparse.Namespace) -> int:
    """Handle: finding resolve"""
    result = resolve_finding(
        plan_id=args.plan_id,
        hash_id=args.hash_id,
        resolution=args.resolution,
        detail=args.detail,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_finding_promote(args: argparse.Namespace) -> int:
    """Handle: finding promote"""
    result = promote_finding(
        plan_id=args.plan_id,
        hash_id=args.hash_id,
        promoted_to=args.promoted_to,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Plan-level artifact management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='artifact_type', required=True)

    # --- Assessment commands ---
    assessment_parser = subparsers.add_parser('assessment', help='Manage assessments')
    assessment_sub = assessment_parser.add_subparsers(dest='action', required=True)

    # assessment add
    add_parser = assessment_sub.add_parser('add', help='Add an assessment')
    add_parser.add_argument('plan_id', help='Plan identifier')
    add_parser.add_argument('file_path', help='Path to assessed component')
    add_parser.add_argument('certainty', choices=CERTAINTY_VALUES, help='Certainty value')
    add_parser.add_argument('confidence', type=int, help='Confidence 0-100')
    add_parser.add_argument('--agent', help='Analysis agent name')
    add_parser.add_argument('--detail', help='Reasoning for assessment')
    add_parser.add_argument('--evidence', help='Supporting evidence')
    add_parser.set_defaults(func=cmd_assessment_add)

    # assessment query
    query_parser = assessment_sub.add_parser('query', help='Query assessments')
    query_parser.add_argument('plan_id', help='Plan identifier')
    query_parser.add_argument('--certainty', choices=CERTAINTY_VALUES, help='Filter by certainty')
    query_parser.add_argument('--min-confidence', type=int, help='Minimum confidence')
    query_parser.add_argument('--max-confidence', type=int, help='Maximum confidence')
    query_parser.add_argument('--file-pattern', help='Glob pattern for file_path')
    query_parser.set_defaults(func=cmd_assessment_query)

    # assessment get
    get_parser = assessment_sub.add_parser('get', help='Get single assessment')
    get_parser.add_argument('plan_id', help='Plan identifier')
    get_parser.add_argument('hash_id', help='Assessment hash ID')
    get_parser.set_defaults(func=cmd_assessment_get)

    # --- Finding commands ---
    finding_parser = subparsers.add_parser('finding', help='Manage findings')
    finding_sub = finding_parser.add_subparsers(dest='action', required=True)

    # finding add
    f_add_parser = finding_sub.add_parser('add', help='Add a finding')
    f_add_parser.add_argument('plan_id', help='Plan identifier')
    f_add_parser.add_argument('type', choices=FINDING_TYPES, help='Finding type')
    f_add_parser.add_argument('title', help='Short title')
    f_add_parser.add_argument('--detail', required=True, help='Detailed description')
    f_add_parser.add_argument('--file-path', help='File path (for code-related)')
    f_add_parser.add_argument('--line', type=int, help='Line number')
    f_add_parser.add_argument('--component', help='Component reference')
    f_add_parser.add_argument('--module', help='Module name (for architecture)')
    f_add_parser.add_argument('--rule', help='Rule ID (for lint/sonar)')
    f_add_parser.add_argument('--severity', choices=SEVERITIES, help='Severity level')
    f_add_parser.set_defaults(func=cmd_finding_add)

    # finding query
    f_query_parser = finding_sub.add_parser('query', help='Query findings')
    f_query_parser.add_argument('plan_id', help='Plan identifier')
    f_query_parser.add_argument('--type', help='Filter by type (comma-separated)')
    f_query_parser.add_argument('--resolution', choices=RESOLUTIONS, help='Filter by resolution')
    f_query_parser.add_argument('--promoted', help='Filter by promoted (true/false)')
    f_query_parser.add_argument('--file-pattern', help='Glob pattern for file_path')
    f_query_parser.set_defaults(func=cmd_finding_query)

    # finding get
    f_get_parser = finding_sub.add_parser('get', help='Get single finding')
    f_get_parser.add_argument('plan_id', help='Plan identifier')
    f_get_parser.add_argument('hash_id', help='Finding hash ID')
    f_get_parser.set_defaults(func=cmd_finding_get)

    # finding resolve
    f_resolve_parser = finding_sub.add_parser('resolve', help='Resolve a finding')
    f_resolve_parser.add_argument('plan_id', help='Plan identifier')
    f_resolve_parser.add_argument('hash_id', help='Finding hash ID')
    f_resolve_parser.add_argument('resolution', choices=RESOLUTIONS, help='Resolution status')
    f_resolve_parser.add_argument('--detail', help='Resolution detail')
    f_resolve_parser.set_defaults(func=cmd_finding_resolve)

    # finding promote
    f_promote_parser = finding_sub.add_parser('promote', help='Promote a finding')
    f_promote_parser.add_argument('plan_id', help='Plan identifier')
    f_promote_parser.add_argument('hash_id', help='Finding hash ID')
    f_promote_parser.add_argument('promoted_to', help='Target ID or "architecture"')
    f_promote_parser.set_defaults(func=cmd_finding_promote)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        result: int = args.func(args)
        return result

    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
