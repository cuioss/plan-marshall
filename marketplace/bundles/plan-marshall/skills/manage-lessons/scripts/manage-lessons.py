#!/usr/bin/env python3
"""
Manage lessons learned with global scope.

Stores lessons as markdown files with key=value metadata headers.

Usage:
    python3 manage-lesson.py add --component maven-build --category bug --title "Title"
    python3 manage-lesson.py list --component maven-build
    python3 manage-lesson.py get --lesson-id 2025-12-02-001
    python3 manage-lesson.py set-body --lesson-id 2025-12-02-001 --file body.md
    python3 manage-lesson.py set-title --lesson-id 2025-12-02-001 --title "New Title"
    python3 manage-lesson.py remove --lesson-id 2025-12-02-001 --reason "duplicate"
    python3 manage-lesson.py supersede --lesson-id 2025-12-02-001 \\
        --by 2025-12-03-001 --reason "merged into canonical"
    python3 manage-lesson.py convert-to-plan --lesson-id 2025-12-02-001 --plan-id my-plan

The `add` subcommand allocates a fresh lesson file (metadata header + title, empty
body) and returns its absolute path. Callers write the body directly to that path
via the Write tool — there is no alternative API form for inline body content.

The `remove` and `supersede` subcommands delete or redirect a lesson and write a
tombstone JSON file at ``.plan/local/lessons-learned/.tombstones/{lesson-id}.json``
so historical references resolve by id even after the source file is gone.
"""

import argparse
import json
import re
import shutil
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

# Direct imports - PYTHONPATH set by executor
from _cmd_auto_suggest import cmd_auto_suggest
from _lessons_crud import set_body  # type: ignore[import-not-found]
from constants import DIR_LESSONS, LESSON_CATEGORIES  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    base_path,
    get_marshal_path,
    output_toon,
    parse_markdown_metadata,
    safe_main,
)
from input_validation import (  # type: ignore[import-not-found]
    add_component_arg,
    add_lesson_id_arg,
    add_plan_id_arg,
    parse_args_with_toon_errors,
    validate_lesson_id,
)
from plan_logging import log_entry  # type: ignore[import-not-found]

VALID_CATEGORIES = LESSON_CATEGORIES
VALID_STATUSES = ('active', 'superseded', 'removed')
LIST_STATUS_CHOICES = ('active', 'superseded', 'removed', 'all')

# Maximum retry attempts when allocating a fresh lesson id; bounded so that a
# pathological caller cannot wedge the script in an unbounded loop.
MAX_ID_ALLOCATION_RETRIES = 99

# Hard fallback for ``cleanup-superseded --retention-days`` when neither the
# CLI flag nor ``system.retention.lessons_superseded_days`` in marshal.json
# yields an integer. Matches the default seeded into ``DEFAULT_SYSTEM_RETENTION``
# (0 days — superseded stubs are pruned on the next cleanup invocation).
DEFAULT_LESSONS_SUPERSEDED_DAYS = 0


def get_lessons_dir() -> Path:
    """Get the lessons-learned directory."""
    return base_path(DIR_LESSONS)


def get_tombstones_dir() -> Path:
    """Get the tombstones directory under lessons-learned."""
    return get_lessons_dir() / '.tombstones'


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


def _allocate_and_write_scaffold(metadata_factory: Callable[[str], dict], title: str, body: str = '') -> dict:
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


def _write_tombstone(lesson_id: str, reason: str, status: str, superseded_by: str | None = None) -> Path:
    """Write a tombstone JSON file recording lesson removal/supersede.

    Tombstones live at ``{lessons-learned}/.tombstones/{lesson-id}.json`` and
    survive deletion of the source lesson so callers can still resolve a
    removed id back to its closure context.
    """
    tombstones_dir = get_tombstones_dir()
    tombstones_dir.mkdir(parents=True, exist_ok=True)
    tombstone_path = tombstones_dir / f'{lesson_id}.json'

    payload = {
        'lesson_id': lesson_id,
        'removed_at': datetime.now(UTC).isoformat(),
        'reason': reason,
        'status': status,
    }
    if superseded_by is not None:
        payload['superseded_by'] = superseded_by

    atomic_write_file(tombstone_path, json.dumps(payload, indent=2) + '\n')
    return tombstone_path


def _append_consolidated_from(canonical_id: str, source_id: str) -> None:
    """Append ``source_id`` to the canonical lesson's ``## Consolidated from`` section.

    Creates the section at the end of the body when absent. Idempotent: if
    ``source_id`` is already listed, the canonical is left untouched.
    """
    metadata, title, body = read_lesson(canonical_id)
    if not metadata:
        # Caller is responsible for verifying canonical existence before calling.
        return

    bullet = f'- {source_id}'
    section_marker = '## Consolidated from'

    if section_marker in body:
        # Section exists — append the bullet if not already present.
        if re.search(rf'(?m)^- {re.escape(source_id)}\s*$', body):
            return
        # Append after the last bullet line of the section.
        pattern = r'(## Consolidated from\n+(?:- .*\n)*)'
        match = re.search(pattern, body)
        if match:
            new_body = body[: match.end()].rstrip() + f'\n{bullet}\n' + body[match.end() :]
        else:
            # Section header without bullets — append a bullet block after it.
            new_body = body.replace(section_marker, f'{section_marker}\n\n{bullet}\n', 1)
    else:
        trailer = '\n\n' if body.strip() else ''
        new_body = body.rstrip() + f'{trailer}{section_marker}\n\n{bullet}\n'

    write_lesson(canonical_id, metadata, title, new_body)


def _merge_consolidated_lesson_body(
    canonical_id: str,
    source_id: str,
    source_title: str,
    source_metadata: dict,
    source_body: str,
) -> int:
    """Merge a source lesson's body into the canonical under ``## Consolidated lessons``.

    Appends a ``### {source_id} — {source_title}`` subsection containing the
    source body to the canonical's ``## Consolidated lessons`` section, creating
    the H2 when absent. Returns the number of bytes added to the canonical body.

    Idempotency: if the canonical already has a ``### {source_id}`` subsection,
    the canonical is left untouched and ``0`` is returned.

    The canonical is written via :func:`write_lesson`, which goes through
    :func:`atomic_write_file` — a partial failure during the write leaves the
    canonical's previous body intact on disk.
    """
    metadata, title, body = read_lesson(canonical_id)
    if not metadata:
        # Caller is responsible for verifying canonical existence before calling.
        return 0

    if re.search(rf'(?m)^### {re.escape(source_id)}(?:\s|$)', body):
        return 0

    component = source_metadata.get('component', '')
    category = source_metadata.get('category', '')

    subsection = (
        f'### {source_id} — {source_title}\n\n'
        f'**Component**: `{component}` · **Category**: {category}\n\n'
        f'{source_body.rstrip()}\n'
    )

    h2_marker = '## Consolidated lessons'

    if h2_marker in body:
        # H2 already exists — append a fresh subsection at the end of the body
        # so multiple supersedes against the same canonical accumulate without
        # duplicating the H2 header.
        new_body = body.rstrip() + '\n\n' + subsection
    else:
        # First merge against this canonical — emit the H2 plus the first
        # subsection at the end of the body.
        trailer = '\n\n' if body.strip() else ''
        new_body = body.rstrip() + f'{trailer}{h2_marker}\n\n{subsection}'

    appended_bytes = len(new_body) - len(body)
    write_lesson(canonical_id, metadata, title, new_body)
    return appended_bytes


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
            'status': 'active',
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
    """Update lesson metadata (component, category). For body updates, use ``set-body``."""
    metadata, title, body = read_lesson(args.lesson_id)

    if not metadata:
        return {
            'status': 'error',
            'id': args.lesson_id,
            'error': 'not_found',
            'message': f'Lesson {args.lesson_id} not found',
        }

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
        return {
            'status': 'error',
            'id': args.lesson_id,
            'error': 'not_found',
            'message': f'Lesson {args.lesson_id} not found',
        }

    result = {
        'status': 'success',
        'id': metadata.get('id', args.lesson_id),
        'component': metadata.get('component', ''),
        'category': metadata.get('category', ''),
        'lifecycle_status': metadata.get('status', 'active'),
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

    status_filter = getattr(args, 'status', None) or 'active'

    lessons = []
    total = 0

    for path in sorted(lessons_dir.glob('*.md')):
        total += 1
        content = path.read_text(encoding='utf-8')
        metadata = parse_markdown_metadata(content)

        # Status filter — absence of frontmatter ``status`` field defaults to ``active``.
        lesson_status = metadata.get('status', 'active')
        if status_filter != 'all' and lesson_status != status_filter:
            continue

        # Apply legacy filters
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
            'status': lesson_status,
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
    if any(sep in args.lesson_id for sep in ('/', '\\', '..')) or any(sep in args.plan_id for sep in ('/', '\\', '..')):
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


def cmd_set_body(args: argparse.Namespace) -> dict:
    """Overwrite the body of an existing lesson stub.

    Reads the body content from ``--file PATH`` (preferred) or ``--content
    STRING`` (secondary), preserves the ``key=value`` frontmatter and the H1
    title verbatim, and replaces everything after the H1 with the supplied
    body. Returns TOON ``{status, id, path, body_bytes_written}``.
    """
    return set_body(
        get_lessons_dir(),
        args.lesson_id,
        file_path=args.file,
        content=args.content,
    )


def cmd_set_title(args: argparse.Namespace) -> dict:
    """Rewrite the H1 title of a lesson file in place.

    Locates the first ``^# `` line in the lesson markdown (skipping fenced
    code blocks so a ``# `` line inside a ```` ``` ```` block is not picked
    up) and replaces only that line; the ``key=value`` frontmatter, blank
    lines, and body remain untouched on disk. Active and superseded lifecycle
    states are both rewriteable — only ``not_found`` (no markdown file at the
    canonical path) and malformed-lesson states fail.

    The function is idempotent: rewriting with the existing title produces no
    on-disk change but still returns ``status: success`` with
    ``old_title == new_title``. Returns TOON
    ``{status, lesson_id, old_title, new_title, file}``.
    """
    lessons_dir = get_lessons_dir()
    target = lessons_dir / f'{args.lesson_id}.md'

    if not target.exists():
        return {
            'status': 'error',
            'lesson_id': args.lesson_id,
            'error': 'not_found',
            'message': f'Lesson {args.lesson_id} not found',
        }

    original = target.read_text(encoding='utf-8')
    lines = original.split('\n')

    # Walk lines, tracking fenced-code-block state, and rewrite the first
    # outside-fence line that starts with ``# ``. Three-backtick fences that
    # appear inside the body must be skipped so a literal ``# heading`` line
    # inside a code example is not mistaken for the lesson H1.
    in_fence = False
    h1_index = -1
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith('# '):
            h1_index = i
            break

    if h1_index == -1:
        return {
            'status': 'error',
            'lesson_id': args.lesson_id,
            'error': 'malformed_lesson',
            'message': (
                f'Lesson {args.lesson_id} has no H1 title line; cannot rewrite title'
            ),
        }

    old_title = lines[h1_index][2:].strip()
    new_title = args.title.strip()

    if old_title == new_title:
        # Idempotent no-op — surface success without rewriting the file so
        # callers can re-run safely without churning mtimes or the audit log.
        return {
            'status': 'success',
            'lesson_id': args.lesson_id,
            'old_title': old_title,
            'new_title': new_title,
            'file': str(target.resolve()),
        }

    lines[h1_index] = f'# {new_title}'
    rebuilt = '\n'.join(lines)

    atomic_write_file(target, rebuilt)

    return {
        'status': 'success',
        'lesson_id': args.lesson_id,
        'old_title': old_title,
        'new_title': new_title,
        'file': str(target.resolve()),
    }


# =============================================================================
# Aggregate verb — read-only cross-lesson classifier
# =============================================================================
#
# See ``references/aggregate-analysis.md`` for the authoritative classifier
# specification. Implementation summary:
#   1. Load every active lesson with its body.
#   2. Per-lesson signals: cross_refs (regex), component, standards_dir,
#      workflow_boundary.
#   3. Strongest-signal grouping (cross-ref > shared-component
#      > shared-standards-dir > shared-workflow-boundary). Each lesson
#      participates in at most one group.
#   4. Singletons are dropped.
#   5. Primary pick: highest cross-ref-fan-in → highest recurrence-count
#      → lowest lesson id.
#   6. Compose merged-body preview (~400 chars) per the doc template.
#   7. Emit deterministic TOON.

# Regex matching the lesson-id pattern ``YYYY-MM-DD-HH-NNN`` exactly.
LESSON_ID_REGEX = re.compile(r'\b\d{4}-\d{2}-\d{2}-\d{2}-\d{3}\b')

# Recurrence H2 regex used to count appended dedup-merge sections in a body.
RECURRENCE_H2_REGEX = re.compile(r'(?m)^## Recurrence —')

# Maximum size of merged_body_preview in characters.
AGGREGATE_PREVIEW_CHARS = 400

# Signal priority labels (highest first). Used both for tier-detection during
# grouping and for ordering the headline command list.
SIGNAL_CROSS_REF = 'cross-ref'
SIGNAL_SHARED_COMPONENT = 'shared-component'
SIGNAL_SHARED_STANDARDS_DIR = 'shared-standards-dir'
SIGNAL_SHARED_WORKFLOW_BOUNDARY = 'shared-workflow-boundary'

SIGNAL_PRIORITY: tuple[str, ...] = (
    SIGNAL_CROSS_REF,
    SIGNAL_SHARED_COMPONENT,
    SIGNAL_SHARED_STANDARDS_DIR,
    SIGNAL_SHARED_WORKFLOW_BOUNDARY,
)


def _derive_standards_dir(component: str) -> str:
    """Derive the standards directory path from a ``{bundle}:{skill}`` component.

    Returns the empty string when the component value is not parseable as
    ``bundle:skill`` (e.g., bare strings, multi-colon values from custom
    components). Multi-colon values are intentionally ignored — the doc
    contract requires the exact ``{bundle}:{skill}`` shape.
    """
    if not component or component.count(':') != 1:
        return ''
    bundle, skill = component.split(':', 1)
    if not bundle or not skill:
        return ''
    return f'marketplace/bundles/{bundle}/skills/{skill}/standards/'


def _derive_workflow_boundary(component: str) -> str:
    """Derive the workflow-boundary label from a component value.

    The workflow boundary is the ``{bundle}:{skill}`` pair stripped of any
    task-number suffix (e.g., ``plan-marshall:phase-5-execute:5`` →
    ``plan-marshall:phase-5-execute``). Returns the component verbatim when
    no trailing numeric suffix is present, or the empty string for unparseable
    values.
    """
    if not component:
        return ''
    parts = component.split(':')
    if len(parts) < 2:
        return ''
    # Drop a trailing purely-numeric segment if present.
    if len(parts) >= 3 and parts[-1].isdigit():
        parts = parts[:-1]
    return ':'.join(parts[:2]) if len(parts) >= 2 else ''


def _extract_cross_refs(lesson_id: str, body: str) -> set[str]:
    """Extract lesson-id cross references from a body, excluding self-refs."""
    if not body:
        return set()
    matches = set(LESSON_ID_REGEX.findall(body))
    matches.discard(lesson_id)
    return matches


def _load_active_lessons_with_signals() -> list[dict]:
    """Load every active lesson with body and per-lesson signals.

    Returns a list of dicts with keys ``id``, ``title``, ``component``,
    ``body``, ``cross_refs``, ``standards_dir``, ``workflow_boundary``,
    ``recurrence_count``. Lessons without ``status: active`` (or those with
    no metadata) are skipped — the aggregate verb only operates on the
    active corpus.
    """
    lessons_dir = get_lessons_dir()
    if not lessons_dir.exists():
        return []

    lessons: list[dict] = []
    for path in sorted(lessons_dir.glob('*.md')):
        content = path.read_text(encoding='utf-8')
        metadata = parse_markdown_metadata(content)
        if not metadata:
            continue
        if metadata.get('status', 'active') != 'active':
            continue

        lesson_id = metadata.get('id', path.stem)
        # Reuse read_lesson semantics for title/body extraction so the
        # frontmatter/title/body split matches the rest of the script.
        _, title, body = read_lesson(lesson_id)
        component = metadata.get('component', '')

        lessons.append(
            {
                'id': lesson_id,
                'title': title,
                'component': component,
                'body': body,
                'cross_refs': _extract_cross_refs(lesson_id, body),
                'standards_dir': _derive_standards_dir(component),
                'workflow_boundary': _derive_workflow_boundary(component),
                'recurrence_count': len(RECURRENCE_H2_REGEX.findall(body)),
            }
        )
    return lessons


def _group_by_signals(lessons: list[dict]) -> list[dict]:
    """Build groups using the strongest-wins priority order.

    Walks signal tiers in priority order. Within each tier, members are
    placed into buckets keyed by the tier's signal value (cross-ref groups
    by alphabetically-smallest member id; shared-component groups by the
    component value; etc.). A lesson placed at a higher tier is not
    eligible for a weaker tier. Multi-member groups only — singletons are
    dropped.
    """
    by_id = {lesson['id']: lesson for lesson in lessons}
    placed: dict[str, dict] = {}  # lesson_id -> {group_id, signal}
    # Keyed by (signal, group_key) tuple so the same string value can serve as
    # a group key at multiple tiers without collision.
    groups: dict[tuple[str, str], dict] = {}

    # ---- Tier 1: cross-ref ----
    # A cross-ref pair links two lessons when either body cites the other's
    # id. Connected components form a group.
    adjacency: dict[str, set[str]] = {lid: set() for lid in by_id}
    for lid, lesson in by_id.items():
        for ref in lesson['cross_refs']:
            if ref in by_id:
                adjacency[lid].add(ref)
                adjacency[ref].add(lid)

    visited: set[str] = set()
    for lid in sorted(by_id):
        if lid in visited:
            continue
        # BFS the component containing lid.
        component_members: set[str] = set()
        queue = [lid]
        while queue:
            cur = queue.pop()
            if cur in visited:
                continue
            visited.add(cur)
            component_members.add(cur)
            for neighbour in adjacency[cur]:
                if neighbour not in visited:
                    queue.append(neighbour)
        if len(component_members) < 2:
            continue
        # Place all members at the cross-ref tier.
        group_key = sorted(component_members)[0]  # alphabetically smallest member id
        groups[(SIGNAL_CROSS_REF, group_key)] = {
            'key': group_key,
            'signal': SIGNAL_CROSS_REF,
            'members': component_members,
        }
        for member in component_members:
            placed[member] = {'group_key': group_key, 'signal': SIGNAL_CROSS_REF}

    # Helper: attempt to add lesson at a given tier with a given key.
    def _try_place(lesson_id: str, group_key: str, signal: str) -> None:
        if lesson_id in placed:
            return
        existing = groups.get((signal, group_key))
        if existing is None:
            groups[(signal, group_key)] = {
                'key': group_key,
                'signal': signal,
                'members': {lesson_id},
            }
        else:
            existing['members'].add(lesson_id)

    # ---- Tier 2: shared-component ----
    component_buckets: dict[str, list[str]] = {}
    for lid, lesson in by_id.items():
        if lid in placed:
            continue
        comp = lesson['component']
        if not comp:
            continue
        component_buckets.setdefault(comp, []).append(lid)
    for comp, members in component_buckets.items():
        if len(members) < 2:
            continue
        for member in members:
            _try_place(member, comp, SIGNAL_SHARED_COMPONENT)
        # Mark as placed only if the bucket actually formed a group.
        bucket_group = groups.get((SIGNAL_SHARED_COMPONENT, comp))
        if bucket_group and len(bucket_group['members']) >= 2:
            for member in bucket_group['members']:
                placed[member] = {
                    'group_key': comp,
                    'signal': SIGNAL_SHARED_COMPONENT,
                }

    # ---- Tier 3: shared-standards-dir ----
    standards_buckets: dict[str, list[str]] = {}
    for lid, lesson in by_id.items():
        if lid in placed:
            continue
        sdir = lesson['standards_dir']
        if not sdir:
            continue
        standards_buckets.setdefault(sdir, []).append(lid)
    for sdir, members in standards_buckets.items():
        if len(members) < 2:
            continue
        for member in members:
            _try_place(member, sdir, SIGNAL_SHARED_STANDARDS_DIR)
        bucket_group = groups.get((SIGNAL_SHARED_STANDARDS_DIR, sdir))
        if bucket_group and len(bucket_group['members']) >= 2:
            for member in bucket_group['members']:
                placed[member] = {
                    'group_key': sdir,
                    'signal': SIGNAL_SHARED_STANDARDS_DIR,
                }

    # ---- Tier 4: shared-workflow-boundary ----
    boundary_buckets: dict[str, list[str]] = {}
    for lid, lesson in by_id.items():
        if lid in placed:
            continue
        boundary = lesson['workflow_boundary']
        if not boundary:
            continue
        boundary_buckets.setdefault(boundary, []).append(lid)
    for boundary, members in boundary_buckets.items():
        if len(members) < 2:
            continue
        for member in members:
            _try_place(member, boundary, SIGNAL_SHARED_WORKFLOW_BOUNDARY)
        bucket_group = groups.get((SIGNAL_SHARED_WORKFLOW_BOUNDARY, boundary))
        if bucket_group and len(bucket_group['members']) >= 2:
            for member in bucket_group['members']:
                placed[member] = {
                    'group_key': boundary,
                    'signal': SIGNAL_SHARED_WORKFLOW_BOUNDARY,
                }

    # Filter to multi-member groups only (drop singletons that may have
    # leaked through helper bookkeeping).
    return [
        {
            'key': info['key'],
            'signal': info['signal'],
            'members': sorted(info['members']),
        }
        for info in groups.values()
        if len(info['members']) >= 2
    ]


def _pick_primary(group_member_ids: list[str], by_id: dict[str, dict]) -> str:
    """Apply the primary-pick rule from ``aggregate-analysis.md``.

    Order: highest cross-ref-fan-in (count of OTHER members citing this
    lesson) → highest recurrence-count → lowest lesson id ascending.
    """
    member_set = set(group_member_ids)

    def fan_in(lid: str) -> int:
        return sum(
            1
            for other in member_set
            if other != lid and lid in by_id[other]['cross_refs']
        )

    # Sort by (-fan_in, -recurrence, id ascending) — ascending wins are first.
    ranked = sorted(
        group_member_ids,
        key=lambda lid: (-fan_in(lid), -by_id[lid]['recurrence_count'], lid),
    )
    return ranked[0]


def _absorbed_reason(
    absorbed_id: str,
    primary_id: str,
    signal: str,
    by_id: dict[str, dict],
    group_key: str,
) -> str:
    """Compose the absorbed-row ``reason`` field per the doc contract."""
    if signal == SIGNAL_CROSS_REF:
        return f'cross-ref to {primary_id}'
    if signal == SIGNAL_SHARED_COMPONENT:
        return f'shared component {by_id[absorbed_id]["component"]}'
    if signal == SIGNAL_SHARED_STANDARDS_DIR:
        return f'shared standards-dir {group_key}'
    if signal == SIGNAL_SHARED_WORKFLOW_BOUNDARY:
        return f'shared workflow-boundary {group_key}'
    return signal


def _compose_merged_body(primary: dict, absorbed: list[dict]) -> str:
    """Compose the would-be merged body verbatim per the doc template."""
    sections = [primary['body'].rstrip()]
    for member in absorbed:
        sections.append(
            f'## Sub-task: {member["title"]} ({member["id"]})\n\n'
            f'{member["body"].rstrip()}'
        )
    return '\n\n'.join(sections)


def _truncate_preview(text: str, limit: int) -> str:
    """Truncate ``text`` to at most ``limit`` characters on a code-point boundary.

    Python string slicing already operates on code-point boundaries, so a
    plain ``text[:limit]`` is safe here. The helper is kept as a named
    boundary for the doc contract (``first ~400 chars`` rule).
    """
    if len(text) <= limit:
        return text
    return text[:limit]


def cmd_aggregate(args: argparse.Namespace) -> dict:
    """Classify the active lesson corpus into would-land-in-one-plan groups.

    Read-only — never invokes ``set-body``, ``set-title``, ``supersede``, or
    ``cleanup-superseded``. Emits TOON
    ``{status, top_n, groups[]{primary_id, primary_title, absorb_count,
    absorbed[{lesson_id, title, reason}], merged_body_preview}, top_n_commands[]}``.

    The classifier rules and primary-pick ordering are specified in
    ``references/aggregate-analysis.md``.
    """
    top_n = args.top_n if args.top_n is not None else 5

    lessons = _load_active_lessons_with_signals()
    by_id = {lesson['id']: lesson for lesson in lessons}
    raw_groups = _group_by_signals(lessons)

    # Sort groups by key ascending for deterministic output.
    raw_groups.sort(key=lambda g: g['key'])

    out_groups: list[dict] = []
    # Track per-group (signal, group_key, primary_id, absorb_count) so we can
    # build the prioritised top_n_commands list afterwards without re-scanning.
    headline_records: list[tuple[int, int, str, str]] = []

    for group in raw_groups:
        members = group['members']
        signal = group['signal']
        group_key = group['key']
        primary_id = _pick_primary(members, by_id)
        absorbed_ids = [m for m in members if m != primary_id]
        # Absorbed members keep the deterministic id-ascending order.
        absorbed_ids.sort()

        primary = by_id[primary_id]
        absorbed_lessons = [by_id[aid] for aid in absorbed_ids]

        full_merged = _compose_merged_body(primary, absorbed_lessons)
        preview = _truncate_preview(full_merged, AGGREGATE_PREVIEW_CHARS)

        absorbed_rows = [
            {
                'lesson_id': aid,
                'title': by_id[aid]['title'],
                'reason': _absorbed_reason(aid, primary_id, signal, by_id, group_key),
            }
            for aid in absorbed_ids
        ]

        out_groups.append(
            {
                'primary_id': primary_id,
                'primary_title': primary['title'],
                'absorb_count': len(absorbed_ids),
                'absorbed': absorbed_rows,
                'merged_body_preview': preview,
            }
        )

        # Headline ordering: signal-tier index ASC, absorb_count DESC, key ASC.
        tier_index = SIGNAL_PRIORITY.index(signal)
        headline_records.append(
            (tier_index, -len(absorbed_ids), group_key, primary_id)
        )

    headline_records.sort()
    top_n_commands = [
        f'/plan-marshall:plan-marshall lesson={primary_id}'
        for _tier, _neg_count, _key, primary_id in headline_records[:top_n]
    ]

    return {
        'status': 'success',
        'top_n': top_n,
        'groups': out_groups,
        'top_n_commands': top_n_commands,
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
        return {
            'id': lesson_id,
            'component': component,
            'category': 'bug',
            'status': 'active',
            'created': today,
        }

    title = f'Error: {error[:50]}'
    body = f'## Error\n\n{error}\n\n'
    if solution:
        body += f'## Solution\n\n{solution}\n'

    allocation = _allocate_and_write_scaffold(_metadata, title, body)
    if allocation['status'] != 'success':
        return allocation

    return {'status': 'success', 'id': allocation['id'], 'created_from': 'error_context'}


def cmd_remove(args: argparse.Namespace) -> dict:
    """Remove a lesson file and write a tombstone.

    Refuses without ``--reason``. Without ``--force``, prints the lesson
    metadata + body length to stderr and reads a yes/no confirmation from
    stdin. On confirm, writes the tombstone JSON, deletes the lesson file,
    and emits an INFO line to script-execution.log.
    """
    metadata, title, body = read_lesson(args.lesson_id)
    if not metadata:
        return {
            'status': 'error',
            'id': args.lesson_id,
            'error': 'not_found',
            'message': f'Lesson {args.lesson_id} not found',
        }

    if not args.force:
        print(
            f'Lesson {args.lesson_id}: {title}',
            f'  component: {metadata.get("component", "")}',
            f'  category:  {metadata.get("category", "")}',
            f'  status:    {metadata.get("status", "active")}',
            f'  body:      {len(body)} chars',
            f'  reason:    {args.reason}',
            sep='\n',
            file=sys.stderr,
        )
        # Write the prompt to stderr — input()'s prompt argument writes to
        # stdout by default, which would corrupt the script's machine-readable
        # TOON output emitted by output_toon().
        print(f'Remove lesson {args.lesson_id}? [y/N]: ', end='', flush=True, file=sys.stderr)
        try:
            answer = input().strip().lower()
        except EOFError:
            answer = ''
        if answer not in ('y', 'yes'):
            return {
                'status': 'cancelled',
                'id': args.lesson_id,
                'message': 'User declined removal',
            }

    tombstone_path = _write_tombstone(args.lesson_id, args.reason, status='removed')

    lesson_path = get_lessons_dir() / f'{args.lesson_id}.md'
    lesson_path.unlink()

    log_entry(
        'script',
        'global',
        'INFO',
        f'(plan-marshall:manage-lessons) Removed lesson {args.lesson_id} — {args.reason}',
    )

    return {
        'status': 'success',
        'id': args.lesson_id,
        'reason': args.reason,
        'tombstone': str(tombstone_path.resolve()),
    }


def cmd_supersede(args: argparse.Namespace) -> dict:
    """Mark a lesson as superseded by a canonical lesson.

    Merges the source body into the canonical under ``## Consolidated lessons``,
    appends the source id to the canonical's ``## Consolidated from`` section,
    writes a tombstone JSON with ``superseded_by``, and replaces the source
    body with a ``[SUPERSEDED]`` redirect stub (frontmatter ``status:
    superseded``).

    The canonical is mutated before the source body is destroyed: if either
    canonical write fails, the source remains untouched on disk so callers can
    retry safely. Subsequent supersedes against the same canonical append new
    ``### {source-id}`` subsections under the existing ``## Consolidated
    lessons`` H2 without duplicating it; a re-run against an already-merged
    source is idempotent.
    """
    if args.lesson_id == args.by:
        return {
            'status': 'error',
            'error': 'self_supersede',
            'message': 'A lesson cannot supersede itself',
        }

    metadata, title, body = read_lesson(args.lesson_id)
    if not metadata:
        return {
            'status': 'error',
            'id': args.lesson_id,
            'error': 'not_found',
            'message': f'Lesson {args.lesson_id} not found',
        }

    canonical_metadata, _canonical_title, _canonical_body = read_lesson(args.by)
    if not canonical_metadata:
        return {
            'status': 'error',
            'id': args.by,
            'error': 'canonical_not_found',
            'message': f'Canonical lesson {args.by} not found',
        }

    tombstone_path = _write_tombstone(args.lesson_id, args.reason, status='superseded', superseded_by=args.by)

    # Mutate canonical first so the source body is preserved in the canonical
    # before its on-disk form is destroyed. If either canonical write raises,
    # the source remains intact and callers can retry; both helpers are
    # idempotent so the retry will not double-append.
    _append_consolidated_from(args.by, args.lesson_id)
    merged_bytes = _merge_consolidated_lesson_body(args.by, args.lesson_id, title, metadata, body)

    new_metadata = dict(metadata)
    new_metadata['status'] = 'superseded'

    redirect_body = (
        '[SUPERSEDED]\n\n'
        f'This lesson was superseded by `{args.by}`.\n\n'
        f'Reason: {args.reason}\n\n'
        f'See [{args.by}.md](./{args.by}.md) for the canonical record.'
    )
    write_lesson(args.lesson_id, new_metadata, title, redirect_body)

    log_entry(
        'script',
        'global',
        'INFO',
        f'(plan-marshall:manage-lessons) Superseded lesson {args.lesson_id} by {args.by} — {args.reason} — merged_bytes={merged_bytes}',
    )

    return {
        'status': 'success',
        'id': args.lesson_id,
        'superseded_by': args.by,
        'reason': args.reason,
        'tombstone': str(tombstone_path.resolve()),
        'merged_bytes': merged_bytes,
    }


def _resolve_retention_days(cli_value: int | None) -> int:
    """Resolve effective ``retention_days`` for ``cleanup-superseded``.

    Precedence:
        1. ``cli_value`` (from ``--retention-days``) when not None.
        2. ``system.retention.lessons_superseded_days`` from marshal.json.
        3. :data:`DEFAULT_LESSONS_SUPERSEDED_DAYS` (hard fallback).

    A missing or unreadable marshal.json silently falls through to the hard
    fallback — this command must remain usable on pre-init checkouts where
    marshal.json has not yet been written.
    """
    if cli_value is not None:
        return cli_value

    marshal_path = get_marshal_path()
    if not marshal_path.exists():
        return DEFAULT_LESSONS_SUPERSEDED_DAYS

    try:
        config = json.loads(marshal_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return DEFAULT_LESSONS_SUPERSEDED_DAYS

    retention = config.get('system', {}).get('retention', {})
    value = retention.get('lessons_superseded_days')
    if isinstance(value, int) and value >= 0:
        return value
    return DEFAULT_LESSONS_SUPERSEDED_DAYS


def cmd_cleanup_superseded(args: argparse.Namespace) -> dict:
    """Prune the markdown stubs of superseded lessons while preserving tombstones.

    Two modes (mutually exclusive at the parser level):

    * **Explicit ids** — ``--lesson-id ID`` (repeatable). Each id is evaluated
      independently regardless of file age. Use this to drop a known set of
      stubs immediately.
    * **Age-filtered** — ``--retention-days N``. Walks every superseded lesson
      file whose mtime is older than ``now - N days``. When N is omitted the
      effective value resolves from ``system.retention.lessons_superseded_days``
      in marshal.json, with a hard fallback of
      :data:`DEFAULT_LESSONS_SUPERSEDED_DAYS`.

    Per-id rules (applied to both modes):

    * Lesson must exist with metadata.status == ``superseded``.
    * The matching tombstone ``.tombstones/{id}.json`` must exist —
      otherwise the id is reported under ``skipped_no_tombstone`` and left
      untouched. This guarantees we never destroy the only remaining record
      of a removal.
    * If the ``.md`` is already gone but the tombstone is present, the id
      is reported under ``already_removed`` (idempotent re-runs are a no-op).
    * Tombstone files are NEVER deleted by this command.

    On ``--dry-run`` the script reports what it would do without unlinking
    anything; the ``dry_run`` flag in the output mirrors the input.
    """
    retention_days_effective = _resolve_retention_days(args.retention_days)
    explicit_ids: list[str] = list(args.lesson_id) if args.lesson_id else []
    use_age_filter = not explicit_ids

    lessons_dir = get_lessons_dir()
    tombstones_dir = get_tombstones_dir()

    removed: list[dict] = []
    already_removed: list[dict] = []
    skipped_no_tombstone: list[dict] = []

    if use_age_filter:
        if not lessons_dir.exists():
            candidates: list[str] = []
        else:
            cutoff = datetime.now(UTC).timestamp() - (retention_days_effective * 86400)
            candidate_paths: list[Path] = []
            for path in sorted(lessons_dir.glob('*.md')):
                try:
                    if path.stat().st_mtime >= cutoff:
                        continue
                    content = path.read_text(encoding='utf-8')
                except OSError:
                    continue
                metadata = parse_markdown_metadata(content)
                if metadata.get('status') != 'superseded':
                    continue
                candidate_paths.append(path)
            candidates = [p.stem for p in candidate_paths]
    else:
        candidates = explicit_ids

    for lesson_id in candidates:
        lesson_path = lessons_dir / f'{lesson_id}.md'
        tombstone_path = tombstones_dir / f'{lesson_id}.json'

        if not tombstone_path.exists():
            skipped_no_tombstone.append({'lesson_id': lesson_id})
            continue

        if not lesson_path.exists():
            already_removed.append({'lesson_id': lesson_id})
            continue

        # Verify status (only enforced for explicit ids; age-filter walk has
        # already filtered on metadata.status == 'superseded').
        if not use_age_filter:
            metadata, _title, _body = read_lesson(lesson_id)
            if metadata.get('status') != 'superseded':
                skipped_no_tombstone.append({'lesson_id': lesson_id})
                continue

        if args.dry_run:
            removed.append({'lesson_id': lesson_id})
            continue

        lesson_path.unlink()
        log_entry(
            'script',
            'global',
            'INFO',
            f'(plan-marshall:manage-lessons) Pruned superseded stub {lesson_id}',
        )
        removed.append({'lesson_id': lesson_id})

    return {
        'status': 'success',
        'dry_run': bool(args.dry_run),
        'retention_days_effective': retention_days_effective,
        'removed': removed,
        'already_removed': already_removed,
        'skipped_no_tombstone': skipped_no_tombstone,
    }


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
    add_component_arg(add_parser)
    add_parser.add_argument(
        '--category', required=True, choices=['bug', 'improvement', 'anti-pattern'], help='Lesson category'
    )
    add_parser.add_argument('--title', required=True, help='Lesson title')
    add_parser.add_argument('--bundle', help='Optional bundle reference')
    add_parser.set_defaults(func=cmd_add)

    # update
    update_parser = subparsers.add_parser('update', help='Update lesson metadata', allow_abbrev=False)
    add_lesson_id_arg(update_parser)
    add_component_arg(update_parser, required=False)
    update_parser.add_argument('--category', choices=['bug', 'improvement', 'anti-pattern'], help='Update category')
    update_parser.set_defaults(func=cmd_update)

    # get
    get_parser = subparsers.add_parser('get', help='Get single lesson', allow_abbrev=False)
    add_lesson_id_arg(get_parser)
    get_parser.set_defaults(func=cmd_get)

    # list
    list_parser = subparsers.add_parser('list', help='List lessons', allow_abbrev=False)
    add_component_arg(list_parser, required=False)
    list_parser.add_argument('--category', choices=['bug', 'improvement', 'anti-pattern'], help='Filter by category')
    list_parser.add_argument(
        '--status',
        choices=list(LIST_STATUS_CHOICES),
        default='active',
        help='Filter by lifecycle status (default: active; use "all" to include superseded/removed)',
    )
    list_parser.add_argument('--full', action='store_true', help='Include full lesson body content')
    list_parser.set_defaults(func=cmd_list)

    # convert-to-plan
    convert_parser = subparsers.add_parser(
        'convert-to-plan',
        help='Move a lesson file into a plan directory as lesson-{id}.md',
        allow_abbrev=False,
    )
    add_lesson_id_arg(convert_parser)
    add_plan_id_arg(convert_parser)
    convert_parser.set_defaults(func=cmd_convert_to_plan)

    # set-body
    set_body_parser = subparsers.add_parser(
        'set-body',
        help='Overwrite the body of an existing lesson stub (preserves frontmatter and H1 title)',
        allow_abbrev=False,
    )
    add_lesson_id_arg(set_body_parser)
    set_body_input = set_body_parser.add_mutually_exclusive_group(required=True)
    set_body_input.add_argument('--file', help='Path to a file containing the body content')
    set_body_input.add_argument('--content', help='Inline body content (secondary form for tiny payloads)')
    set_body_parser.set_defaults(func=cmd_set_body)

    # set-title
    set_title_parser = subparsers.add_parser(
        'set-title',
        help='Rewrite the H1 title of an existing lesson file in place (preserves frontmatter and body)',
        allow_abbrev=False,
    )
    add_lesson_id_arg(set_title_parser)
    set_title_parser.add_argument('--title', required=True, help='New lesson title (replaces the H1 line)')
    set_title_parser.set_defaults(func=cmd_set_title)

    # aggregate
    aggregate_parser = subparsers.add_parser(
        'aggregate',
        help=(
            'Read-only classifier: group active lessons that would land in '
            'one plan. See references/aggregate-analysis.md for rules.'
        ),
        allow_abbrev=False,
    )
    aggregate_parser.add_argument(
        '--top-n',
        type=int,
        default=5,
        help=(
            'Number of headline commands to surface (default: 5). The full '
            'group list is always returned regardless of this flag.'
        ),
    )
    aggregate_parser.set_defaults(func=cmd_aggregate)

    # from-error
    from_error_parser = subparsers.add_parser('from-error', help='Create from error context', allow_abbrev=False)
    from_error_parser.add_argument('--context', required=True, help='JSON error context')
    from_error_parser.set_defaults(func=cmd_from_error)

    # remove
    remove_parser = subparsers.add_parser(
        'remove',
        help='Delete a lesson file and write a tombstone (interactive confirm by default)',
        allow_abbrev=False,
    )
    add_lesson_id_arg(remove_parser)
    remove_parser.add_argument('--reason', required=True, help='Removal reason (recorded in tombstone and audit log)')
    remove_parser.add_argument('--force', action='store_true', help='Skip the interactive confirmation prompt')
    remove_parser.set_defaults(func=cmd_remove)

    # supersede
    supersede_parser = subparsers.add_parser(
        'supersede',
        help='Mark a lesson as superseded by a canonical lesson, write redirect stub and tombstone',
        allow_abbrev=False,
    )
    add_lesson_id_arg(supersede_parser)
    supersede_parser.add_argument('--by', required=True, help='Canonical lesson ID that absorbs the source')
    supersede_parser.add_argument(
        '--reason', required=True, help='Supersede reason (recorded in tombstone and audit log)'
    )
    supersede_parser.set_defaults(func=cmd_supersede)

    # cleanup-superseded
    cleanup_parser = subparsers.add_parser(
        'cleanup-superseded',
        help=(
            'Prune the .md stubs of superseded lessons (tombstones are preserved). '
            'Either pass --lesson-id ID (repeatable) for explicit ids or '
            '--retention-days N for age-filtered pruning.'
        ),
        allow_abbrev=False,
    )
    cleanup_mode = cleanup_parser.add_mutually_exclusive_group(required=False)
    cleanup_mode.add_argument(
        '--lesson-id',
        action='append',
        type=validate_lesson_id,
        help=(
            'Lesson ID to prune (repeatable). When supplied, --retention-days '
            'is ignored and ids are evaluated regardless of file age.'
        ),
    )
    cleanup_mode.add_argument(
        '--retention-days',
        type=int,
        help=(
            'Age threshold in days. Falls back to '
            'system.retention.lessons_superseded_days from marshal.json '
            f'(hard fallback {DEFAULT_LESSONS_SUPERSEDED_DAYS}) when omitted.'
        ),
    )
    cleanup_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report what would be removed without unlinking anything.',
    )
    cleanup_parser.set_defaults(func=cmd_cleanup_superseded)

    # auto-suggest — recipe-registry matcher for phase-1-init Step 5c.
    auto_suggest_parser = subparsers.add_parser(
        'auto-suggest',
        help='Recipe-registry matcher for phase-1-init Step 5c (no LLM dispatch)',
        description=(
            "Scan the marketplace recipe registry (manage-config list-recipes) and "
            "return up to --max-suggestions recipes ordered by deterministic "
            "confidence. The score blends keyword overlap (request narrative vs "
            "recipe description), domain alignment, and scope alignment. With "
            "--emit (default), each suggestion is also written as an info-severity "
            "Q-Gate finding so the orchestrator can surface the list. Use "
            "--no-emit to inspect suggestions without writing findings."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    auto_suggest_parser.add_argument('--plan-id', dest='plan_id', required=True, help='Plan identifier')
    auto_suggest_parser.add_argument(
        '--max-suggestions',
        dest='max_suggestions',
        type=int,
        default=3,
        help='Maximum number of suggestions returned (default: 3).',
    )
    auto_suggest_parser.add_argument(
        '--no-emit',
        dest='no_emit',
        action='store_true',
        help='Return suggestions without writing Q-Gate findings (dry-run).',
    )
    auto_suggest_parser.set_defaults(func=cmd_auto_suggest)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
