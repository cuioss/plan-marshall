#!/usr/bin/env python3
"""
CLI for unified finding, Q-Gate, and assessment storage.

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

    python3 manage-findings.py assessment add --plan-id <plan_id> --file-path <path> --certainty <certainty> --confidence <confidence> [options]
    python3 manage-findings.py assessment query --plan-id <plan_id> [options]
    python3 manage-findings.py assessment get --plan-id <plan_id> --hash-id <hash_id>
    python3 manage-findings.py assessment clear --plan-id <plan_id> [--agent AGENT]

All commands output TOON format.
"""

import argparse
import sys
from pathlib import Path

# Allow direct invocation and testing — executor sets PYTHONPATH for production
sys.path.insert(0, str(Path(__file__).parent))

from _findings_core import (
    CERTAINTY_VALUES,
    FINDING_TYPES,
    QGATE_PHASES,
    QGATE_SOURCES,
    RESOLUTIONS,
    SEVERITIES,
    add_assessment,
    add_finding,
    add_qgate_finding,
    clear_assessments,
    clear_qgate_findings,
    get_assessment,
    get_finding,
    promote_finding,
    query_assessments,
    query_findings,
    query_qgate_findings,
    resolve_finding,
    resolve_qgate_finding,
)
from file_ops import output_toon, safe_main
from input_validation import add_phase_arg, add_plan_id_arg  # type: ignore[import-not-found]


def cmd_add(args: argparse.Namespace) -> dict:
    """Handle: add"""
    return add_finding(
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


def cmd_query(args: argparse.Namespace) -> dict:
    """Handle: query"""
    promoted = None
    if args.promoted is not None:
        promoted = args.promoted.lower() in ('true', '1', 'yes')

    return query_findings(
        plan_id=args.plan_id,
        finding_type=args.type,
        resolution=args.resolution,
        promoted=promoted,
        file_pattern=args.file_pattern,
    )


def cmd_get(args: argparse.Namespace) -> dict:
    """Handle: get"""
    result = get_finding(args.plan_id, args.hash_id)
    if result:
        return result
    return {'status': 'error', 'message': f'Finding not found: {args.hash_id}'}


def cmd_resolve(args: argparse.Namespace) -> dict:
    """Handle: resolve"""
    return resolve_finding(
        plan_id=args.plan_id,
        hash_id=args.hash_id,
        resolution=args.resolution,
        detail=args.detail,
    )


def cmd_promote(args: argparse.Namespace) -> dict:
    """Handle: promote"""
    return promote_finding(
        plan_id=args.plan_id,
        hash_id=args.hash_id,
        promoted_to=args.promoted_to,
    )


def cmd_qgate_add(args: argparse.Namespace) -> dict:
    """Handle: qgate add"""
    return add_qgate_finding(
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


def cmd_qgate_query(args: argparse.Namespace) -> dict:
    """Handle: qgate query"""
    return query_qgate_findings(
        plan_id=args.plan_id,
        phase=args.phase,
        resolution=args.resolution,
        source=args.source,
        iteration=args.iteration,
    )


def cmd_qgate_resolve(args: argparse.Namespace) -> dict:
    """Handle: qgate resolve"""
    return resolve_qgate_finding(
        plan_id=args.plan_id,
        phase=args.phase,
        hash_id=args.hash_id,
        resolution=args.resolution,
        detail=args.detail,
    )


def cmd_qgate_clear(args: argparse.Namespace) -> dict:
    """Handle: qgate clear"""
    return clear_qgate_findings(
        plan_id=args.plan_id,
        phase=args.phase,
    )


def cmd_assessment_add(args: argparse.Namespace) -> dict:
    """Handle: assessment add"""
    return add_assessment(
        plan_id=args.plan_id,
        file_path=args.file_path,
        certainty=args.certainty,
        confidence=args.confidence,
        agent=args.agent,
        detail=args.detail,
        evidence=args.evidence,
    )


def cmd_assessment_query(args: argparse.Namespace) -> dict:
    """Handle: assessment query"""
    return query_assessments(
        plan_id=args.plan_id,
        certainty=args.certainty,
        min_confidence=args.min_confidence,
        max_confidence=args.max_confidence,
        file_pattern=args.file_pattern,
    )


def cmd_assessment_get(args: argparse.Namespace) -> dict:
    """Handle: assessment get"""
    return get_assessment(args.plan_id, args.hash_id)


def cmd_assessment_clear(args: argparse.Namespace) -> dict:
    """Handle: assessment clear"""
    return clear_assessments(
        plan_id=args.plan_id,
        agent=args.agent,
    )


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Unified finding and Q-Gate storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # --- Plan-scoped finding commands ---

    # add
    add_parser = subparsers.add_parser('add', help='Add a finding', allow_abbrev=False)
    add_plan_id_arg(add_parser)
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
    query_parser = subparsers.add_parser('query', help='Query findings', allow_abbrev=False)
    add_plan_id_arg(query_parser)
    query_parser.add_argument('--type', help='Filter by type (comma-separated)')
    query_parser.add_argument('--resolution', choices=RESOLUTIONS, help='Filter by resolution')
    query_parser.add_argument('--promoted', help='Filter by promoted (true/false)')
    query_parser.add_argument('--file-pattern', help='Glob pattern for file_path')
    query_parser.set_defaults(func=cmd_query)

    # get
    get_parser = subparsers.add_parser('get', help='Get single finding', allow_abbrev=False)
    add_plan_id_arg(get_parser)
    get_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Finding hash ID')
    get_parser.set_defaults(func=cmd_get)

    # resolve
    resolve_parser = subparsers.add_parser('resolve', help='Resolve a finding', allow_abbrev=False)
    add_plan_id_arg(resolve_parser)
    resolve_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Finding hash ID')
    resolve_parser.add_argument(
        '--resolution', required=True, choices=RESOLUTIONS, dest='resolution', help='Resolution status'
    )
    resolve_parser.add_argument('--detail', help='Resolution detail')
    resolve_parser.set_defaults(func=cmd_resolve)

    # promote
    promote_parser = subparsers.add_parser('promote', help='Promote a finding', allow_abbrev=False)
    add_plan_id_arg(promote_parser)
    promote_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Finding hash ID')
    promote_parser.add_argument('--promoted-to', required=True, dest='promoted_to', help='Target ID or "architecture"')
    promote_parser.set_defaults(func=cmd_promote)

    # --- Q-Gate commands ---
    qgate_parser = subparsers.add_parser('qgate', help='Manage per-phase Q-Gate findings', allow_abbrev=False)
    qgate_sub = qgate_parser.add_subparsers(dest='action', required=True)

    # qgate add
    q_add_parser = qgate_sub.add_parser('add', help='Add a Q-Gate finding', allow_abbrev=False)
    add_plan_id_arg(q_add_parser)
    add_phase_arg(q_add_parser, choices=QGATE_PHASES)
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
    q_query_parser = qgate_sub.add_parser('query', help='Query Q-Gate findings', allow_abbrev=False)
    add_plan_id_arg(q_query_parser)
    add_phase_arg(q_query_parser, choices=QGATE_PHASES)
    q_query_parser.add_argument('--resolution', choices=RESOLUTIONS, help='Filter by resolution')
    q_query_parser.add_argument('--source', choices=QGATE_SOURCES, help='Filter by source')
    q_query_parser.add_argument('--iteration', type=int, help='Filter by iteration')
    q_query_parser.set_defaults(func=cmd_qgate_query)

    # qgate resolve
    q_resolve_parser = qgate_sub.add_parser('resolve', help='Resolve a Q-Gate finding', allow_abbrev=False)
    add_plan_id_arg(q_resolve_parser)
    q_resolve_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Finding hash ID')
    q_resolve_parser.add_argument(
        '--resolution', required=True, choices=RESOLUTIONS, dest='resolution', help='Resolution status'
    )
    add_phase_arg(q_resolve_parser, choices=QGATE_PHASES)
    q_resolve_parser.add_argument('--detail', help='Resolution detail')
    q_resolve_parser.set_defaults(func=cmd_qgate_resolve)

    # qgate clear
    q_clear_parser = qgate_sub.add_parser(
        'clear', help='Clear Q-Gate findings for a phase', allow_abbrev=False
    )
    add_plan_id_arg(q_clear_parser)
    add_phase_arg(q_clear_parser, choices=QGATE_PHASES)
    q_clear_parser.set_defaults(func=cmd_qgate_clear)

    # --- Assessment commands ---
    assessment_parser = subparsers.add_parser(
        'assessment', help='Manage component assessments', allow_abbrev=False
    )
    assessment_sub = assessment_parser.add_subparsers(dest='action', required=True)

    # assessment add
    a_add_parser = assessment_sub.add_parser('add', help='Add an assessment', allow_abbrev=False)
    add_plan_id_arg(a_add_parser)
    a_add_parser.add_argument('--file-path', required=True, dest='file_path', help='Path to assessed component')
    a_add_parser.add_argument('--certainty', required=True, choices=CERTAINTY_VALUES, help='Certainty value')
    a_add_parser.add_argument('--confidence', required=True, type=int, help='Confidence 0-100')
    a_add_parser.add_argument('--agent', help='Analysis agent name')
    a_add_parser.add_argument('--detail', help='Reasoning for assessment')
    a_add_parser.add_argument('--evidence', help='Supporting evidence')
    a_add_parser.set_defaults(func=cmd_assessment_add)

    # assessment query
    a_query_parser = assessment_sub.add_parser('query', help='Query assessments', allow_abbrev=False)
    add_plan_id_arg(a_query_parser)
    a_query_parser.add_argument('--certainty', choices=CERTAINTY_VALUES, help='Filter by certainty')
    a_query_parser.add_argument('--min-confidence', type=int, help='Minimum confidence')
    a_query_parser.add_argument('--max-confidence', type=int, help='Maximum confidence')
    a_query_parser.add_argument('--file-pattern', help='Glob pattern for file_path')
    a_query_parser.set_defaults(func=cmd_assessment_query)

    # assessment get
    a_get_parser = assessment_sub.add_parser('get', help='Get single assessment', allow_abbrev=False)
    add_plan_id_arg(a_get_parser)
    a_get_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Assessment hash ID')
    a_get_parser.set_defaults(func=cmd_assessment_get)

    # assessment clear
    a_clear_parser = assessment_sub.add_parser('clear', help='Clear assessments', allow_abbrev=False)
    add_plan_id_arg(a_clear_parser)
    a_clear_parser.add_argument('--agent', help='Only clear assessments from this agent')
    a_clear_parser.set_defaults(func=cmd_assessment_clear)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        result = args.func(args)
        output_toon(result)
        return 0

    parser.print_help()
    return 1


if __name__ == '__main__':
    main()
