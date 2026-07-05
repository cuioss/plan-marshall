#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Read-only and relocate command handlers for ``manage-lessons.py``.

Co-located helper module holding the lesson subcommands that carry no
wall-clock dependency and do not go through the entry module's patched write
path (``_mod.atomic_write_file`` / ``_mod.log_entry`` / ``_mod.input`` /
``_mod._write_tombstone``): ``get``, ``list``, ``list-stalled``,
``restore-from-plan``, ``set-body`` and ``set-title``.

Write commands that a test patches (``supersede`` via ``atomic_write_file`` /
``log_entry``, ``remove`` via ``input``) and every datetime-stamped command
(``add``, ``from-error``, ``convert-to-plan``, ``cleanup-superseded``,
``retire-quiet``) stay in the entry module. This module imports only shared
modules plus the co-located ``_lessons_io`` read-core, so the entry module can
re-import these handlers without an import cycle.
"""

import argparse
import json
import re
import shutil
from pathlib import Path

from _lessons_crud import set_body
from _lessons_io import get_lessons_dir, read_lesson
from file_ops import (
    atomic_write_file,
    parse_markdown_metadata,
)
from marketplace_paths import (
    resolve_main_anchored_path,
)


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


def cmd_restore_from_plan(args: argparse.Namespace) -> dict:
    """Move all lesson files from a plan directory back to the global lessons directory.

    Inverse of ``cmd_convert_to_plan``. Scans the plan directory for every
    ``lesson-*.md`` file, derives the original ``lesson_id`` from each filename,
    and moves the file back to ``.plan/local/lessons-learned/{lesson_id}.md``.
    Plans that consolidate several lessons may carry more than one
    ``lesson-*.md`` file at the plan-dir root; every match is restored.

    Idempotent on missing lesson file — returns ``status: success`` with
    ``action: no_lesson_file`` when nothing to restore so callers don't need to
    pre-check. Refuses to clobber a pre-existing destination file (fail-fast on
    the first collision; any lessons restored before the collision remain in
    ``lessons-learned/``).
    """
    if any(sep in args.plan_id for sep in ('/', '\\', '..')):
        return {
            'status': 'error',
            'error': 'invalid_id',
            'message': 'Identifiers must not contain path separators or traversal sequences',
        }

    plan_parent = resolve_main_anchored_path('plans').resolve()
    plan_dir = (plan_parent / args.plan_id).resolve()
    lessons_dir = get_lessons_dir().resolve()

    if plan_dir.parent != plan_parent:
        return {
            'status': 'error',
            'error': 'path_traversal',
            'message': 'Resolved path escapes intended parent directory',
        }

    if not plan_dir.exists():
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'action': 'no_lesson_file',
        }

    matches = sorted(plan_dir.glob('lesson-*.md'))
    if not matches:
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'action': 'no_lesson_file',
        }

    lessons_dir.mkdir(parents=True, exist_ok=True)
    restored_lessons: list[dict] = []

    for match in matches:
        source = match.resolve()
        # Derive lesson id by stripping the ``lesson-`` prefix and ``.md`` suffix.
        lesson_id = source.stem[len('lesson-'):]

        # Defensive: ensure the derived id has no traversal sequences and resolves
        # back inside the plan dir.
        if any(sep in lesson_id for sep in ('/', '\\', '..')) or source.parent != plan_dir:
            return {
                'status': 'error',
                'error': 'path_traversal',
                'message': 'Resolved path escapes intended parent directory',
            }

        destination = (lessons_dir / f'{lesson_id}.md').resolve()

        if destination.parent != lessons_dir:
            return {
                'status': 'error',
                'error': 'path_traversal',
                'message': 'Resolved path escapes intended parent directory',
            }

        if destination.exists():
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'lesson_id': lesson_id,
                'error': 'destination_exists',
                'message': f'Destination {destination} already exists; refusing to clobber',
            }

        shutil.move(source, destination)
        restored_lessons.append({
            'lesson_id': lesson_id,
            'source': str(source),
            'destination': str(destination),
        })

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'restored_count': len(restored_lessons),
        'restored_lessons': restored_lessons,
    }


# Lesson ids embedded in a plan's ``metadata.plan_source`` must match the
# canonical ``YYYY-MM-DD-HH-NNN`` shape exactly (anchored full-match) to mark
# the plan as lesson-sourced. The unanchored ``LESSON_ID_REGEX`` (in
# ``_lessons_aggregate``) is used for free-text scanning; this one is the strict
# classifier gate.
LESSON_SOURCE_ID_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}-\d{2}-\d{3}$')


def cmd_list_stalled(args: argparse.Namespace) -> dict:  # noqa: ARG001
    """List lesson-sourced plans whose relocated lesson is stranded (stalled).

    A lesson-sourced plan relocates its lesson into the plan directory via
    ``convert-to-plan`` (``plans/{plan_id}/lesson-{id}.md``). If such a plan
    stalls or is abandoned in ``5-execute``/``6-finalize`` without running
    ``restore-from-plan``, the lesson is trapped out of the active corpus and
    silently lost. This read-only scanner surfaces every such plan so callers
    can decide whether to restore or discard.
    """
    plans_root = resolve_main_anchored_path('plans')
    if not plans_root.exists():
        return {'status': 'success', 'stalled_count': 0, 'stalled_plans': []}

    # Group relocated lesson files by their owning plan directory.
    by_plan: dict[Path, list[str]] = {}
    for lesson_file in sorted(plans_root.glob('*/lesson-*.md')):
        if not lesson_file.is_file():
            continue
        plan_dir = lesson_file.parent
        lesson_id = lesson_file.stem[len('lesson-'):]
        by_plan.setdefault(plan_dir, []).append(lesson_id)

    stalled_plans: list[dict] = []

    for plan_dir in sorted(by_plan, key=lambda p: p.name):
        lesson_ids = sorted(by_plan[plan_dir])
        status_path = plan_dir / 'status.json'
        if not status_path.exists():
            # No status.json — cannot classify; skip rather than crash.
            continue

        try:
            status = json.loads(status_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            # Corrupt/unreadable status.json — skip rather than crash.
            continue

        if not isinstance(status, dict):
            # Valid JSON but not an object (e.g. a list or string) — calling
            # status.get() would raise AttributeError; skip rather than crash.
            continue

        metadata = status.get('metadata', {})
        plan_source = metadata.get('plan_source', '') if isinstance(metadata, dict) else ''
        if not isinstance(plan_source, str) or not LESSON_SOURCE_ID_REGEX.match(plan_source):
            # Not lesson-sourced — the relocated lesson is unexpected, but a
            # non-lesson-id plan_source is out of scope for stalled detection.
            continue

        current_phase = status.get('current_phase', '')
        phase_status = ''
        phases = status.get('phases', [])
        if isinstance(phases, list):
            for row in phases:
                if isinstance(row, dict) and row.get('name') == current_phase:
                    phase_status = row.get('status', '')
                    break

        # Terminal guard: a lesson-sourced plan whose current phase has fully
        # completed is NOT stalled — its lesson was (or will be) restored on a
        # normal terminal path. Stalled = the relocated lesson is present AND
        # the current phase has not reached ``done`` (covers in_progress /
        # blocked / pending in 5-execute / 6-finalize, and any non-terminal
        # dormated-without-merge state).
        is_stalled = current_phase in ('5-execute', '6-finalize') and phase_status != 'done'

        if not is_stalled:
            continue

        plan_id = plan_dir.name
        stalled_plans.append({
            'plan_id': plan_id,
            'plan_source': plan_source,
            'current_phase': current_phase,
            'phase_status': phase_status,
            'lesson_ids': lesson_ids,
            'restore_command': (
                'python3 .plan/execute-script.py '
                'plan-marshall:manage-lessons:manage-lessons '
                f'restore-from-plan --plan-id {plan_id}'
            ),
        })

    return {
        'status': 'success',
        'stalled_count': len(stalled_plans),
        'stalled_plans': stalled_plans,
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
