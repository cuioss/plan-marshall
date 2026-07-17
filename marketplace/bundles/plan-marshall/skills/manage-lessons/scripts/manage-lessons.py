#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    python3 manage-lesson.py convert-to-plan --lesson-id 2025-12-02-001 --plan-id EXAMPLE-PLAN

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
from _lessons_aggregate import (
    AGGREGATE_PREVIEW_CHARS,
    RECURRENCE_H2_REGEX,
    SIGNAL_CROSS_REF,
    SIGNAL_PRIORITY,
    _absorbed_reason,
    _compose_merged_body,
    _derive_workflow_boundary,
    _extract_cross_refs,
    _group_by_signals,
    _pick_primary,
    _truncate_preview,
)
from _lessons_crud import (
    DEFAULT_ARCH_CONSTRAINT_QUIET_DAYS,
    find_active_arch_constraint_by_rule,
    reinforce_arch_constraint,
    retire_quiet_arch_constraints,
)
from _lessons_io import (
    WrongStoreError,
    _build_lesson_content,
    get_lessons_dir,
    get_tombstones_dir,
    guard_component_store_match,
    read_lesson,
)
from _lessons_query import (
    cmd_get,
    cmd_list,
    cmd_list_stalled,
    cmd_restore_from_plan,
    cmd_set_body,
    cmd_set_title,
)
from _lessons_retention import (
    DEFAULT_LESSONS_SUPERSEDED_DAYS,
    _resolve_quiet_days,
    _resolve_retention_days,
)
from constants import LESSON_CATEGORIES
from file_ops import (
    atomic_write_file,
    output_toon,
    parse_markdown_metadata,
    safe_main,
)
from input_validation import (
    add_component_arg,
    add_lesson_id_arg,
    add_plan_id_arg,
    parse_args_with_toon_errors,
    validate_lesson_id,
)
from marketplace_paths import (
    MARKETPLACE_BUNDLES_PATH,
    find_marketplace_path,
    resolve_main_anchored_path,
)
from plan_logging import log_entry

VALID_CATEGORIES = LESSON_CATEGORIES
VALID_STATUSES = ('active', 'superseded', 'removed')
LIST_STATUS_CHOICES = ('active', 'superseded', 'removed', 'all')

# Maximum retry attempts when allocating a fresh lesson id; bounded so that a
# pathological caller cannot wedge the script in an unbounded loop.
MAX_ID_ALLOCATION_RETRIES = 99


def get_next_id() -> str:
    """Generate the next lesson ID.

    Allocates the next sequence number for the current ``{date}-{hour}`` prefix
    by scanning the union of three id sources so a freed-up sequence number is
    never re-issued for an id that still exists elsewhere:

    1. Live lesson files: ``lessons-learned/{prefix}-*.md`` stems.
    2. Tombstones: ``lessons-learned/.tombstones/{prefix}-*.json`` basenames
       (``remove``/``supersede``/``convert-to-plan`` all write these).
    3. Plan-derived lesson files: ``plans/*/lesson-{prefix}-*.md`` files inside
       any plan directory (the ``lesson-`` prefix is stripped from the filename
       stem to recover the bare id). Globbing files rather than directories
       captures lessons placed under arbitrary-named plan directories by
       ``convert-to-plan`` (e.g. ``plans/my-plan/lesson-{id}.md``), not just the
       canonical ``lesson-{id}`` directory name.

    Each scan is guarded by an ``.exists()`` check so a missing directory yields
    an empty contribution. The return shape is unchanged — a single id string.
    """
    now = datetime.now().astimezone()
    date = now.strftime('%Y-%m-%d')
    hour = now.strftime('%H')
    prefix = f'{date}-{hour}'

    # Union of bare ids (without extension) that already reserve a sequence
    # number for this prefix, drawn from live lessons, tombstones, and
    # plan-derived directories.
    existing_ids: set[str] = set()

    lessons_dir = get_lessons_dir()
    if lessons_dir.exists():
        existing_ids.update(f.stem for f in lessons_dir.glob(f'{prefix}-*.md'))

    tombstones_dir = get_tombstones_dir()
    if tombstones_dir.exists():
        existing_ids.update(f.stem for f in tombstones_dir.glob(f'{prefix}-*.json'))

    plans_dir = resolve_main_anchored_path('plans')
    if plans_dir.exists():
        existing_ids.update(
            f.stem[len('lesson-'):]
            for f in plans_dir.glob(f'*/lesson-{prefix}-*.md')
            if f.is_file()
        )

    if not existing_ids:
        return f'{prefix}-001'

    # Highest trailing sequence number across the union.
    max_seq = 0
    for candidate in existing_ids:
        match = re.match(r'\d{4}-\d{2}-\d{2}-\d{2}-(\d+)', candidate)
        if match:
            max_seq = max(max_seq, int(match.group(1)))

    if max_seq == 0:
        return f'{prefix}-001'

    return f'{prefix}-{max_seq + 1:03d}'


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
            with path.open('x', encoding='utf-8') as f:
                f.write(content)
        except FileExistsError:
            # ``manage-lessons`` is a global script with no plan context, so the
            # WARNING line lands in the date-suffixed global script-execution log.
            # The ``'global'`` sentinel matches the convention used by other
            # global callers (build-pyproject/build-npm/manage-architecture).
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
    try:
        guard_component_store_match(args.component, getattr(args, 'allow_foreign_store', False))
    except WrongStoreError as exc:
        return {'status': 'error', 'error': 'wrong_store', 'message': str(exc)}

    if args.category not in VALID_CATEGORIES:
        return {
            'status': 'error',
            'error': 'invalid_category',
            'message': f'Invalid category: {args.category}',
            'valid_categories': VALID_CATEGORIES,
        }

    today = datetime.now(UTC).strftime('%Y-%m-%d')
    rule = getattr(args, 'rule', None)

    # arch-constraint lessons dedup by RULE identity: a recurring violation of a
    # rule already captured by an active arch-constraint lesson REINFORCES that
    # lesson (recurrence_count bump + ## Recurrence section) instead of allocating
    # a new one. A --rule is mandatory for this category — the rule is the dedup
    # key and the retire-on-quiet anchor.
    if args.category == 'arch-constraint':
        if not rule:
            return {
                'status': 'error',
                'error': 'missing_rule',
                'message': '--rule is required for category arch-constraint (it is the dedup key)',
            }
        existing_id = find_active_arch_constraint_by_rule(get_lessons_dir(), rule)
        if existing_id is not None:
            reinforced = reinforce_arch_constraint(get_lessons_dir(), existing_id, today)
            if reinforced['status'] == 'success':
                reinforced['path'] = str((get_lessons_dir() / f'{existing_id}.md').resolve())
                reinforced['component'] = args.component
                reinforced['category'] = args.category
                reinforced['rule'] = rule
            return reinforced

    def _metadata(lesson_id: str) -> dict:
        metadata = {
            'id': lesson_id,
            'component': args.component,
            'category': args.category,
            'status': 'active',
            'created': today,
        }
        if args.category == 'arch-constraint':
            metadata['rule'] = rule
            metadata['recurrence_count'] = '1'
            metadata['last_seen'] = today
        if args.bundle:
            metadata['bundle'] = args.bundle
        return metadata

    allocation = _allocate_and_write_scaffold(_metadata, args.title, '')
    if allocation['status'] != 'success':
        return allocation

    result = {
        'status': 'success',
        'id': allocation['id'],
        'path': str(allocation['path'].resolve()),
        'component': args.component,
        'category': args.category,
    }
    if args.category == 'arch-constraint':
        result['action'] = 'created'
        result['rule'] = rule
    return result


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


def cmd_convert_to_plan(args: argparse.Namespace) -> dict:
    """Move a lesson file from the global lessons directory into a plan directory.

    The lesson is renamed to lesson-{id}.md inside .plan/local/plans/{plan_id}/.
    Errors if the source lesson does not exist.

    The relocation is transactional: the source is deleted only AFTER the copy to
    the plan directory has been written and verified as complete and readable
    (byte-for-byte read-back). A failed copy or read-back leaves the source intact
    and removes any partial artifact from the plan directory, so the lesson is
    never left in a missing state when an error occurs mid-operation.
    """
    if any(sep in args.lesson_id for sep in ('/', '\\', '..')) or any(sep in args.plan_id for sep in ('/', '\\', '..')):
        return {
            'status': 'error',
            'error': 'invalid_id',
            'message': 'Identifiers must not contain path separators or traversal sequences',
        }

    lessons_dir = get_lessons_dir().resolve()
    source = (lessons_dir / f'{args.lesson_id}.md').resolve()
    plan_parent = resolve_main_anchored_path('plans').resolve()
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

    # Transactional copy-verify-delete: copy the source into the plan directory,
    # verify the copy is complete and readable, and only then delete the source.
    # A failure at any point before the source delete leaves the source intact and
    # removes any partial destination artifact, so the lesson is never lost.
    source_bytes = source.read_bytes()
    try:
        shutil.copyfile(source, destination)
        # Read-back verification: the destination must exist and its content must
        # match the source byte-for-byte before the source may be deleted.
        if not destination.exists() or destination.read_bytes() != source_bytes:
            raise OSError('copy verification failed: destination content mismatch')
    except OSError as exc:
        # Clean up any partial artifact; leave the source untouched.
        if destination.exists():
            destination.unlink()
        return {
            'status': 'error',
            'id': args.lesson_id,
            'error': 'copy_failed',
            'message': f'Failed to copy lesson {args.lesson_id} to plan directory: {exc}',
            'source': str(source),
            'destination': str(destination),
        }

    source.unlink()

    # Reserve the consumed id with a tombstone so it stays reserved even if the
    # plan directory (and the relocated .md inside it) is later deleted. Unlike
    # remove/supersede, convert-to-plan keeps the lesson alive — but the id must
    # not be re-issued by get_next_id, so a one-way archival-survival tombstone
    # is recorded here.
    _write_tombstone(args.lesson_id, reason='converted-to-plan', status='converted-to-plan')

    return {
        'status': 'success',
        'lesson_id': args.lesson_id,
        'plan_id': args.plan_id,
        'source': str(source),
        'destination': str(destination),
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
#
# The datetime-free, non-patched pieces of this section (the lesson-id /
# recurrence regexes, the signal-tier constants, and the pure grouping /
# primary-pick / composition helpers) live in the co-located
# ``_lessons_aggregate`` module and are imported at the top of this file.
# ``_derive_standards_dir`` (below) and ``_load_active_lessons_with_signals``
# stay here because the former reads the test-patched ``find_marketplace_path``
# and the latter drives the corpus scan.


def _derive_standards_dir(component: str) -> str:
    """Derive the standards directory path from a ``{bundle}:{skill}`` component.

    The bundles root is resolved through the cache-aware bundle resolver in
    script-shared (:func:`marketplace_paths.find_marketplace_path`) rather than
    a hard-coded ``marketplace/bundles`` literal, so the derivation tracks the
    actually-resolved bundles location (explicit ``PM_MARKETPLACE_ROOT`` anchor,
    plugin-cache install, or cwd walk-up) instead of assuming the meta-project
    source layout. When the resolver finds no bundles tree (e.g. an environment
    with neither a source checkout nor a configured anchor), the derivation
    falls back to the relative ``marketplace/bundles`` segment so the value
    still serves as a deterministic per-component grouping key.

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
    bundles_root = find_marketplace_path()
    base = str(bundles_root) if bundles_root is not None else MARKETPLACE_BUNDLES_PATH
    return f'{base}/{bundle}/skills/{skill}/standards/'


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


def cmd_aggregate(args: argparse.Namespace) -> dict:
    """Classify the active lesson corpus into would-land-in-one-plan groups.

    Read-only — never invokes ``set-body``, ``set-title``, ``supersede``, or
    ``cleanup-superseded``. Emits TOON
    ``{status, top_n, groups[]{primary_id, primary_title, absorb_count, tier,
    enacted, absorbed[{lesson_id, title, reason}], merged_body_preview},
    top_n_commands[]}``. ``tier`` is the group's strongest signal
    (cross-ref | shared-component | shared-standards-dir |
    shared-workflow-boundary); ``enacted`` is ``True`` only for the cross-ref
    tier.

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
                'tier': signal,
                'enacted': signal == SIGNAL_CROSS_REF,
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
        return {'status': 'error', 'error': 'invalid_json', 'message': 'Context must be a valid JSON object'}

    # A valid JSON array or scalar (e.g. "[]") parses cleanly but has no .get,
    # so reject any non-dict context with the same structured error.
    if not isinstance(context, dict):
        return {'status': 'error', 'error': 'invalid_json', 'message': 'Context must be a valid JSON object'}

    # An explicit null or numeric component would crash guard_component_store_match;
    # coerce any non-string value to the 'unknown' default before the guard.
    component = context.get('component', 'unknown')
    if not isinstance(component, str):
        component = 'unknown'

    try:
        guard_component_store_match(component, getattr(args, 'allow_foreign_store', False))
    except WrongStoreError as exc:
        return {'status': 'error', 'error': 'wrong_store', 'message': str(exc)}

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


def cmd_retire_quiet(args: argparse.Namespace) -> dict:
    """Retire active arch-constraint lessons whose rule has stayed quiet.

    The retire-on-quiet sibling of ``cleanup-superseded``: walks active
    arch-constraint lessons and retires (tombstone + unlink) every one whose
    ``last_seen`` is older than the resolved quiet window. The window resolves via
    :func:`_resolve_quiet_days` (CLI ``--quiet-days`` → marshal
    ``system.retention.arch_constraint_quiet_days`` → hard fallback). ``--dry-run``
    reports the would-be retirements without mutating the corpus.
    """
    quiet_days = _resolve_quiet_days(args.quiet_days)
    result = retire_quiet_arch_constraints(
        get_lessons_dir(),
        quiet_days,
        datetime.now(UTC).date(),
        _write_tombstone,
        dry_run=bool(args.dry_run),
    )
    if not args.dry_run:
        for entry in result.get('retired', []):
            log_entry(
                'script',
                'global',
                'INFO',
                (
                    f'(plan-marshall:manage-lessons) Retired quiet arch-constraint lesson '
                    f'{entry["lesson_id"]} (rule {entry["rule"]!r}, quiet {entry["quiet_days_elapsed"]}d '
                    f'>= {quiet_days}d)'
                ),
            )
    return result


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
        '--category', required=True, choices=list(VALID_CATEGORIES), help='Lesson category'
    )
    add_parser.add_argument('--title', required=True, help='Lesson title')
    add_parser.add_argument('--bundle', help='Optional bundle reference')
    add_parser.add_argument(
        '--rule',
        help=(
            'Rule identity for category arch-constraint (required for that category). '
            'The dedup key: a recurring violation of the same rule reinforces the '
            'existing lesson instead of allocating a new one.'
        ),
    )
    add_parser.add_argument(
        '--allow-foreign-store',
        action='store_true',
        help=(
            'Bypass the cross-repo wrong-store guard: file the lesson even when the '
            "resolved main-anchored store repo does not own the component's bundle."
        ),
    )
    add_parser.set_defaults(func=cmd_add)

    # update
    update_parser = subparsers.add_parser('update', help='Update lesson metadata', allow_abbrev=False)
    add_lesson_id_arg(update_parser)
    add_component_arg(update_parser, required=False)
    update_parser.add_argument('--category', choices=list(VALID_CATEGORIES), help='Update category')
    update_parser.set_defaults(func=cmd_update)

    # get (read is an accepted alias for the same operation)
    get_parser = subparsers.add_parser('get', aliases=['read'], help='Get single lesson', allow_abbrev=False)
    add_lesson_id_arg(get_parser)
    get_parser.set_defaults(func=cmd_get)

    # list
    list_parser = subparsers.add_parser('list', help='List lessons', allow_abbrev=False)
    add_component_arg(list_parser, required=False)
    list_parser.add_argument('--category', choices=list(VALID_CATEGORIES), help='Filter by category')
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

    # restore-from-plan
    restore_parser = subparsers.add_parser(
        'restore-from-plan',
        help='Move a lesson-{id}.md file from a plan directory back to the global lessons directory',
        allow_abbrev=False,
    )
    add_plan_id_arg(restore_parser)
    restore_parser.set_defaults(func=cmd_restore_from_plan)

    # list-stalled
    list_stalled_parser = subparsers.add_parser(
        'list-stalled',
        help=(
            'Read-only scanner: list lesson-sourced plans whose relocated lesson '
            'is stranded (stalled in 5-execute/6-finalize without restore-from-plan)'
        ),
        allow_abbrev=False,
    )
    list_stalled_parser.set_defaults(func=cmd_list_stalled)

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
    from_error_parser.add_argument(
        '--allow-foreign-store',
        action='store_true',
        help=(
            'Bypass the cross-repo wrong-store guard: file the lesson even when the '
            "resolved main-anchored store repo does not own the component's bundle."
        ),
    )
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

    # retire-quiet — retire-on-quiet sibling of cleanup-superseded for the
    # arch-constraint lifecycle.
    retire_quiet_parser = subparsers.add_parser(
        'retire-quiet',
        help=(
            'Retire active arch-constraint lessons whose rule has stayed quiet '
            '(no recurrence) past the quiet window. Tombstones are preserved, '
            'mirroring cleanup-superseded.'
        ),
        allow_abbrev=False,
    )
    retire_quiet_parser.add_argument(
        '--quiet-days',
        type=int,
        help=(
            'Quiet window in days. A lesson whose last_seen is at least this many '
            'days old is retired. Falls back to '
            'system.retention.arch_constraint_quiet_days from marshal.json '
            f'(hard fallback {DEFAULT_ARCH_CONSTRAINT_QUIET_DAYS}) when omitted.'
        ),
    )
    retire_quiet_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report what would be retired without unlinking anything.',
    )
    retire_quiet_parser.set_defaults(func=cmd_retire_quiet)

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
