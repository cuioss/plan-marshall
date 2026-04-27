#!/usr/bin/env python3
"""
Manage lessons learned with global scope.

Stores lessons as markdown files with key=value metadata headers.

Usage:
    python3 manage-lesson.py add --component maven-build --category bug --title "Title"
    python3 manage-lesson.py list --component maven-build
    python3 manage-lesson.py get --lesson-id 2025-12-02-001
    python3 manage-lesson.py convert-to-plan --lesson-id 2025-12-02-001 --plan-id my-plan

The `add` subcommand allocates a fresh lesson file (metadata header + title, empty
body) and returns its absolute path. Callers write the body directly to that path
via the Write tool — there is no alternative API form for inline body content.
"""

import argparse
import json
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

# Direct imports - PYTHONPATH set by executor
from constants import DIR_LESSONS, LESSON_CATEGORIES  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    base_path,
    output_toon,
    parse_markdown_metadata,
    safe_main,
)
from plan_logging import log_entry  # type: ignore[import-not-found]

VALID_CATEGORIES = LESSON_CATEGORIES

# Maximum retry attempts when allocating a fresh lesson id; bounded so that a
# pathological caller cannot wedge the script in an unbounded loop.
MAX_ID_ALLOCATION_RETRIES = 99


def get_lessons_dir() -> Path:
    """Get the lessons-learned directory."""
    return base_path(DIR_LESSONS)


def get_next_id() -> str:
    """Generate the next lesson ID."""
    now = datetime.now().astimezone()
    date = now.strftime('%Y-%m-%d')
    hour = now.strftime('%H')
    prefix = f'{date}-{hour}'
    lessons_dir = get_lessons_dir()

    if not lessons_dir.exists():
        return f'{prefix}-001'

    # Find existing lessons for this hour
    existing = sorted([f.stem for f in lessons_dir.glob(f'{prefix}-*.md')])

    if not existing:
        return f'{prefix}-001'

    # Get the highest sequence number
    last = existing[-1]
    match = re.match(r'\d{4}-\d{2}-\d{2}-\d{2}-(\d+)', last)
    if match:
        seq = int(match.group(1)) + 1
        return f'{prefix}-{seq:03d}'

    return f'{prefix}-001'


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


def _build_lesson_content(metadata: dict, title: str, body: str) -> str:
    """Render a lesson file's content to a string.

    Mirrors the on-disk shape produced by ``write_lesson_to`` /
    ``atomic_write_file`` (metadata header, blank line, ``# title``, blank line,
    body, terminating newline) so callers using exclusive create can write the
    same bytes without going through the atomic temp-file path.
    """
    lines = [f'{key}={value}' for key, value in metadata.items()]
    lines.append('')
    lines.append(f'# {title}')
    lines.append('')
    lines.append(body)
    rendered = '\n'.join(lines)
    if not rendered.endswith('\n'):
        rendered += '\n'
    return rendered


def _next_sequential_id(current_id: str) -> str:
    """Return the next id by incrementing the trailing 3-digit sequence.

    The lesson id format is ``YYYY-MM-DD-HH-NNN`` (see ``get_next_id``). The
    helper bumps ``NNN`` by one and re-zero-pads, leaving the rest of the id
    untouched. Used by ``_allocate_and_write_scaffold`` to walk past collisions
    deterministically rather than rolling the clock forward.
    """
    match = re.match(r'^(\d{4}-\d{2}-\d{2}-\d{2})-(\d+)$', current_id)
    if not match:
        # Fall back to ``get_next_id`` semantics: same prefix, seq=001.
        return f'{current_id}-001'
    prefix, seq = match.group(1), int(match.group(2))
    return f'{prefix}-{seq + 1:03d}'


def _allocate_and_write_scaffold(
    metadata_factory: Callable[[str], dict], title: str, body: str = ''
) -> dict:
    """Allocate a fresh lesson id and exclusively create its file.

    Uses ``open(path, 'x')`` (kernel-enforced O_CREAT|O_EXCL) so a concurrent
    or stale-cache caller can never silently overwrite an existing lesson.
    On ``FileExistsError`` the helper logs a WARN to ``script-execution.log``
    and retries with the next sequential id, up to
    ``MAX_ID_ALLOCATION_RETRIES`` (99) attempts. Exhaustion returns an error
    dict ``{'status': 'error', 'error': 'id_exhausted', ...}``.

    Args:
        metadata_factory: Callable that takes the candidate ``lesson_id`` and
            returns the metadata dict to embed in the file header. Called
            fresh on every retry so the embedded ``id`` field stays in sync
            with the path.
        title: Markdown ``# title`` line for the scaffold.
        body: Initial body content (may be empty for ``cmd_add``).

    Returns:
        On success: ``{'status': 'success', 'id': lesson_id, 'path': Path,
        'metadata': metadata}``.
        On exhaustion: ``{'status': 'error', 'error': 'id_exhausted', ...}``.
    """
    lessons_dir = get_lessons_dir()
    lessons_dir.mkdir(parents=True, exist_ok=True)

    lesson_id = get_next_id()

    for _ in range(MAX_ID_ALLOCATION_RETRIES):
        metadata = metadata_factory(lesson_id)
        content = _build_lesson_content(metadata, title, body)
        path = lessons_dir / f'{lesson_id}.md'

        try:
            with open(path, 'x', encoding='utf-8') as f:
                f.write(content)
        except FileExistsError:
            # ``manage-lessons`` is a global script with no plan context, so the
            # WARNING line lands in the date-suffixed global script-execution log.
            # The ``'global'`` sentinel matches the convention used by other
            # global callers (build-python/build-npm/manage-architecture).
            log_entry(
                'script',
                'global',
                'WARNING',
                f'(plan-marshall:manage-lessons) id_collision at {path} — retrying with seq+1',
            )
            lesson_id = _next_sequential_id(lesson_id)
            continue

        return {
            'status': 'success',
            'id': lesson_id,
            'path': path,
            'metadata': metadata,
        }

    return {
        'status': 'error',
        'error': 'id_exhausted',
        'message': (
            f'Could not allocate a unique lesson id after {MAX_ID_ALLOCATION_RETRIES} '
            'attempts; the lessons directory likely contains a colliding file or a '
            'corrupted id sequence.'
        ),
    }


def cmd_add(args: argparse.Namespace) -> dict:
    """Allocate a new lesson file with metadata header and title (empty body).

    Returns the absolute path of the created file. The caller writes the body
    directly to that path via the Write tool — there is no inline body API.
    """
    if args.category not in VALID_CATEGORIES:
        return {
            'status': 'error',
            'error': 'invalid_category',
            'message': f'Invalid category: {args.category}',
            'valid_categories': VALID_CATEGORIES,
        }

    today = datetime.now(UTC).strftime('%Y-%m-%d')

    def _metadata(lesson_id: str) -> dict:
        metadata = {
            'id': lesson_id,
            'component': args.component,
            'category': args.category,
            'created': today,
        }
        if args.bundle:
            metadata['bundle'] = args.bundle
        return metadata

    allocation = _allocate_and_write_scaffold(_metadata, args.title, '')
    if allocation['status'] != 'success':
        return allocation

    return {
        'status': 'success',
        'id': allocation['id'],
        'path': str(allocation['path'].resolve()),
        'component': args.component,
        'category': args.category,
    }


def cmd_update(args: argparse.Namespace) -> dict:
    """Update lesson metadata."""
    metadata, title, body = read_lesson(args.lesson_id)

    if not metadata:
        return {'status': 'error', 'id': args.lesson_id, 'error': 'not_found', 'message': f'Lesson {args.lesson_id} not found'}

    # Determine which field to update
    field = None
    value = None
    previous = None

    if args.component:
        field = 'component'
        previous = metadata.get('component')
        value = args.component
        metadata['component'] = value
    elif args.category:
        if args.category not in VALID_CATEGORIES:
            return {
                'status': 'error',
                'error': 'invalid_category',
                'message': f'Invalid category: {args.category}',
                'valid_categories': VALID_CATEGORIES,
            }
        field = 'category'
        previous = metadata.get('category')
        value = args.category
        metadata['category'] = value

    if not field:
        return {'status': 'error', 'error': 'no_update', 'message': 'No field to update specified'}

    write_lesson(args.lesson_id, metadata, title, body)

    return {'status': 'success', 'id': args.lesson_id, 'field': field, 'value': value, 'previous': previous}


def cmd_get(args: argparse.Namespace) -> dict:
    """Get a single lesson."""
    metadata, title, body = read_lesson(args.lesson_id)

    if not metadata:
        return {'status': 'error', 'id': args.lesson_id, 'error': 'not_found', 'message': f'Lesson {args.lesson_id} not found'}

    result = {
        'status': 'success',
        'id': metadata.get('id', args.lesson_id),
        'component': metadata.get('component', ''),
        'category': metadata.get('category', ''),
        'created': metadata.get('created', ''),
        'title': title,
    }

    if body:
        result['content'] = body

    return result


def cmd_list(args: argparse.Namespace) -> dict:
    """List lessons with filtering."""
    lessons_dir = get_lessons_dir()

    if not lessons_dir.exists():
        return {'status': 'success', 'total': 0, 'filtered': 0, 'lessons': []}

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

        # Get title
        title = ''
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break

        entry = {
            'id': metadata.get('id', path.stem),
            'component': metadata.get('component', ''),
            'category': metadata.get('category', ''),
            'title': title,
        }

        if args.full:
            body_start = 0
            for i, line in enumerate(content.split('\n')):
                if line.startswith('# '):
                    body_start = i + 1
                    break
            entry['content'] = '\n'.join(content.split('\n')[body_start:]).strip()

        lessons.append(entry)

    return {'status': 'success', 'total': total, 'filtered': len(lessons), 'lessons': lessons}


def cmd_convert_to_plan(args: argparse.Namespace) -> dict:
    """Move a lesson file from the global lessons directory into a plan directory.

    The lesson is renamed to lesson-{id}.md inside .plan/local/plans/{plan_id}/.
    Errors if the source lesson does not exist.
    """
    if any(sep in args.lesson_id for sep in ('/', '\\', '..')) or any(
        sep in args.plan_id for sep in ('/', '\\', '..')
    ):
        return {
            'status': 'error',
            'error': 'invalid_id',
            'message': 'Identifiers must not contain path separators or traversal sequences',
        }

    lessons_dir = get_lessons_dir().resolve()
    source = (lessons_dir / f'{args.lesson_id}.md').resolve()
    plan_parent = base_path('plans').resolve()
    plan_dir = (plan_parent / args.plan_id).resolve()

    if source.parent != lessons_dir or plan_dir.parent != plan_parent:
        return {
            'status': 'error',
            'error': 'path_traversal',
            'message': 'Resolved path escapes intended parent directory',
        }

    if not source.exists():
        return {
            'status': 'error',
            'id': args.lesson_id,
            'error': 'not_found',
            'message': f'Lesson {args.lesson_id} not found',
        }

    plan_dir.mkdir(parents=True, exist_ok=True)
    destination = plan_dir / f'lesson-{args.lesson_id}.md'

    shutil.move(source, destination)

    return {
        'status': 'success',
        'lesson_id': args.lesson_id,
        'plan_id': args.plan_id,
        'source': str(source),
        'destination': str(destination),
    }


def cmd_from_error(args: argparse.Namespace) -> dict:
    """Create lesson from error context."""
    try:
        context = json.loads(args.context)
    except json.JSONDecodeError:
        return {'status': 'error', 'error': 'invalid_json', 'message': 'Context must be valid JSON'}

    component = context.get('component', 'unknown')
    error = context.get('error', 'Unknown error')
    solution = context.get('solution', '')

    today = datetime.now(UTC).strftime('%Y-%m-%d')

    def _metadata(lesson_id: str) -> dict:
        return {'id': lesson_id, 'component': component, 'category': 'bug', 'created': today}

    title = f'Error: {error[:50]}'
    body = f'## Error\n\n{error}\n\n'
    if solution:
        body += f'## Solution\n\n{solution}\n'

    allocation = _allocate_and_write_scaffold(_metadata, title, body)
    if allocation['status'] != 'success':
        return allocation

    return {'status': 'success', 'id': allocation['id'], 'created_from': 'error_context'}


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Manage lessons learned', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # add
    add_parser = subparsers.add_parser(
        'add',
        help='Allocate a new lesson file (metadata + title, empty body) and return its absolute path',
        allow_abbrev=False,
    )
    add_parser.add_argument('--component', required=True, help='Component name')
    add_parser.add_argument(
        '--category', required=True, choices=['bug', 'improvement', 'anti-pattern'], help='Lesson category'
    )
    add_parser.add_argument('--title', required=True, help='Lesson title')
    add_parser.add_argument('--bundle', help='Optional bundle reference')
    add_parser.set_defaults(func=cmd_add)

    # update
    update_parser = subparsers.add_parser('update', help='Update lesson', allow_abbrev=False)
    update_parser.add_argument('--lesson-id', required=True, help='Lesson ID')
    update_parser.add_argument('--component', help='Update component')
    update_parser.add_argument('--category', choices=['bug', 'improvement', 'anti-pattern'], help='Update category')
    update_parser.set_defaults(func=cmd_update)

    # get
    get_parser = subparsers.add_parser('get', help='Get single lesson', allow_abbrev=False)
    get_parser.add_argument('--lesson-id', required=True, help='Lesson ID')
    get_parser.set_defaults(func=cmd_get)

    # list
    list_parser = subparsers.add_parser('list', help='List lessons', allow_abbrev=False)
    list_parser.add_argument('--component', help='Filter by component')
    list_parser.add_argument('--category', choices=['bug', 'improvement', 'anti-pattern'], help='Filter by category')
    list_parser.add_argument('--full', action='store_true', help='Include full lesson body content')
    list_parser.set_defaults(func=cmd_list)

    # convert-to-plan
    convert_parser = subparsers.add_parser(
        'convert-to-plan',
        help='Move a lesson file into a plan directory as lesson-{id}.md',
        allow_abbrev=False,
    )
    convert_parser.add_argument('--lesson-id', required=True, help='Lesson ID')
    convert_parser.add_argument('--plan-id', required=True, help='Target plan ID')
    convert_parser.set_defaults(func=cmd_convert_to_plan)

    # from-error
    from_error_parser = subparsers.add_parser(
        'from-error', help='Create from error context', allow_abbrev=False
    )
    from_error_parser.add_argument('--context', required=True, help='JSON error context')
    from_error_parser.set_defaults(func=cmd_from_error)

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
