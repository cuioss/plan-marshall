#!/usr/bin/env python3
"""
Manage references.toon files with field-level access and list management.

Tracks files, branches, and external references for a plan.

Usage:
    python3 manage-references.py create --plan-id my-plan --branch feature/x
    python3 manage-references.py read --plan-id my-plan
    python3 manage-references.py get --plan-id my-plan --field branch
    python3 manage-references.py set --plan-id my-plan --field branch --value feature/x
    python3 manage-references.py add-file --plan-id my-plan --file src/Main.java
"""

import argparse
import re
import sys

from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def get_references_path(plan_id: str) -> Path:
    """Get the references.toon file path."""
    return base_path('plans', plan_id, 'references.toon')


def read_references(plan_id: str) -> dict:
    """Read references.toon for a plan."""
    path = get_references_path(plan_id)
    if not path.exists():
        return {}
    return parse_toon(path.read_text(encoding='utf-8'))


def write_references(plan_id: str, refs: dict):
    """Write references.toon for a plan."""
    path = get_references_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "# Plan References\n\n" + serialize_toon(refs)
    atomic_write_file(path, content)


def output_toon(data: dict):
    """Output TOON format to stdout."""
    print(serialize_toon(data))


def cmd_create(args):
    """Create references.toon with basic fields."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    path = get_references_path(args.plan_id)
    if path.exists():
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'already_exists',
            'message': 'references.toon already exists'
        })
        sys.exit(1)

    # Build base references
    refs = {
        'branch': args.branch,
        'base_branch': 'main',
        'modified_files': [],
        'config_files': [],
        'test_files': []
    }

    # Add optional fields
    if args.issue_url:
        refs['issue_url'] = args.issue_url
    if args.build_system:
        refs['build_system'] = args.build_system

    write_references(args.plan_id, refs)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'file': 'references.toon',
        'created': True,
        'fields': list(refs.keys())
    })


def cmd_read(args):
    """Read entire references.toon."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    refs = read_references(args.plan_id)
    if not refs:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'references.toon not found'
        })
        sys.exit(1)

    # Summarize lists
    summary = {}
    for key, value in refs.items():
        if isinstance(value, list):
            summary[key] = f"{len(value)} items"
        else:
            summary[key] = value

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'references': summary
    })


def cmd_get(args):
    """Get a specific field value."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    refs = read_references(args.plan_id)
    if not refs:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'references.toon not found'
        })
        sys.exit(1)

    value = refs.get(args.field)
    if value is None:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'field': args.field,
            'error': 'field_not_found',
            'message': f"Field '{args.field}' not found"
        })
        sys.exit(1)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'field': args.field,
        'value': value
    })


def cmd_set(args):
    """Set a specific field value."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    refs = read_references(args.plan_id)
    previous = refs.get(args.field)
    refs[args.field] = args.value
    write_references(args.plan_id, refs)

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'field': args.field,
        'value': args.value
    }
    if previous is not None:
        result['previous'] = previous
    output_toon(result)


def cmd_add_file(args):
    """Add a file to modified_files list."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    refs = read_references(args.plan_id)
    if 'modified_files' not in refs:
        refs['modified_files'] = []

    if args.file not in refs['modified_files']:
        refs['modified_files'].append(args.file)
        write_references(args.plan_id, refs)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'section': 'modified_files',
        'added': args.file,
        'total': len(refs['modified_files'])
    })


def cmd_remove_file(args):
    """Remove a file from modified_files list."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    refs = read_references(args.plan_id)
    if 'modified_files' not in refs or args.file not in refs['modified_files']:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'not_found',
            'message': f"File '{args.file}' not in modified_files"
        })
        sys.exit(1)

    refs['modified_files'].remove(args.file)
    write_references(args.plan_id, refs)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'section': 'modified_files',
        'removed': args.file,
        'total': len(refs['modified_files'])
    })


def cmd_get_context(args):
    """Get all references context in one call."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    refs = read_references(args.plan_id)
    if not refs:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'references.toon not found'
        })
        sys.exit(1)

    # Build comprehensive context
    context = {
        'status': 'success',
        'plan_id': args.plan_id,
        'branch': refs.get('branch', ''),
        'base_branch': refs.get('base_branch', 'main'),
        'modified_files_count': len(refs.get('modified_files', [])),
        'config_files_count': len(refs.get('config_files', [])),
        'test_files_count': len(refs.get('test_files', []))
    }

    # Include optional fields if present
    if refs.get('issue_url'):
        context['issue_url'] = refs['issue_url']
    if refs.get('build_system'):
        context['build_system'] = refs['build_system']

    # Include file lists if requested
    if args.include_files:
        context['modified_files'] = refs.get('modified_files', [])
        context['config_files'] = refs.get('config_files', [])
        context['test_files'] = refs.get('test_files', [])

    output_toon(context)


def main():
    parser = argparse.ArgumentParser(
        description='Manage references.toon files'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # create
    create_parser = subparsers.add_parser('create', help='Create references.toon')
    create_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    create_parser.add_argument('--branch', required=True, help='Git branch name')
    create_parser.add_argument('--issue-url', help='GitHub issue URL')
    create_parser.add_argument('--build-system', help='Build system (maven, gradle, npm)')
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

    # get-context
    get_context_parser = subparsers.add_parser('get-context',
        help='Get all references context in one call')
    get_context_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_context_parser.add_argument('--include-files', action='store_true',
        help='Include full file lists in output')
    get_context_parser.set_defaults(func=cmd_get_context)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
