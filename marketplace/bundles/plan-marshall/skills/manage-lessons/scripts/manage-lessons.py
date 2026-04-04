#!/usr/bin/env python3
"""
Manage lessons learned with global scope.

Stores lessons as markdown files with key=value metadata headers.

Usage:
    python3 manage-lesson.py add --component maven-build --category bug --title "Title" --detail "..."
    python3 manage-lesson.py list --component maven-build
    python3 manage-lesson.py get --id 2025-12-02-001
    python3 manage-lesson.py update --id 2025-12-02-001 --applied true
    python3 manage-lesson.py archive --id 2025-12-02-001
"""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

# Direct imports - PYTHONPATH set by executor
from constants import DIR_ARCHIVED_LESSONS, DIR_LESSONS, LESSON_CATEGORIES  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    base_path,
    output_toon,
    parse_markdown_metadata,
    safe_main,
)

VALID_CATEGORIES = LESSON_CATEGORIES


def get_lessons_dir() -> Path:
    """Get the lessons-learned directory."""
    return base_path(DIR_LESSONS)


def get_next_id() -> str:
    """Generate the next lesson ID."""
    today = datetime.now(UTC).strftime('%Y-%m-%d')
    lessons_dir = get_lessons_dir()

    if not lessons_dir.exists():
        return f'{today}-001'

    # Find existing lessons for today
    existing = sorted([f.stem for f in lessons_dir.glob(f'{today}-*.md')])

    if not existing:
        return f'{today}-001'

    # Get the highest sequence number
    last = existing[-1]
    match = re.match(r'\d{4}-\d{2}-\d{2}-(\d+)', last)
    if match:
        seq = int(match.group(1)) + 1
        return f'{today}-{seq:03d}'

    return f'{today}-001'


def read_lesson(lesson_id: str) -> tuple[dict, str, str]:
    """Read a lesson file and return (metadata, title, body)."""
    lessons_dir = get_lessons_dir()
    path = lessons_dir / f'{lesson_id}.md'

    if not path.exists():
        return {}, '', ''

    content = path.read_text(encoding='utf-8')
    metadata = parse_markdown_metadata(content)

    # Extract title and body
    lines = content.split('\n')
    title = ''
    body_start = 0

    for i, line in enumerate(lines):
        if line.startswith('# '):
            title = line[2:].strip()
            body_start = i + 1
            break

    body = '\n'.join(lines[body_start:]).strip()

    return metadata, title, body


def write_lesson(lesson_id: str, metadata: dict, title: str, body: str) -> None:
    """Write a lesson file to the lessons directory."""
    lessons_dir = get_lessons_dir()
    lessons_dir.mkdir(parents=True, exist_ok=True)
    write_lesson_to(lessons_dir / f'{lesson_id}.md', metadata, title, body)


def write_lesson_to(path: Path, metadata: dict, title: str, body: str) -> None:
    """Write a lesson file to a specific path."""
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for key, value in metadata.items():
        lines.append(f'{key}={value}')

    lines.append('')
    lines.append(f'# {title}')
    lines.append('')
    lines.append(body)

    atomic_write_file(path, '\n'.join(lines))


def cmd_add(args: argparse.Namespace) -> int:
    """Create a new lesson."""
    if args.category not in VALID_CATEGORIES:
        output_toon(
            {
                'status': 'error',
                'error': 'invalid_category',
                'message': f'Invalid category: {args.category}',
                'valid_categories': VALID_CATEGORIES,
            }
        )
        return 1

    lesson_id = get_next_id()
    today = datetime.now(UTC).strftime('%Y-%m-%d')

    metadata = {
        'id': lesson_id,
        'component': args.component,
        'category': args.category,
        'applied': 'false',
        'created': today,
    }

    if args.bundle:
        metadata['bundle'] = args.bundle

    write_lesson(lesson_id, metadata, args.title, args.detail)

    output_toon(
        {
            'status': 'success',
            'id': lesson_id,
            'file': f'{lesson_id}.md',
            'component': args.component,
            'category': args.category,
        }
    )
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Update lesson metadata."""
    metadata, title, body = read_lesson(args.id)

    if not metadata:
        output_toon({'status': 'error', 'id': args.id, 'error': 'not_found', 'message': f'Lesson {args.id} not found'})
        return 1

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
            output_toon(
                {
                    'status': 'error',
                    'error': 'invalid_category',
                    'message': f'Invalid category: {args.category}',
                    'valid_categories': VALID_CATEGORIES,
                }
            )
            return 1
        field = 'category'
        previous = metadata.get('category')
        value = args.category
        metadata['category'] = value

    if not field:
        output_toon({'status': 'error', 'error': 'no_update', 'message': 'No field to update specified'})
        return 1

    write_lesson(args.id, metadata, title, body)

    output_toon({'status': 'success', 'id': args.id, 'field': field, 'value': value, 'previous': previous})
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    """Get a single lesson."""
    metadata, title, body = read_lesson(args.id)

    if not metadata:
        output_toon({'status': 'error', 'id': args.id, 'error': 'not_found', 'message': f'Lesson {args.id} not found'})
        return 1

    result = {
        'status': 'success',
        'id': metadata.get('id', args.id),
        'component': metadata.get('component', ''),
        'category': metadata.get('category', ''),
        'applied': metadata.get('applied', 'false'),
        'created': metadata.get('created', ''),
        'title': title,
    }

    if body:
        result['content'] = body

    output_toon(result)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List lessons with filtering."""
    lessons_dir = get_lessons_dir()

    if not lessons_dir.exists():
        output_toon({'status': 'success', 'total': 0, 'filtered': 0, 'lessons': []})
        return 0

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
        title = ''
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break

        lessons.append(
            {
                'id': metadata.get('id', path.stem),
                'component': metadata.get('component', ''),
                'category': metadata.get('category', ''),
                'applied': metadata.get('applied', 'false'),
                'title': title,
            }
        )

    output_toon({'status': 'success', 'total': total, 'filtered': len(lessons), 'lessons': lessons})
    return 0


def get_archived_dir() -> Path:
    """Get the archived-lessons directory."""
    return base_path(DIR_ARCHIVED_LESSONS)


def cmd_archive(args: argparse.Namespace) -> int:
    """Archive a lesson: set applied=true and move to archived-lessons."""
    metadata, title, body = read_lesson(args.id)

    if not metadata:
        output_toon({'status': 'error', 'id': args.id, 'error': 'not_found', 'message': f'Lesson {args.id} not found'})
        return 1

    lessons_dir = get_lessons_dir()
    archived_dir = get_archived_dir()
    archived_dir.mkdir(parents=True, exist_ok=True)

    src = lessons_dir / f'{args.id}.md'
    dst = archived_dir / f'{args.id}.md'

    # Update applied status
    metadata['applied'] = 'true' if args.applied else 'false'

    # Write to archived location
    write_lesson_to(dst, metadata, title, body)

    # Remove original
    src.unlink()

    output_toon({'status': 'success', 'id': args.id, 'archived_to': str(dst)})
    return 0


def cmd_from_error(args: argparse.Namespace) -> int:
    """Create lesson from error context."""
    try:
        context = json.loads(args.context)
    except json.JSONDecodeError:
        output_toon({'status': 'error', 'error': 'invalid_json', 'message': 'Context must be valid JSON'})
        return 1

    component = context.get('component', 'unknown')
    error = context.get('error', 'Unknown error')
    solution = context.get('solution', '')

    lesson_id = get_next_id()
    today = datetime.now(UTC).strftime('%Y-%m-%d')

    metadata = {'id': lesson_id, 'component': component, 'category': 'bug', 'applied': 'false', 'created': today}

    title = f'Error: {error[:50]}'
    body = f'## Error\n\n{error}\n\n'
    if solution:
        body += f'## Solution\n\n{solution}\n'

    write_lesson(lesson_id, metadata, title, body)

    output_toon({'status': 'success', 'id': lesson_id, 'created_from': 'error_context'})
    return 0


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Manage lessons learned')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # add
    add_parser = subparsers.add_parser('add', help='Create new lesson')
    add_parser.add_argument('--component', required=True, help='Component name')
    add_parser.add_argument(
        '--category', required=True, choices=['bug', 'improvement', 'anti-pattern'], help='Lesson category'
    )
    add_parser.add_argument('--title', required=True, help='Lesson title')
    add_parser.add_argument('--detail', required=True, help='Lesson detail')
    add_parser.add_argument('--bundle', help='Optional bundle reference')
    add_parser.set_defaults(func=cmd_add)

    # update
    update_parser = subparsers.add_parser('update', help='Update lesson')
    update_parser.add_argument('--id', required=True, help='Lesson ID')
    update_parser.add_argument('--applied', type=lambda x: x.lower() == 'true', help='Set applied status')
    update_parser.add_argument('--component', help='Update component')
    update_parser.add_argument('--category', choices=['bug', 'improvement', 'anti-pattern'], help='Update category')
    update_parser.set_defaults(func=cmd_update)

    # get
    get_parser = subparsers.add_parser('get', help='Get single lesson')
    get_parser.add_argument('--id', required=True, help='Lesson ID')
    get_parser.set_defaults(func=cmd_get)

    # list
    list_parser = subparsers.add_parser('list', help='List lessons')
    list_parser.add_argument('--component', help='Filter by component')
    list_parser.add_argument('--category', choices=['bug', 'improvement', 'anti-pattern'], help='Filter by category')
    list_parser.add_argument('--applied', type=lambda x: x.lower() == 'true', help='Filter by applied status')
    list_parser.set_defaults(func=cmd_list)

    # archive
    archive_parser = subparsers.add_parser('archive', help='Archive a lesson (set applied status and move)')
    archive_parser.add_argument('--id', required=True, help='Lesson ID')
    archive_parser.add_argument(
        '--applied', type=lambda x: x.lower() == 'true', default=True, help='Set applied status (default: true)'
    )
    archive_parser.set_defaults(func=cmd_archive)

    # from-error
    from_error_parser = subparsers.add_parser('from-error', help='Create from error context')
    from_error_parser.add_argument('--context', required=True, help='JSON error context')
    from_error_parser.set_defaults(func=cmd_from_error)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    main()
