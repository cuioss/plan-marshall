#!/usr/bin/env python3
"""
Assessment storage for plan-level component evaluations.

Provides JSONL-based storage for certainty/confidence assessments
from analysis agents.

Storage: .plan/plans/{plan_id}/artifacts/assessments.jsonl

Stdlib-only - no external dependencies (except toon_parser for output).
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

# Add toon_parser to path
_toon_parser_path = (
    Path(__file__).parent.parent.parent.parent.parent / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts'
)
if _toon_parser_path.exists():
    sys.path.insert(0, str(_toon_parser_path))
    from toon_parser import serialize_toon
else:
    # Fallback: simple dict-to-toon for basic cases
    def serialize_toon(data: dict[str, Any], indent: int = 0) -> str:
        lines = []
        prefix = '  ' * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'{prefix}{key}:')
                lines.append(serialize_toon(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f'{prefix}{key}[{len(value)}]:')
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f'{prefix}  {",".join(str(v) for v in item.values())}')
                    else:
                        lines.append(f'{prefix}  - {item}')
            elif isinstance(value, bool):
                lines.append(f'{prefix}{key}: {"true" if value else "false"}')
            elif value is None:
                lines.append(f'{prefix}{key}: null')
            else:
                lines.append(f'{prefix}{key}: {value}')
        return '\n'.join(lines)


# Constants
CERTAINTY_VALUES = ['CERTAIN_INCLUDE', 'CERTAIN_EXCLUDE', 'UNCERTAIN']


# --- JSONL Infrastructure ---


def get_plan_root() -> Path:
    """Get the .plan directory root."""
    import os

    base_dir = os.environ.get('PLAN_BASE_DIR')
    if base_dir:
        return Path(base_dir)
    return Path.cwd() / '.plan'


def get_assessments_path(plan_id: str) -> Path:
    """Returns .plan/plans/{plan_id}/artifacts/assessments.jsonl"""
    return get_plan_root() / 'plans' / plan_id / 'artifacts' / 'assessments.jsonl'


def generate_hash_id() -> str:
    """Generate a 6-char hex hash for artifact identification."""
    import secrets

    data = f'{datetime.now(UTC).isoformat()}{secrets.token_hex(8)}'
    return hashlib.sha256(data.encode()).hexdigest()[:6]


def _ensure_dir(path: Path) -> None:
    """Ensure parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append a JSON record to a JSONL file."""
    _ensure_dir(path)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read all records from a JSONL file."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _timestamp() -> str:
    """Get current ISO timestamp."""
    return datetime.now(UTC).isoformat()


def format_output(data: dict[str, Any]) -> str:
    """Format output as TOON."""
    result: str = serialize_toon(data)
    return result


# --- Assessment Operations ---


def clear_assessments(
    plan_id: str,
    agent: str | None = None,
) -> dict[str, Any]:
    """Clear assessment records, optionally filtered by agent."""
    path = get_assessments_path(plan_id)
    if not path.exists():
        return {'status': 'success', 'cleared': 0}

    records = _read_jsonl(path)
    original_count = len(records)

    if agent:
        remaining = [r for r in records if r.get('agent') != agent]
        cleared = original_count - len(remaining)
        _ensure_dir(path)
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
        'timestamp': _timestamp(),
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

    _append_jsonl(get_assessments_path(plan_id), record)

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
    records = _read_jsonl(path)
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


def get_assessment(plan_id: str, hash_id: str) -> dict[str, Any] | None:
    """Get a single assessment by hash_id."""
    path = get_assessments_path(plan_id)
    for record in _read_jsonl(path):
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
    print(format_output(result))
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
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_clear(args: argparse.Namespace) -> int:
    """Handle: clear"""
    result = clear_assessments(
        plan_id=args.plan_id,
        agent=args.agent,
    )
    print(format_output(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_get(args: argparse.Namespace) -> int:
    """Handle: get"""
    result = get_assessment(args.plan_id, args.hash_id)
    if result:
        print(format_output(result))
        return 0 if result.get('status') == 'success' else 1
    print(format_output({'status': 'error', 'message': f'Assessment not found: {args.hash_id}'}))
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Assessment storage for plan-level component evaluations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='action', required=True)

    # add
    add_parser = subparsers.add_parser('add', help='Add an assessment')
    add_parser.add_argument('plan_id', help='Plan identifier')
    add_parser.add_argument('file_path', help='Path to assessed component')
    add_parser.add_argument('certainty', choices=CERTAINTY_VALUES, help='Certainty value')
    add_parser.add_argument('confidence', type=int, help='Confidence 0-100')
    add_parser.add_argument('--agent', help='Analysis agent name')
    add_parser.add_argument('--detail', help='Reasoning for assessment')
    add_parser.add_argument('--evidence', help='Supporting evidence')
    add_parser.set_defaults(func=cmd_add)

    # query
    query_parser = subparsers.add_parser('query', help='Query assessments')
    query_parser.add_argument('plan_id', help='Plan identifier')
    query_parser.add_argument('--certainty', choices=CERTAINTY_VALUES, help='Filter by certainty')
    query_parser.add_argument('--min-confidence', type=int, help='Minimum confidence')
    query_parser.add_argument('--max-confidence', type=int, help='Maximum confidence')
    query_parser.add_argument('--file-pattern', help='Glob pattern for file_path')
    query_parser.set_defaults(func=cmd_query)

    # clear
    clear_parser = subparsers.add_parser('clear', help='Clear assessments')
    clear_parser.add_argument('plan_id', help='Plan identifier')
    clear_parser.add_argument('--agent', help='Only clear assessments from this agent')
    clear_parser.set_defaults(func=cmd_clear)

    # get
    get_parser = subparsers.add_parser('get', help='Get single assessment')
    get_parser.add_argument('plan_id', help='Plan identifier')
    get_parser.add_argument('hash_id', help='Assessment hash ID')
    get_parser.set_defaults(func=cmd_get)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        result: int = args.func(args)
        return result

    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
