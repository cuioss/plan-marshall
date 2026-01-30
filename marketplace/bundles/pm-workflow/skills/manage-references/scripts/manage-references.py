#!/usr/bin/env python3
"""
Manage references.json files with field-level access and list management.

Tracks files, branches, and external references for a plan.
Storage: JSON format (.plan/plans/{plan_id}/references.json)
Output: TOON format for API responses

Usage:
    python3 manage-references.py create --plan-id my-plan --branch feature/x
    python3 manage-references.py read --plan-id my-plan
    python3 manage-references.py get --plan-id my-plan --field branch
    python3 manage-references.py set --plan-id my-plan --field branch --value feature/x
    python3 manage-references.py add-file --plan-id my-plan --file src/Main.java
    python3 manage-references.py add-list --plan-id my-plan --field affected_files --values file1.md,file2.md
    python3 manage-references.py set-list --plan-id my-plan --field affected_files --values file1.md,file2.md
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TypedDict, cast

from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]


class ReferencesData(TypedDict, total=False):
    """Type definition for references data structure."""

    branch: str
    base_branch: str
    issue_url: str
    build_system: str
    modified_files: list[str]
    domains: list[str]
    affected_files: list[str]
    external_docs: dict[str, Any]


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def get_references_path(plan_id: str) -> Path:
    """Get the references.json file path."""
    return cast(Path, base_path('plans', plan_id, 'references.json'))


def read_references(plan_id: str) -> dict[Any, Any]:
    """Read references.json for a plan."""
    path = get_references_path(plan_id)
    if not path.exists():
        return {}
    return cast(dict[Any, Any], json.loads(path.read_text(encoding='utf-8')))


def write_references(plan_id: str, refs: dict) -> None:
    """Write references.json for a plan."""
    path = get_references_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(refs, indent=2)
    atomic_write_file(path, content)


def output_toon(data: dict) -> None:
    """Print TOON formatted output to stdout."""
    lines = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f'{key}: {"true" if value else "false"}')
        elif isinstance(value, list):
            if value:
                lines.append(f'{key}[{len(value)}]:')
                for item in value:
                    lines.append(f'  - {item}')
            else:
                lines.append(f'{key}: []')
        elif isinstance(value, dict):
            lines.append(f'{key}:')
            for k, v in value.items():
                if isinstance(v, list):
                    lines.append(f'  {k}: {len(v)} items')
                else:
                    lines.append(f'  {k}: {v}')
        elif value is None:
            lines.append(f'{key}: null')
        else:
            lines.append(f'{key}: {value}')
    print('\n'.join(lines))


def cmd_create(args):
    """Create references.json with basic fields."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    path = get_references_path(args.plan_id)
    if path.exists():
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'already_exists',
                'message': 'references.json already exists',
            }
        )
        sys.exit(1)

    # Build base references
    refs = {'branch': args.branch, 'base_branch': 'main', 'modified_files': []}

    # Add optional fields
    if args.issue_url:
        refs['issue_url'] = args.issue_url
    if args.build_system:
        refs['build_system'] = args.build_system
    if args.domains:
        refs['domains'] = [d.strip() for d in args.domains.split(',') if d.strip()]

    write_references(args.plan_id, refs)

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'file': 'references.json',
            'created': True,
            'fields': list(refs.keys()),
        }
    )


def cmd_read(args):
    """Read entire references.json."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    refs = read_references(args.plan_id)
    if not refs:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'file_not_found',
                'message': 'references.json not found',
            }
        )
        sys.exit(1)

    # Summarize lists
    summary = {}
    for key, value in refs.items():
        if isinstance(value, list):
            summary[key] = f'{len(value)} items'
        else:
            summary[key] = value

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'references': summary})


def cmd_get(args):
    """Get a specific field value."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    refs = read_references(args.plan_id)
    if not refs:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'file_not_found',
                'message': 'references.json not found',
            }
        )
        sys.exit(1)

    value = refs.get(args.field)
    if value is None:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'field': args.field,
                'error': 'field_not_found',
                'message': f"Field '{args.field}' not found",
            }
        )
        sys.exit(1)

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'field': args.field, 'value': value})


def cmd_set(args):
    """Set a specific field value."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    refs = read_references(args.plan_id)
    previous = refs.get(args.field)
    refs[args.field] = args.value
    write_references(args.plan_id, refs)

    result = {'status': 'success', 'plan_id': args.plan_id, 'field': args.field, 'value': args.value}
    if previous is not None:
        result['previous'] = previous
    output_toon(result)


def cmd_add_file(args):
    """Add a file to modified_files list."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    refs = read_references(args.plan_id)
    if 'modified_files' not in refs:
        refs['modified_files'] = []

    if args.file not in refs['modified_files']:
        refs['modified_files'].append(args.file)
        write_references(args.plan_id, refs)

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'section': 'modified_files',
            'added': args.file,
            'total': len(refs['modified_files']),
        }
    )


def cmd_remove_file(args):
    """Remove a file from modified_files list."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    refs = read_references(args.plan_id)
    if 'modified_files' not in refs or args.file not in refs['modified_files']:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'not_found',
                'message': f"File '{args.file}' not in modified_files",
            }
        )
        sys.exit(1)

    refs['modified_files'].remove(args.file)
    write_references(args.plan_id, refs)

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'section': 'modified_files',
            'removed': args.file,
            'total': len(refs['modified_files']),
        }
    )


def cmd_add_list(args):
    """Add multiple values to a list field."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    refs = read_references(args.plan_id)

    # Initialize field as list if not exists
    if args.field not in refs:
        refs[args.field] = []
    elif not isinstance(refs[args.field], list):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'field': args.field,
                'error': 'not_a_list',
                'message': f"Field '{args.field}' is not a list",
            }
        )
        sys.exit(1)

    # Parse comma-separated values
    values = [v.strip() for v in args.values.split(',') if v.strip()]
    added = []
    for value in values:
        if value not in refs[args.field]:
            refs[args.field].append(value)
            added.append(value)

    write_references(args.plan_id, refs)

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'field': args.field,
            'added_count': len(added),
            'total': len(refs[args.field]),
        }
    )


def cmd_set_list(args):
    """Set a list field to new values (replaces existing list)."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    refs = read_references(args.plan_id)
    if not refs:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'file_not_found',
                'message': 'references.json not found',
            }
        )
        sys.exit(1)

    # Get previous count if field exists
    previous_count = 0
    if args.field in refs and isinstance(refs[args.field], list):
        previous_count = len(refs[args.field])

    # Parse comma-separated values
    values = [v.strip() for v in args.values.split(',') if v.strip()]

    # Set the field to the new list (replaces existing)
    refs[args.field] = values
    write_references(args.plan_id, refs)

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'field': args.field,
            'previous_count': previous_count,
            'count': len(values),
        }
    )


def cmd_get_context(args):
    """Get all references context in one call."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    refs = read_references(args.plan_id)
    if not refs:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'file_not_found',
                'message': 'references.json not found',
            }
        )
        sys.exit(1)

    # Build comprehensive context
    context = {
        'status': 'success',
        'plan_id': args.plan_id,
        'branch': refs.get('branch', ''),
        'base_branch': refs.get('base_branch', 'main'),
        'modified_files_count': len(refs.get('modified_files', [])),
    }

    # Include optional fields if present
    if refs.get('issue_url'):
        context['issue_url'] = refs['issue_url']
    if refs.get('build_system'):
        context['build_system'] = refs['build_system']

    # Include file lists if requested
    if args.include_files:
        context['modified_files'] = refs.get('modified_files', [])

    output_toon(context)


def main():
    parser = argparse.ArgumentParser(description='Manage references.json files')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # create
    create_parser = subparsers.add_parser('create', help='Create references.json')
    create_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    create_parser.add_argument('--branch', required=True, help='Git branch name')
    create_parser.add_argument('--issue-url', help='GitHub issue URL')
    create_parser.add_argument('--build-system', help='Build system (maven, gradle, npm)')
    create_parser.add_argument('--domains', help='Comma-separated domain list (e.g., java,documentation)')
    create_parser.set_defaults(func=cmd_create)

    # read
    read_parser = subparsers.add_parser('read', help='Read entire references')
    read_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    read_parser.set_defaults(func=cmd_read)

    # get
    get_parser = subparsers.add_parser('get', help='Get specific field')
    get_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_parser.add_argument('--field', required=True, help='Field name')
    get_parser.set_defaults(func=cmd_get)

    # set
    set_parser = subparsers.add_parser('set', help='Set specific field')
    set_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    set_parser.add_argument('--field', required=True, help='Field name')
    set_parser.add_argument('--value', required=True, help='Field value')
    set_parser.set_defaults(func=cmd_set)

    # add-file
    add_file_parser = subparsers.add_parser('add-file', help='Add file to modified_files')
    add_file_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    add_file_parser.add_argument('--file', required=True, help='File path to add')
    add_file_parser.set_defaults(func=cmd_add_file)

    # remove-file
    remove_file_parser = subparsers.add_parser('remove-file', help='Remove file from modified_files')
    remove_file_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    remove_file_parser.add_argument('--file', required=True, help='File path to remove')
    remove_file_parser.set_defaults(func=cmd_remove_file)

    # add-list
    add_list_parser = subparsers.add_parser('add-list', help='Add multiple values to a list field')
    add_list_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    add_list_parser.add_argument('--field', required=True, help='List field name')
    add_list_parser.add_argument('--values', required=True, help='Comma-separated values to add')
    add_list_parser.set_defaults(func=cmd_add_list)

    # set-list
    set_list_parser = subparsers.add_parser('set-list', help='Set a list field (replaces existing)')
    set_list_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    set_list_parser.add_argument('--field', required=True, help='List field name')
    set_list_parser.add_argument('--values', required=True, help='Comma-separated values')
    set_list_parser.set_defaults(func=cmd_set_list)

    # get-context
    get_context_parser = subparsers.add_parser('get-context', help='Get all references context in one call')
    get_context_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_context_parser.add_argument('--include-files', action='store_true', help='Include full file lists in output')
    get_context_parser.set_defaults(func=cmd_get_context)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
