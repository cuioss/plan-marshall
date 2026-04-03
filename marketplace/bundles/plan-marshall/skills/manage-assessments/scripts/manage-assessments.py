#!/usr/bin/env python3
"""
Assessment storage for plan-level component evaluations.

Provides JSONL-based storage for certainty/confidence assessments
from analysis agents.

Storage: .plan/plans/{plan_id}/artifacts/assessments.jsonl

Usage:
    manage-assessments.py add --plan-id PLAN_ID --file-path PATH --certainty CERTAINTY --confidence CONFIDENCE [OPTIONS]
    manage-assessments.py query --plan-id PLAN_ID [OPTIONS]
    manage-assessments.py clear --plan-id PLAN_ID [OPTIONS]
    manage-assessments.py get --plan-id PLAN_ID --hash-id HASH_ID

Stdlib-only - no external dependencies (except shared modules via PYTHONPATH).
"""

import argparse
import json
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from input_validation import validate_plan_id  # type: ignore[import-not-found]
from jsonl_store import (  # type: ignore[import-not-found]
    append_jsonl,
    ensure_parent_dir,
    generate_hash_id,
    get_artifact_path,
    output_toon,
    read_jsonl,
    timestamp,
)
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Constants
CERTAINTY_VALUES = ['CERTAIN_INCLUDE', 'CERTAIN_EXCLUDE', 'UNCERTAIN']


# --- Assessment Operations ---


def get_assessments_path(plan_id: str) -> 'Path':
    """Returns .plan/plans/{plan_id}/artifacts/assessments.jsonl"""
    validate_plan_id(plan_id)
    return get_artifact_path(plan_id, 'assessments.jsonl')


def clear_assessments(
    plan_id: str,
    agent: str | None = None,
) -> dict[str, Any]:
    """Clear assessment records, optionally filtered by agent."""
    path = get_assessments_path(plan_id)
    if not path.exists():
        return {'status': 'success', 'cleared': 0}

    records = read_jsonl(path)
    original_count = len(records)

    if agent:
        remaining = [r for r in records if r.get('agent') != agent]
        cleared = original_count - len(remaining)
        ensure_parent_dir(path)
        with open(path, 'w', encoding='utf-8') as f:
            for record in remaining:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    else:
        cleared = original_count
        path.unlink()

    return {'status': 'success', 'cleared': cleared}


def add_assessment(
    plan_id: str,
    file_path: str,
    certainty: str,
    confidence: int,
    agent: str | None = None,
    detail: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    """Add an assessment record."""
    if certainty not in CERTAINTY_VALUES:
        return {'status': 'error', 'message': f'Invalid certainty: {certainty}. Must be one of {CERTAINTY_VALUES}'}

    if not 0 <= confidence <= 100:
        return {'status': 'error', 'message': f'Invalid confidence: {confidence}. Must be 0-100'}

    hash_id = generate_hash_id()
    record = {
        'hash_id': hash_id,
        'timestamp': timestamp(),
        'file_path': file_path,
        'certainty': certainty,
        'confidence': confidence,
    }
    if agent:
        record['agent'] = agent
    if detail:
        record['detail'] = detail
    if evidence:
        record['evidence'] = evidence

    append_jsonl(get_assessments_path(plan_id), record)

    return {'status': 'success', 'hash_id': hash_id, 'file_path': file_path}


def query_assessments(
    plan_id: str,
    certainty: str | None = None,
    min_confidence: int | None = None,
    max_confidence: int | None = None,
    file_pattern: str | None = None,
) -> dict[str, Any]:
    """Query assessments with filters."""
    path = get_assessments_path(plan_id)
    records = read_jsonl(path)
    total_count = len(records)

    filtered = []
    for r in records:
        if certainty and r.get('certainty') != certainty:
            continue
        if min_confidence is not None and r.get('confidence', 0) < min_confidence:
            continue
        if max_confidence is not None and r.get('confidence', 100) > max_confidence:
            continue
        if file_pattern and not fnmatch(r.get('file_path', ''), file_pattern):
            continue
        filtered.append(r)

    result = {
        'status': 'success',
        'plan_id': plan_id,
        'total_count': total_count,
        'filtered_count': len(filtered),
        'assessments': filtered,
        'file_paths': list({r.get('file_path') for r in filtered}),
    }

    return result


def get_assessment(plan_id: str, hash_id: str) -> dict[str, Any]:
    """Get a single assessment by hash_id."""
    path = get_assessments_path(plan_id)
    for record in read_jsonl(path):
        if record.get('hash_id') == hash_id:
            return {'status': 'success', **record}
    return {'status': 'error', 'message': f'Assessment not found: {hash_id}'}


# --- CLI ---


def cmd_add(args: argparse.Namespace) -> int:
    """Handle: add"""
    result = add_assessment(
        plan_id=args.plan_id,
        file_path=args.file_path,
        certainty=args.certainty,
        confidence=args.confidence,
        agent=args.agent,
        detail=args.detail,
        evidence=args.evidence,
    )
    print(output_toon(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_query(args: argparse.Namespace) -> int:
    """Handle: query"""
    result = query_assessments(
        plan_id=args.plan_id,
        certainty=args.certainty,
        min_confidence=args.min_confidence,
        max_confidence=args.max_confidence,
        file_pattern=args.file_pattern,
    )
    print(output_toon(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_clear(args: argparse.Namespace) -> int:
    """Handle: clear"""
    result = clear_assessments(
        plan_id=args.plan_id,
        agent=args.agent,
    )
    print(output_toon(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_get(args: argparse.Namespace) -> int:
    """Handle: get"""
    result = get_assessment(args.plan_id, args.hash_id)
    print(output_toon(result))
    return 0 if result.get('status') == 'success' else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Assessment storage for plan-level component evaluations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='action', required=True)

    # add
    add_parser = subparsers.add_parser('add', help='Add an assessment')
    add_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    add_parser.add_argument('--file-path', required=True, dest='file_path', help='Path to assessed component')
    add_parser.add_argument('--certainty', required=True, choices=CERTAINTY_VALUES, help='Certainty value')
    add_parser.add_argument('--confidence', required=True, type=int, help='Confidence 0-100')
    add_parser.add_argument('--agent', help='Analysis agent name')
    add_parser.add_argument('--detail', help='Reasoning for assessment')
    add_parser.add_argument('--evidence', help='Supporting evidence')
    add_parser.set_defaults(func=cmd_add)

    # query
    query_parser = subparsers.add_parser('query', help='Query assessments')
    query_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    query_parser.add_argument('--certainty', choices=CERTAINTY_VALUES, help='Filter by certainty')
    query_parser.add_argument('--min-confidence', type=int, help='Minimum confidence')
    query_parser.add_argument('--max-confidence', type=int, help='Maximum confidence')
    query_parser.add_argument('--file-pattern', help='Glob pattern for file_path')
    query_parser.set_defaults(func=cmd_query)

    # clear
    clear_parser = subparsers.add_parser('clear', help='Clear assessments')
    clear_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    clear_parser.add_argument('--agent', help='Only clear assessments from this agent')
    clear_parser.set_defaults(func=cmd_clear)

    # get
    get_parser = subparsers.add_parser('get', help='Get single assessment')
    get_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    get_parser.add_argument('--hash-id', required=True, dest='hash_id', help='Assessment hash ID')
    get_parser.set_defaults(func=cmd_get)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        result: int = args.func(args)
        return result

    parser.print_help()
    return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(serialize_toon({'status': 'error', 'error': 'unexpected', 'message': str(e)}), file=sys.stderr)
        sys.exit(1)
