#!/usr/bin/env python3
"""
Manage lessons learned with global scope.

Stores lessons as markdown files with key=value metadata headers.

Usage:
    python3 manage-lesson.py add --component maven-build --category bug --title "Title" --detail "..."
    python3 manage-lesson.py list --component maven-build
    python3 manage-lesson.py get --id 2025-12-02-001
    python3 manage-lesson.py update --id 2025-12-02-001 --applied true
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Direct imports - PYTHONPATH set by executor
from file_ops import atomic_write_file, base_path, parse_markdown_metadata  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

VALID_CATEGORIES = ['bug', 'improvement', 'anti-pattern']


def get_lessons_dir() -> Path:
    """Get the lessons-learned directory."""
    return base_path('lessons-learned')


def get_next_id() -> str:
    """Generate the next lesson ID."""
    today = datetime.utcnow().strftime('%Y-%m-%d')
    lessons_dir = get_lessons_dir()

    if not lessons_dir.exists():
        return f"{today}-001"

    # Find existing lessons for today
    existing = sorted([
        f.stem for f in lessons_dir.glob(f"{today}-*.md")
    ])

    if not existing:
        return f"{today}-001"

    # Get the highest sequence number
    last = existing[-1]
    match = re.match(r'\d{4}-\d{2}-\d{2}-(\d+)', last)
    if match:
        seq = int(match.group(1)) + 1
        return f"{today}-{seq:03d}"

    return f"{today}-001"


def read_lesson(lesson_id: str) -> tuple[dict, str]:
    """Read a lesson file and return (metadata, content)."""
    lessons_dir = get_lessons_dir()
    path = lessons_dir / f"{lesson_id}.md"

    if not path.exists():
        return {}, ""

    content = path.read_text(encoding='utf-8')
    metadata = parse_markdown_metadata(content)

    # Extract title and body
    lines = content.split('\n')
    body_start = 0

    for i, line in enumerate(lines):
        if line.startswith('# '):
            body_start = i + 1
            break

    body = '\n'.join(lines[body_start:]).strip()

    return metadata, body


def write_lesson(lesson_id: str, metadata: dict, title: str, body: str):
    """Write a lesson file."""
    lessons_dir = get_lessons_dir()
    lessons_dir.mkdir(parents=True, exist_ok=True)

    path = lessons_dir / f"{lesson_id}.md"

    # Build content
    lines = []
    for key, value in metadata.items():
        lines.append(f"{key}={value}")

    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(body)

    atomic_write_file(path, '\n'.join(lines))


def output_toon(data: dict):
    """Output TOON format to stdout."""
    print(serialize_toon(data))


def cmd_add(args):
    """Create a new lesson."""
    if args.category not in VALID_CATEGORIES:
        output_toon({
            'status': 'error',
            'error': 'invalid_category',
            'message': f"Invalid category: {args.category}",
            'valid_categories': VALID_CATEGORIES
        })
        sys.exit(1)

    lesson_id = get_next_id()
    today = datetime.utcnow().strftime('%Y-%m-%d')

    metadata = {
        'id': lesson_id,
        'component': args.component,
        'category': args.category,
        'applied': 'false',
        'created': today
    }

    if args.bundle:
        metadata['bundle'] = args.bundle

    write_lesson(lesson_id, metadata, args.title, args.detail)

    output_toon({
        'status': 'success',
        'id': lesson_id,
        'file': f"{lesson_id}.md",
        'component': args.component,
        'category': args.category
    })


def cmd_update(args):
    """Update lesson metadata."""
    metadata, body = read_lesson(args.id)

    if not metadata:
        output_toon({
            'status': 'error',
            'id': args.id,
            'error': 'not_found',
            'message': f"Lesson {args.id} not found"
        })
        sys.exit(1)

    # Determine which field to update
    field = None
    value = None
    previous = None

    if args.applied is not None:
        field = 'applied'
        previous = metadata.get('applied')
        value = 'true' if args.applied else 'false'
        metadata['applied'] = value
    elif args.component:
        field = 'component'
        previous = metadata.get('component')
        value = args.component
        metadata['component'] = value
    elif args.category:
        if args.category not in VALID_CATEGORIES:
            output_toon({
                'status': 'error',
                'error': 'invalid_category',
                'message': f"Invalid category: {args.category}",
                'valid_categories': VALID_CATEGORIES
            })
            sys.exit(1)
        field = 'category'
        previous = metadata.get('category')
        value = args.category
        metadata['category'] = value

    if not field:
        output_toon({
            'status': 'error',
            'error': 'no_update',
            'message': 'No field to update specified'
        })
        sys.exit(1)

    # Get title from content
    lessons_dir = get_lessons_dir()
    path = lessons_dir / f"{args.id}.md"
    content = path.read_text(encoding='utf-8')

    title = ""
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line[2:].strip()
            break

    write_lesson(args.id, metadata, title, body)

    output_toon({
        'status': 'success',
        'id': args.id,
        'field': field,
        'value': value,
        'previous': previous
    })


def cmd_get(args):
    """Get a single lesson."""
    metadata, body = read_lesson(args.id)

    if not metadata:
        output_toon({
            'status': 'error',
            'id': args.id,
            'error': 'not_found',
            'message': f"Lesson {args.id} not found"
        })
        sys.exit(1)

    # Get title from content
    lessons_dir = get_lessons_dir()
    path = lessons_dir / f"{args.id}.md"
    content = path.read_text(encoding='utf-8')

    title = ""
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line[2:].strip()
            break

    result = {
        'status': 'success',
        'id': metadata.get('id', args.id),
        'component': metadata.get('component', ''),
        'category': metadata.get('category', ''),
        'applied': metadata.get('applied', 'false'),
        'created': metadata.get('created', ''),
        'title': title
    }

    if body:
        result['content'] = body

    output_toon(result)


def cmd_list(args):
    """List lessons with filtering."""
    lessons_dir = get_lessons_dir()

    if not lessons_dir.exists():
        output_toon({
            'status': 'success',
            'total': 0,
            'filtered': 0,
            'lessons': []
        })
        return

    lessons = []
    total = 0

    for path in sorted(lessons_dir.glob('*.md')):
        total += 1
        content = path.read_text(encoding='utf-8')
        metadata = parse_markdown_metadata(content)

        # Apply filters
        if args.component and metadata.get('component') != args.component:
            continue
        if args.category and metadata.get('category') != args.category:
            continue
        if args.applied is not None:
            applied_val = 'true' if args.applied else 'false'
            if metadata.get('applied') != applied_val:
                continue

        # Get title
        title = ""
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break

        lessons.append({
            'id': metadata.get('id', path.stem),
            'component': metadata.get('component', ''),
            'category': metadata.get('category', ''),
            'applied': metadata.get('applied', 'false'),
            'title': title
        })

    output_toon({
        'status': 'success',
        'total': total,
        'filtered': len(lessons),
        'lessons': lessons
    })


def cmd_from_error(args):
    """Create lesson from error context."""
    try:
        context = json.loads(args.context)
    except json.JSONDecodeError:
        output_toon({
            'status': 'error',
            'error': 'invalid_json',
            'message': 'Context must be valid JSON'
        })
        sys.exit(1)

    component = context.get('component', 'unknown')
    error = context.get('error', 'Unknown error')
    solution = context.get('solution', '')

    lesson_id = get_next_id()
    today = datetime.utcnow().strftime('%Y-%m-%d')

    metadata = {
        'id': lesson_id,
        'component': component,
        'category': 'bug',
        'applied': 'false',
        'created': today
    }

    title = f"Error: {error[:50]}"
    body = f"## Error\n\n{error}\n\n"
    if solution:
        body += f"## Solution\n\n{solution}\n"

    write_lesson(lesson_id, metadata, title, body)

    output_toon({
        'status': 'success',
        'id': lesson_id,
        'created_from': 'error_context'
    })


def main():
    parser = argparse.ArgumentParser(
        description='Manage lessons learned'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # add
    add_parser = subparsers.add_parser('add', help='Create new lesson')
    add_parser.add_argument('--component', required=True, help='Component name')
    add_parser.add_argument('--category', required=True,
                           choices=['bug', 'improvement', 'anti-pattern'],
                           help='Lesson category')
    add_parser.add_argument('--title', required=True, help='Lesson title')
    add_parser.add_argument('--detail', required=True, help='Lesson detail')
    add_parser.add_argument('--bundle', help='Optional bundle reference')
    add_parser.set_defaults(func=cmd_add)

    # update
    update_parser = subparsers.add_parser('update', help='Update lesson')
    update_parser.add_argument('--id', required=True, help='Lesson ID')
    update_parser.add_argument('--applied', type=lambda x: x.lower() == 'true',
                               help='Set applied status')
    update_parser.add_argument('--component', help='Update component')
    update_parser.add_argument('--category',
                               choices=['bug', 'improvement', 'anti-pattern'],
                               help='Update category')
    update_parser.set_defaults(func=cmd_update)

    # get
    get_parser = subparsers.add_parser('get', help='Get single lesson')
    get_parser.add_argument('--id', required=True, help='Lesson ID')
    get_parser.set_defaults(func=cmd_get)

    # list
    list_parser = subparsers.add_parser('list', help='List lessons')
    list_parser.add_argument('--component', help='Filter by component')
    list_parser.add_argument('--category',
                            choices=['bug', 'improvement', 'anti-pattern'],
                            help='Filter by category')
    list_parser.add_argument('--applied', type=lambda x: x.lower() == 'true',
                            help='Filter by applied status')
    list_parser.set_defaults(func=cmd_list)

    # from-error
    from_error_parser = subparsers.add_parser('from-error', help='Create from error context')
    from_error_parser.add_argument('--context', required=True, help='JSON error context')
    from_error_parser.set_defaults(func=cmd_from_error)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
