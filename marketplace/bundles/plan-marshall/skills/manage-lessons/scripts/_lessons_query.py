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
from _lessons_io import (
    LessonStore,
    get_lessons_dir,
    read_lesson,
    resolve_lesson_store,
)
from _plan_parsing import extract_deliverables, parse_document_sections
from file_ops import (
    atomic_write_file,
    parse_markdown_metadata,
)
from marketplace_paths import (
    resolve_main_anchored_path,
)
from toon_parser import serialize_toon


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


def _extract_h1_title(content: str) -> str:
    """Return the text of the first ``# `` line in a lesson markdown body.

    Returns the empty string when the file carries no H1 line.
    """
    for line in content.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return ''


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

        title = _extract_h1_title(content)

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


# Default per-component cap for ``consult``. Deliberately set above the largest
# per-component lesson count observed on the live corpus, so it does not bind in
# practice and exists purely as a runaway guard for future corpus growth.
DEFAULT_CONSULT_MAX_PER_COMPONENT = 25

# An affected-file path maps to a ``{bundle}:{skill}`` lesson component only when
# it lives under ``marketplace/bundles/{bundle}/skills/{skill}/`` AND names
# something inside that skill directory. Paths outside this shape (tests, docs,
# repo-root files) are reported in ``unmapped_paths[]`` rather than dropped.
_COMPONENT_PATH_REGEX = re.compile(r'^marketplace/bundles/([^/]+)/skills/([^/]+)/.+$')


def _derive_components(deliverables: list[dict]) -> tuple[list[str], list[str]]:
    """Split every deliverable's affected-file paths into components and leftovers.

    Returns ``(components, unmapped_paths)`` — both deduplicated and sorted, so
    the derivation is deterministic regardless of document order.
    """
    components: set[str] = set()
    unmapped: set[str] = set()

    for deliverable in deliverables:
        for entry in deliverable.get('affected_files', []):
            path = entry.get('path', '')
            if not path:
                continue
            match = _COMPONENT_PATH_REGEX.match(path)
            if match:
                components.add(f'{match.group(1)}:{match.group(2)}')
            else:
                unmapped.add(path)

    return sorted(components), sorted(unmapped)


def _active_lessons_by_component(components: set[str]) -> dict[str, list[dict]]:
    """Group active lessons whose ``component`` exactly equals a requested one.

    Applies the same exact-string-equality predicate ``cmd_list`` uses for
    ``--component``; there is no fuzzy or prefix expansion. Lessons are appended
    in lesson-id order within each component.
    """
    lessons_dir = get_lessons_dir()
    if not lessons_dir.exists():
        return {}

    by_component: dict[str, list[dict]] = {}

    for path in sorted(lessons_dir.glob('*.md')):
        content = path.read_text(encoding='utf-8')
        metadata = parse_markdown_metadata(content)

        if metadata.get('status', 'active') != 'active':
            continue

        component = metadata.get('component', '')
        if component not in components:
            continue

        by_component.setdefault(component, []).append(
            {
                'lesson_id': metadata.get('id', path.stem),
                'component': component,
                'category': metadata.get('category', ''),
                'title': _extract_h1_title(content),
            }
        )

    for rows in by_component.values():
        rows.sort(key=lambda row: row['lesson_id'])

    return by_component


def cmd_consult(args: argparse.Namespace) -> dict:
    """Surface the active lessons that name the components a plan is editing.

    Read-only prospective query fired by ``phase-3-outline`` once the plan's
    ``solution_outline.md`` has been written and validated. It derives the
    plan's ``{bundle}:{skill}`` component set from the deliverables' affected-file
    paths, returns every active lesson whose ``component`` exactly equals one of
    them, and writes the machine record to ``work/lessons-consult.toon``.

    The verb never mutates a lesson, never emits a Q-Gate finding, and never
    applies a surfaced lesson — the outline author judges the returned set and
    records a per-lesson disposition in the outline's ``## Lessons Consulted``
    section. A present artifact with ``surfaced_count: 0`` means the consult
    fired and matched nothing; an absent artifact means it never fired.

    A missing ``solution_outline.md`` is a structured ``error: outline_not_found``
    — never ``status: success`` with an empty surfaced set.
    """
    if any(sep in args.plan_id for sep in ('/', '\\', '..')):
        return {
            'status': 'error',
            'error': 'invalid_id',
            'message': 'Identifiers must not contain path separators or traversal sequences',
        }

    if args.max_per_component < 0:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_cap',
            'message': (
                f'--max-per-component must be >= 0, got {args.max_per_component}'
            ),
        }

    plan_dir = resolve_main_anchored_path('plans') / args.plan_id
    outline_path = plan_dir / 'solution_outline.md'

    if not outline_path.exists():
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'outline_not_found',
            'message': f'No solution_outline.md at {outline_path}',
        }

    sections = parse_document_sections(outline_path.read_text(encoding='utf-8'))
    deliverables = extract_deliverables(sections.get('deliverables', ''))
    components, unmapped_paths = _derive_components(deliverables)

    by_component = _active_lessons_by_component(set(components))

    max_per_component = args.max_per_component
    surfaced: list[dict] = []
    total_matched = 0
    truncated = False

    # Iterate the derived component list (already sorted) so the union is
    # ordered by (component, lesson_id) with no filesystem order leaking through.
    for component in components:
        rows = by_component.get(component, [])
        total_matched += len(rows)
        if len(rows) > max_per_component:
            truncated = True
        surfaced.extend(rows[:max_per_component])

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'components': components,
        'unmapped_paths': unmapped_paths,
        'surfaced': surfaced,
        'surfaced_count': len(surfaced),
        'total_matched': total_matched,
        'truncated': truncated,
    }

    artifact_path = plan_dir / 'work' / 'lessons-consult.toon'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_file(artifact_path, serialize_toon(result))

    result['artifact_path'] = str(artifact_path.resolve())
    return result


#: The closed vocabulary :func:`cmd_restore_from_plan` reports as ``action``.
#:
#: - ``restored`` — the plan directory resolved, was scanned, carried at least
#:   one ``lesson-*.md``, and EVERY carried file landed in the corpus. Pairs
#:   with ``status: success``.
#: - ``restore_incomplete`` — the plan directory resolved, was scanned, and
#:   carried lesson files, but the move aborted on a guard (a traversal-shaped
#:   id, or a destination that already exists). ``restored_count`` states how
#:   many landed BEFORE the abort and is legitimately ``0`` when the very first
#:   file collided. Pairs with ``status: error``.
#: - ``no_lesson_file`` — the plan directory GENUINELY resolved, WAS scanned,
#:   and held no ``lesson-*.md``. This is the benign zero.
#: - ``plan_dir_unresolved`` — the plan directory could not be resolved to the
#:   main-anchored store, so the verb never looked. This is the NON-benign zero.
#:
#: Splitting ``plan_dir_unresolved`` out of ``no_lesson_file`` is the whole
#: point of the contract: the two were previously the same answer, so a plan
#: directory reached through the wrong store — or not reached at all — reported
#: as a plan that verifiably carried no lesson. ``restore_incomplete`` exists
#: for the same reason one level down: an aborted move used to report
#: ``action: restored`` alongside ``status: error`` and ``restored_count: 0``,
#: so a consumer asserting against this set — which this contract instructs
#: callers to do rather than re-listing literals — concluded at least one
#: lesson had landed when none had. ``restored`` now means exactly what it
#: says, and never rides with an error status.
RESTORE_ACTIONS = frozenset(
    {'restored', 'restore_incomplete', 'no_lesson_file', 'plan_dir_unresolved'}
)


def _restore_payload(
    plan_id: str,
    action: str,
    store: LessonStore,
    *,
    restored: list[dict] | None = None,
    error: str = '',
    message: str = '',
    **extra: object,
) -> dict:
    """Build a ``restore-from-plan`` payload carrying the FULL documented field set.

    Every return of :func:`cmd_restore_from_plan` — success and error alike —
    routes through here, so no early-return branch can omit a field the verb's
    documented Output contract promises unconditionally. A caller parsing
    ``store_resolution`` or ``restored_count`` gets them on the could-not-look
    path exactly as on the restored path.

    ``status`` is derived from ``error`` rather than passed separately, so a
    payload can never claim success while naming an error code.
    """
    restored_lessons = restored if restored is not None else []
    payload: dict = {
        'status': 'error' if error else 'success',
        'plan_id': plan_id,
        'action': action,
        'store_resolution': store.resolution,
        'plans_root': '' if store.path is None else str(store.path),
        'restored_count': len(restored_lessons),
        'restored_lessons': restored_lessons,
    }
    if error:
        payload['error'] = error
        payload['message'] = message
    payload.update(extra)
    return payload


def cmd_restore_from_plan(args: argparse.Namespace) -> dict:
    """Move all lesson files from a plan directory back to the global lessons directory.

    Inverse of ``cmd_convert_to_plan``. Scans the plan directory for every
    ``lesson-*.md`` file, derives the original ``lesson_id`` from each filename,
    and moves the file back to ``.plan/local/lessons-learned/{lesson_id}.md``.
    Plans that consolidate several lessons may carry more than one
    ``lesson-*.md`` file at the plan-dir root; every match is restored.

    The verb reports FOUR distinguishable outcomes over the closed
    :data:`RESTORE_ACTIONS` vocabulary, modelled on
    ``_orchestrator_inbox.cmd_inbox_list``'s ``epic_not_found`` /
    ``inbox_state: missing`` / ``present with count: 0`` triple: the
    discriminator rides the PAYLOAD, and the verb stays non-faulting for the
    benign zero. ``action: no_lesson_file`` now means what it says — the plan
    directory resolved, was scanned, and held nothing — while a plan directory
    that could not be resolved under the main-anchored plans root is the
    distinct, NON-benign ``action: plan_dir_unresolved``, returned as a
    structured ``status: error`` with that error code. ``store_resolution``
    sub-discriminates the two ways that can happen: ``unresolved`` (the store
    itself was unreachable) versus a resolved store that simply does not hold
    the named plan directory.

    An absent plan directory is deliberately the non-benign outcome, not the
    benign one: "the plan never existed" and "I looked in the wrong store" are
    indistinguishable from here, and reporting either as a verified-empty plan
    is exactly the fail-open this contract closes.

    Refuses to clobber a pre-existing destination file (fail-fast on the first
    collision; any lessons restored before the collision remain in
    ``lessons-learned/`` and are reported in ``restored_lessons``). An aborted
    move is the fourth outcome, ``action: restore_incomplete`` — NOT
    ``restored``: on a collision with the very first match nothing has landed,
    and reporting that as ``restored`` claims the one thing the value promises.
    ``restored`` is therefore reachable only from the final return, where every
    carried file moved.
    """
    plans_store = resolve_lesson_store('plans')

    if any(sep in args.plan_id for sep in ('/', '\\', '..')):
        return _restore_payload(
            args.plan_id,
            'plan_dir_unresolved',
            plans_store,
            error='invalid_id',
            message='Identifiers must not contain path separators or traversal sequences',
        )

    if plans_store.path is None:
        return _restore_payload(
            args.plan_id,
            'plan_dir_unresolved',
            plans_store,
            error='plan_dir_unresolved',
            message=(
                f'Cannot resolve the main-anchored plans root, so the plan directory '
                f'was never scanned: {plans_store.detail}'
            ),
        )

    lessons_store = resolve_lesson_store()
    if lessons_store.path is None:
        return _restore_payload(
            args.plan_id,
            'plan_dir_unresolved',
            plans_store,
            error='plan_dir_unresolved',
            message=(
                f'Cannot resolve the main-anchored lessons corpus, so no lesson could '
                f'be restored: {lessons_store.detail}'
            ),
        )

    plan_parent = plans_store.path.resolve()
    plan_dir = (plan_parent / args.plan_id).resolve()
    lessons_dir = lessons_store.path.resolve()

    if plan_dir.parent != plan_parent:
        return _restore_payload(
            args.plan_id,
            'plan_dir_unresolved',
            plans_store,
            error='path_traversal',
            message='Resolved path escapes intended parent directory',
        )

    if not plan_dir.exists():
        return _restore_payload(
            args.plan_id,
            'plan_dir_unresolved',
            plans_store,
            error='plan_dir_unresolved',
            message=(
                f'Plan directory {plan_dir} does not exist under the main-anchored '
                f'plans root, so it was never scanned for lesson files; this is NOT '
                f'evidence that the plan carries no lesson.'
            ),
        )

    matches = sorted(plan_dir.glob('lesson-*.md'))
    if not matches:
        return _restore_payload(args.plan_id, 'no_lesson_file', plans_store)

    lessons_dir.mkdir(parents=True, exist_ok=True)
    restored_lessons: list[dict] = []

    for match in matches:
        source = match.resolve()
        # Derive lesson id by stripping the ``lesson-`` prefix and ``.md`` suffix.
        lesson_id = source.stem[len('lesson-'):]

        # Defensive: ensure the derived id has no traversal sequences and resolves
        # back inside the plan dir.
        if any(sep in lesson_id for sep in ('/', '\\', '..')) or source.parent != plan_dir:
            return _restore_payload(
                args.plan_id,
                'restore_incomplete',
                plans_store,
                restored=restored_lessons,
                error='path_traversal',
                message='Resolved path escapes intended parent directory',
            )

        destination = (lessons_dir / f'{lesson_id}.md').resolve()

        if destination.parent != lessons_dir:
            return _restore_payload(
                args.plan_id,
                'restore_incomplete',
                plans_store,
                restored=restored_lessons,
                error='path_traversal',
                message='Resolved path escapes intended parent directory',
            )

        if destination.exists():
            return _restore_payload(
                args.plan_id,
                'restore_incomplete',
                plans_store,
                restored=restored_lessons,
                error='destination_exists',
                message=f'Destination {destination} already exists; refusing to clobber',
                lesson_id=lesson_id,
            )

        shutil.move(source, destination)
        restored_lessons.append({
            'lesson_id': lesson_id,
            'source': str(source),
            'destination': str(destination),
        })

    return _restore_payload(
        args.plan_id, 'restored', plans_store, restored=restored_lessons
    )


#: The closed vocabulary :func:`cmd_list_stalled` reports as ``plans_root_state``.
#:
#: - ``present`` — the enumeration looked at a real plans directory.
#: - ``missing`` — the store RESOLVED, and the main-anchored plans root it
#:   points at does not exist, so the enumeration could not look. As in
#:   ``_orchestrator_inbox.cmd_inbox_list``, an absent root is NOT a fault — the
#:   verb still returns ``status: success`` so a sweep is never aborted by it,
#:   and the two zeros are told apart by the PAYLOAD rather than by the status.
#: - ``unknown`` — a required store did not resolve at all, so whether the
#:   plans root exists was never determined. Reporting that case as ``missing``
#:   asserts a fact about the filesystem the verb never established; it rides
#:   only with the ``store_unresolved`` error.
#:
#: Consumers assert against this set rather than re-listing the literals.
PLANS_ROOT_STATES = frozenset({'present', 'missing', 'unknown'})

#: Which store :func:`cmd_list_stalled` names in ``unresolved_store``. The verb
#: needs BOTH the plans root and the lessons corpus, so a caller reading
#: ``error: store_unresolved`` must be told which one failed — the two demand
#: different remediation. Empty string on every branch where both resolved.
UNRESOLVED_STORES = frozenset({'', 'plans', 'lessons'})


def _stalled_payload(
    store: LessonStore,
    plans_root_state: str,
    *,
    scanned_plan_count: int = 0,
    stalled: list[dict] | None = None,
    duplicates: list[dict] | None = None,
    unclassifiable: list[dict] | None = None,
    unresolved_store: str = '',
    error: str = '',
    message: str = '',
) -> dict:
    """Build a ``list-stalled`` payload carrying the FULL documented field set.

    Every return of :func:`cmd_list_stalled` routes through here, so a
    could-not-look return states every count the documented Output contract
    promises unconditionally instead of emitting a bare ``stalled_count: 0``.

    ``store`` MUST be the store whose resolution the payload is reporting — on
    a could-not-look return that is the store that actually FAILED, never a
    sibling that happened to resolve. ``store_resolution`` is the field the
    documented consumer branches on, so a resolved value emitted next to
    ``error: store_unresolved`` sends that consumer past its could-not-look
    exit and into a reconciliation against a corpus nothing ever read.
    """
    stalled_plans = stalled if stalled is not None else []
    duplicate_lessons = duplicates if duplicates is not None else []
    unclassifiable_plans = unclassifiable if unclassifiable is not None else []
    payload: dict = {
        'status': 'error' if error else 'success',
        'store_resolution': store.resolution,
        'plans_root': '' if store.path is None else str(store.path),
        'plans_root_state': plans_root_state,
        'unresolved_store': unresolved_store,
        'scanned_plan_count': scanned_plan_count,
        'stalled_count': len(stalled_plans),
        'stalled_plans': stalled_plans,
        'duplicate_count': len(duplicate_lessons),
        'duplicate_lessons': duplicate_lessons,
        'unclassifiable_count': len(unclassifiable_plans),
        'unclassifiable_plans': unclassifiable_plans,
    }
    if error:
        payload['error'] = error
        payload['message'] = message
    return payload


def _read_plan_status(status_path: Path) -> tuple[dict | None, str]:
    """Read and parse a plan's ``status.json``, reporting WHY a read failed.

    Returns ``(status, reason)`` where exactly one side is meaningful: a parsed
    mapping with an empty reason, or ``None`` with a reason token naming why the
    plan could not be classified. The reason is what keeps an unclassifiable
    plan visible in the payload instead of being silently skipped out of the
    population — a silent skip is the same could-not-look-reports-benign
    collapse at row granularity.
    """
    if not status_path.exists():
        return None, 'status_json_missing'
    try:
        status = json.loads(status_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None, 'status_json_unreadable'
    if not isinstance(status, dict):
        # Valid JSON but not an object (e.g. a list or string) — calling
        # status.get() would raise AttributeError.
        return None, 'status_json_not_an_object'
    return status, ''


def cmd_list_stalled(args: argparse.Namespace) -> dict:  # noqa: ARG001
    """List plans whose relocated lesson file is stranded (stalled).

    A plan relocates a lesson into its plan directory via ``convert-to-plan``
    (``plans/{plan_id}/lesson-{id}.md``). If such a plan stalls or is abandoned
    in ``5-execute``/``6-finalize`` without running ``restore-from-plan``, the
    lesson is trapped out of the active corpus and silently lost. This read-only
    scanner surfaces every such plan so callers can decide whether to restore or
    discard.

    **Population.** The candidate population is derived from the OBSERVABLE —
    the presence of a ``lesson-*.md`` file in a plan directory — and nothing
    else. It is deliberately NOT filtered by ``status.metadata.plan_source``:
    that gate excluded every ``convert-to-plan``-carried plan, whose
    ``plan_source`` is unset, so the verb reported a clean zero over a
    population that had already discarded the very plans it exists to find. A
    file on disk cannot be argued with; a metadata field that was never written
    can. ``plan_source`` is still REPORTED on each row as context, but it
    classifies nothing.

    **Both directions are reported.** Absence is only half the failure. A
    carried ``lesson-*.md`` whose id ALREADY exists in the active corpus is the
    inverse direction — restoring it would collide — and is reported as its own
    separately-counted ``duplicate_lessons`` outcome rather than folded into
    the stalled count. The two lists are independent views over the same scan,
    correlated by ``plan_id``: a plan may legitimately appear in both, and a
    consumer that intends to call ``restore-from-plan`` on a stalled plan must
    check the duplicate list first or the restore will fail on the collision.

    **Every zero states which kind of zero it is.** An unresolvable store is a
    structured ``status: error`` (``store_unresolved``) carrying
    ``store_resolution: unresolved``, ``plans_root_state: unknown``, and the
    ``unresolved_store`` name of the store that failed; an absent plans root
    under a store that DID resolve is the non-faulting
    ``plans_root_state: missing``; and a plan whose ``status.json`` cannot be
    read is surfaced in ``unclassifiable_plans`` instead of being silently
    dropped from the population. ``stalled_count: 0`` is therefore never bare —
    it always rides with the discriminators that say whether the store was
    actually resolved and scanned.

    **The verb needs BOTH stores**, so both are resolved up front and either
    one failing is a could-not-look return. The discriminator reports the store
    that failed, not the one that happened to succeed: an unresolved lessons
    corpus reported as ``store_resolution: main_anchored`` is the same
    could-not-look-reports-benign collapse this verb exists to close, one field
    removed.
    """
    plans_store = resolve_lesson_store('plans')
    lessons_store = resolve_lesson_store()

    if plans_store.path is None or lessons_store.path is None:
        # Report the resolution of the store that ACTUALLY failed. Passing the
        # plans store here emitted a RESOLVED ``store_resolution`` next to
        # ``error: store_unresolved`` whenever the LESSONS corpus was the
        # unreachable one — and the documented consumer branches on
        # ``store_resolution``, so it skipped its could-not-look exit and
        # reconciled against a corpus it never reached. ``plans_root_state`` is
        # ``unknown`` rather than ``missing`` for the same reason: nothing here
        # established that the plans root is absent.
        unresolved_name = 'plans' if plans_store.path is None else 'lessons'
        unresolved = plans_store if plans_store.path is None else lessons_store
        return _stalled_payload(
            unresolved,
            'unknown',
            unresolved_store=unresolved_name,
            error='store_unresolved',
            message=(
                f'Cannot resolve the main-anchored {unresolved_name} store, so no '
                f'plan directory was ever scanned: {unresolved.detail}'
            ),
        )

    plans_root = plans_store.path
    if not plans_root.exists():
        return _stalled_payload(plans_store, 'missing')

    lessons_dir = lessons_store.path

    # Group relocated lesson files by their owning plan directory. Presence of
    # the file IS the population predicate.
    by_plan: dict[Path, list[str]] = {}
    for lesson_file in sorted(plans_root.glob('*/lesson-*.md')):
        if not lesson_file.is_file():
            continue
        plan_dir = lesson_file.parent
        lesson_id = lesson_file.stem[len('lesson-'):]
        by_plan.setdefault(plan_dir, []).append(lesson_id)

    stalled_plans: list[dict] = []
    duplicate_lessons: list[dict] = []
    unclassifiable_plans: list[dict] = []

    for plan_dir in sorted(by_plan, key=lambda p: p.name):
        plan_id = plan_dir.name
        lesson_ids = sorted(by_plan[plan_dir])

        # Inverse direction: a carried lesson id that already exists in the
        # active corpus. Reported for every scanned plan regardless of its
        # stalled classification — the collision is a fact about the corpus,
        # not about the plan's phase.
        for lesson_id in lesson_ids:
            corpus_path = lessons_dir / f'{lesson_id}.md'
            if corpus_path.exists():
                duplicate_lessons.append({
                    'plan_id': plan_id,
                    'lesson_id': lesson_id,
                    'corpus_path': str(corpus_path),
                })

        status, unreadable_reason = _read_plan_status(plan_dir / 'status.json')
        if status is None:
            # Cannot classify this plan. Surface it rather than dropping it —
            # a silently-skipped row is a stalled plan the caller never hears
            # about, which is the same fail-open at row granularity.
            unclassifiable_plans.append({
                'plan_id': plan_id,
                'lesson_ids': lesson_ids,
                'reason': unreadable_reason,
            })
            continue

        metadata = status.get('metadata', {})
        plan_source = metadata.get('plan_source', '') if isinstance(metadata, dict) else ''
        if not isinstance(plan_source, str):
            plan_source = ''

        current_phase = status.get('current_phase', '')
        phase_status = ''
        phases = status.get('phases', [])
        if isinstance(phases, list):
            for row in phases:
                if isinstance(row, dict) and row.get('name') == current_phase:
                    phase_status = row.get('status', '')
                    break

        # Terminal guard: a plan whose current phase has fully completed is NOT
        # stalled — its lesson was (or will be) restored on a normal terminal
        # path. Stalled = the relocated lesson is present AND the current phase
        # has not reached ``done`` (covers in_progress / blocked / pending in
        # 5-execute / 6-finalize, and any non-terminal dormated-without-merge
        # state). This classification is unchanged; only the population feeding
        # it widened.
        is_stalled = current_phase in ('5-execute', '6-finalize') and phase_status != 'done'

        if not is_stalled:
            continue

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

    return _stalled_payload(
        plans_store,
        'present',
        scanned_plan_count=len(by_plan),
        stalled=stalled_plans,
        duplicates=duplicate_lessons,
        unclassifiable=unclassifiable_plans,
    )


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
