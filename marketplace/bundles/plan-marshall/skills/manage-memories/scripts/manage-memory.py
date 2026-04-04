#!/usr/bin/env python3
"""
Manage the .plan/memory/ layer for session persistence.

Provides CRUD operations for memory files organized by category:
context, decisions, interfaces.

Output: TOON to stdout with operation results.
"""

import argparse
import json
import re
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Direct imports - PYTHONPATH set by executor
from constants import DIR_MEMORIES  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    base_path,
    now_utc_iso,
    output_toon,
    output_toon_error,
    parse_duration,  # type: ignore[import-not-found]
    read_json,
    safe_main,
    write_json,
)
from file_ops import output_success as _output_success
from input_validation import check_field_type, check_required_fields  # type: ignore[import-not-found]

# Suppress deprecation warnings in output
warnings.filterwarnings('ignore', category=DeprecationWarning)


# Get memory base path from base_path
MEMORY_BASE = base_path(DIR_MEMORIES)
CATEGORIES = ('context',)


def get_memory_path(category: str, identifier: str | None = None) -> Path:
    """Get path to memory category or specific file."""
    if category not in CATEGORIES:
        raise ValueError(f'Invalid category: {category}. Must be one of: {", ".join(CATEGORIES)}')

    path = MEMORY_BASE / category
    if identifier:
        # Sanitize identifier for filename
        safe_id = re.sub(r'[^\w\-.]', '_', identifier)
        if not safe_id.endswith('.json'):
            safe_id += '.json'
        path = path / safe_id

    return path


def create_memory_envelope(category: str, identifier: str, content: Any, session_id: str | None = None) -> dict:
    """Create memory file with metadata envelope."""
    return {
        'meta': {
            'created': now_utc_iso(),
            'category': category,
            'summary': identifier,
            'session_id': session_id,
        },
        'content': content,
    }


def read_memory_file(file_path: Path) -> dict:
    """Read and parse a memory file."""
    result: dict = read_json(file_path)
    return result


def write_memory_file(file_path: Path, data: dict) -> None:
    """Write memory file with proper formatting."""
    write_json(file_path, data)


def get_file_info(file_path: Path) -> dict:
    """Get metadata about a memory file."""
    stat = file_path.stat()
    try:
        data = read_memory_file(file_path)
        meta = data.get('meta', {})
    except (json.JSONDecodeError, KeyError):
        meta = {}

    return {
        'name': file_path.name,
        'path': str(file_path),
        'created': meta.get('created', datetime.fromtimestamp(stat.st_ctime).isoformat() + 'Z'),
        'size': stat.st_size,
        'summary': meta.get('summary', file_path.stem),
        'category': meta.get('category'),
    }


def output_success(operation: str, **kwargs) -> None:
    """Output success result as TOON to stdout."""
    _output_success(operation, **kwargs)


def output_error(operation: str, error: str) -> int:
    """Output error result as TOON and return 1."""
    output_toon_error(operation, error)
    return 1


def cmd_save(args) -> int:
    """Save content to memory file."""
    try:
        content = json.loads(args.content)

        # Generate timestamped filename for context category
        if args.category == 'context':
            date_prefix = datetime.now(UTC).strftime('%Y-%m-%d')
            identifier = f'{date_prefix}-{args.identifier}'
        else:
            identifier = args.identifier

        file_path = get_memory_path(args.category, identifier)
        data = create_memory_envelope(args.category, args.identifier, content, args.session_id)

        write_memory_file(file_path, data)

        output_success('save', path=str(file_path), category=args.category, identifier=identifier)
        return 0
    except json.JSONDecodeError as e:
        output_error('save', f'Invalid JSON content: {e}')
        return 1
    except Exception as e:
        output_error('save', str(e))
        return 1


def cmd_load(args) -> int:
    """Load content from memory file."""
    try:
        file_path = get_memory_path(args.category, args.identifier)

        if not file_path.exists():
            output_error('load', f'File not found: {file_path}')
            return 1

        data = read_memory_file(file_path)

        output_success('load', path=str(file_path), meta=data.get('meta', {}), content=data.get('content', {}))
        return 0
    except Exception as e:
        output_error('load', str(e))
        return 1


def cmd_list(args) -> int:
    """List memory files in category."""
    try:
        files = []

        if args.category:
            categories = [args.category]
        else:
            categories = list(CATEGORIES)

        for category in categories:
            cat_path = MEMORY_BASE / category
            if not cat_path.exists():
                continue

            for file_path in cat_path.glob('*.json'):
                info = get_file_info(file_path)

                # Apply --since filter
                if args.since:
                    try:
                        duration = parse_duration(args.since)
                        cutoff = datetime.now(UTC) - duration
                        created_str = info.get('created', '')
                        if created_str:
                            # Parse ISO timestamp; append UTC if naive (Z-suffix stripped)
                            created = datetime.fromisoformat(created_str.rstrip('Z')).replace(tzinfo=UTC)
                            if created < cutoff:
                                continue
                    except (ValueError, TypeError):
                        pass

                files.append(info)

        # Sort by created date, newest first
        files.sort(key=lambda x: x.get('created', ''), reverse=True)

        output_success('list', category=args.category, count=len(files), files=files)
        return 0
    except Exception as e:
        output_error('list', str(e))
        return 1


def cmd_query(args) -> int:
    """Find memory files matching pattern."""
    try:
        # Convert glob pattern to regex
        pattern = args.pattern.replace('*', '.*').replace('?', '.')
        regex = re.compile(pattern, re.IGNORECASE)

        files = []
        categories = [args.category] if args.category else CATEGORIES

        for category in categories:
            cat_path = MEMORY_BASE / category
            if not cat_path.exists():
                continue

            for file_path in cat_path.glob('*.json'):
                # Match against filename and summary
                info = get_file_info(file_path)
                if regex.search(file_path.stem) or regex.search(info.get('summary', '')):
                    files.append(info)

        files.sort(key=lambda x: x.get('created', ''), reverse=True)

        output_success('query', pattern=args.pattern, count=len(files), files=files)
        return 0
    except Exception as e:
        output_error('query', str(e))
        return 1


def cmd_cleanup(args) -> int:
    """Remove old memory files based on age."""
    try:
        duration = parse_duration(args.older_than)
        cutoff = datetime.now(UTC) - duration
        dry_run = getattr(args, 'dry_run', False)

        removed = []
        categories = [args.category] if args.category else CATEGORIES

        for category in categories:
            cat_path = MEMORY_BASE / category
            if not cat_path.exists():
                continue

            for file_path in cat_path.glob('*.json'):
                try:
                    data = read_memory_file(file_path)
                    created_str = data.get('meta', {}).get('created', '')
                    if created_str:
                        created = datetime.fromisoformat(created_str.rstrip('Z')).replace(tzinfo=UTC)
                        if created < cutoff:
                            if not dry_run:
                                file_path.unlink()
                            removed.append(str(file_path))
                except (json.JSONDecodeError, ValueError, KeyError):
                    # If we can't read the file, check file modification time
                    stat = file_path.stat()
                    if datetime.fromtimestamp(stat.st_mtime) < cutoff:
                        if not dry_run:
                            file_path.unlink()
                        removed.append(str(file_path))

        status = 'dry_run' if dry_run else 'success'
        output_toon(
            {
                'status': status,
                'operation': 'cleanup',
                'older_than': args.older_than,
                'removed_count': len(removed),
                'removed': removed,
            }
        )
        return 0
    except Exception as e:
        output_error('cleanup', str(e))
        return 1


def validate_memory_format(data: dict) -> list[dict]:
    """Validate memory file format."""
    checks = []

    # Check required envelope
    required = ['meta', 'content']
    passed, missing = check_required_fields(data, required)
    checks.append(
        {'check': 'required_fields', 'passed': passed, 'fields': required, 'missing': missing if not passed else []}
    )

    # Check meta structure
    if 'meta' in data:
        passed, msg = check_field_type(data, 'meta', dict)
        checks.append({'check': 'meta_object', 'passed': passed, 'message': msg})

        if passed:
            meta_required = ['created', 'category', 'summary']
            meta_passed, meta_missing = check_required_fields(data['meta'], meta_required)
            checks.append(
                {
                    'check': 'meta_required_fields',
                    'passed': meta_passed,
                    'fields': meta_required,
                    'missing': meta_missing if not meta_passed else [],
                }
            )

            # Validate category value
            if 'category' in data['meta']:
                valid_categories = CATEGORIES
                cat = data['meta']['category']
                checks.append(
                    {
                        'check': 'category_valid',
                        'passed': cat in valid_categories,
                        'value': cat,
                        'valid_values': valid_categories,
                    }
                )

    # Check content exists (can be any type)
    if 'content' in data:
        checks.append(
            {'check': 'content_present', 'passed': True, 'message': f'Content is {type(data["content"]).__name__}'}
        )

    return checks


def cmd_validate(args) -> int:
    """Validate memory file format and structure."""
    try:
        file_path = Path(args.file)

        if not file_path.exists():
            output_error('validate', f'File not found: {file_path}')
            return 1

        # Parse JSON
        try:
            data = read_memory_file(file_path)
        except json.JSONDecodeError as e:
            result = {
                'status': 'success',
                'success': True,
                'valid': False,
                'file': str(file_path),
                'format': 'memory',
                'checks': [{'check': 'json_syntax', 'passed': False, 'error': str(e)}],
            }
            output_toon(result)
            return 0

        # Add JSON syntax check
        checks = [{'check': 'json_syntax', 'passed': True}]

        # Run validation
        checks.extend(validate_memory_format(data))

        # Determine overall validity
        valid = all(c.get('passed', True) for c in checks)

        result = {
            'status': 'success',
            'success': True,
            'valid': valid,
            'file': str(file_path),
            'format': 'memory',
            'checks': checks,
        }
        output_toon(result)
        return 0
    except Exception as e:
        output_error('validate', str(e))
        return 1


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Manage .plan/memory/ layer for session persistence',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Categories:
  context     - Session context snapshots (short-lived)

Examples:
  # Save context snapshot (directories created on-the-fly)
  %(prog)s save --category context --identifier "feature-auth" --content '{"notes": "Working on auth"}'

  # Load memory file
  %(prog)s load --category context --identifier "2025-12-02-feature-auth"

  # List context files from last 7 days
  %(prog)s list --category context --since 7d

  # Find files matching pattern
  %(prog)s query --pattern "auth*" --category context

  # Cleanup old context files
  %(prog)s cleanup --category context --older-than 7d
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    # save command
    p_save = subparsers.add_parser('save', help='Save content to memory file')
    p_save.add_argument('--category', required=True, choices=CATEGORIES, help='Memory category')
    p_save.add_argument('--identifier', required=True, help='File identifier/summary')
    p_save.add_argument('--content', required=True, help='JSON content to save')
    p_save.add_argument('--session-id', dest='session_id', help='Optional session ID')
    p_save.set_defaults(func=cmd_save)

    # load command
    p_load = subparsers.add_parser('load', help='Load content from memory file')
    p_load.add_argument('--category', required=True, choices=CATEGORIES, help='Memory category')
    p_load.add_argument('--identifier', required=True, help='File identifier')
    p_load.set_defaults(func=cmd_load)

    # list command
    p_list = subparsers.add_parser('list', help='List memory files')
    p_list.add_argument('--category', choices=CATEGORIES, help='Filter by category')
    p_list.add_argument('--since', help='Filter by age (e.g., 7d, 24h)')
    p_list.set_defaults(func=cmd_list)

    # query command
    p_query = subparsers.add_parser('query', help='Find files matching pattern')
    p_query.add_argument('--pattern', required=True, help='Glob pattern to match')
    p_query.add_argument('--category', choices=CATEGORIES, help='Filter by category')
    p_query.set_defaults(func=cmd_query)

    # cleanup command
    p_cleanup = subparsers.add_parser('cleanup', help='Remove old memory files')
    p_cleanup.add_argument('--category', choices=CATEGORIES, help='Filter by category')
    p_cleanup.add_argument(
        '--older-than', required=True, dest='older_than', help='Remove files older than (e.g., 7d, 24h)'
    )
    p_cleanup.add_argument(
        '--dry-run', action='store_true', dest='dry_run', help='Show what would be removed without removing'
    )
    p_cleanup.set_defaults(func=cmd_cleanup)

    # validate command
    p_validate = subparsers.add_parser('validate', help='Validate memory file format')
    p_validate.add_argument('--file', required=True, help='Path to memory file to validate')
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args) or 0


if __name__ == '__main__':
    main()
