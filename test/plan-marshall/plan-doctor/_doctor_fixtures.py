#!/usr/bin/env python3
"""Local test fixtures for plan-doctor tests.

This module is named ``_fixtures.py`` (NOT ``conftest.py``) per the repo's
fixture-discovery convention documented in ``persona-module-tester``:
pytest auto-imports ``conftest.py`` modules anywhere on the collection path,
which would shadow the per-bundle isolation we want here. ``_fixtures.py``
is imported explicitly by the tests that need it.

Lessons referenced in these fixtures are *real* IDs sourced from the
production ``manage-lessons list`` inventory (see lesson 2026-04-29-10-001
on live-anchored test data — hand-typed lesson IDs in fixtures get out of
sync with the inventory and produce silent green tests).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Real lesson IDs — copy-pasted from production ``manage-lessons list`` so
# the inventory anchor (LESSON_ID_RE vs live data) keeps validating against
# real shapes and these tests fail loudly if either side drifts.
REAL_LESSON_IDS: tuple[str, ...] = (
    '2026-04-24-12-003',
    '2026-04-29-10-001',
    '2026-04-30-23-001',
    '2026-05-03-21-002',
)

# Canonical phase shape used by every status.json fixture below. The order
# mirrors the production six-phase plan lifecycle (init → refine → outline →
# plan → execute → finalize), and the `name` keys match what
# plan_doctor._all_post_refine_pending() looks for. Tests opt into specific
# per-phase statuses by passing overrides to ``make_status_json``.
CANONICAL_PHASES: tuple[str, ...] = (
    '1-init',
    '2-refine',
    '3-outline',
    '4-plan',
    '5-execute',
    '6-finalize',
)


def make_plan_with_tasks(plan_dir: Path, tasks: list[dict[str, Any]]) -> list[Path]:
    """Materialize ``TASK-NNN.json`` files under ``plan_dir/tasks/``.

    Each entry in ``tasks`` is a dict shaped like the on-disk task contract:
    at minimum ``title`` and ``description`` (the only fields ``plan-doctor``
    scans). Sequential numbers are assigned from 1 upward, so the caller's
    list order maps directly to ``TASK-001.json``, ``TASK-002.json``, …

    Returns the list of created file paths in numbering order so callers can
    target a specific file with ``scan-task-file`` if they want.
    """
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    for index, task in enumerate(tasks, start=1):
        # Allow the caller to override the number explicitly when they need
        # a non-sequential layout (e.g., to model a hand-edited gap).
        number = int(task.get('number', index))
        # Build a minimum-viable on-disk task: plan-doctor only reads
        # ``title`` and ``description`` but a realistic record reduces
        # surprise when other readers consume the same fixture later.
        record = {
            'number': number,
            'title': task.get('title', f'Task {number}'),
            'description': task.get('description', ''),
        }
        # Pass-through any extra fields the test cares about (e.g. ``status``).
        for key, value in task.items():
            if key not in record and key != 'number':
                record[key] = value

        path = tasks_dir / f'TASK-{number:03d}.json'
        path.write_text(json.dumps(record, indent=2), encoding='utf-8')
        created.append(path)

    return created


def seed_lesson_inventory(base_dir: Path, lesson_ids: tuple[str, ...] = REAL_LESSON_IDS) -> Path:
    """Populate ``base_dir/lessons-learned/`` with real lesson files.

    Each file is written with a single ``# Title`` line so ``manage-lessons
    list`` reports a non-empty inventory (the live-anchor check counts the
    rows in that listing, not the file contents). The IDs come from the
    production inventory by default — see ``REAL_LESSON_IDS`` above and
    lesson 2026-04-29-10-001 for why hand-typed shapes are forbidden.

    Returns the lessons directory path so tests can extend the seed if a
    case needs an additional lesson.
    """
    lessons_dir = base_dir / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    for lid in lesson_ids:
        # The `id` defaults to the filename stem when frontmatter is absent
        # (see manage-lessons cmd_list), so a single H1 line is enough.
        (lessons_dir / f'{lid}.md').write_text(f'# Lesson {lid}\n', encoding='utf-8')
    return lessons_dir


def make_status_json(
    plan_dir: Path,
    *,
    current_phase: str = '1-init',
    phase_statuses: dict[str, str] | None = None,
    confidence: float | None = None,
    archived_reason: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> Path:
    """Materialize a ``status.json`` file shaped like production.

    The plan-doctor directory-rule scanners read three slots: ``current_phase``,
    ``phases[]`` (a list of ``{name, status}`` records mirroring the canonical
    six-phase shape), and ``metadata`` (``confidence`` + optional
    ``archived_reason``). This helper builds exactly that shape so every test
    has a single deterministic call-site for status fixtures.

    Args:
        plan_dir: directory where ``status.json`` is written (created if absent).
        current_phase: value written to ``status.current_phase``.
        phase_statuses: optional per-phase override map; phases not listed
            default to ``"pending"``. Use this to model "init+refine done,
            rest pending" or "all done".
        confidence: optional numeric value stored under
            ``metadata.confidence``. Omitted when ``None`` (Rule 2's
            "no confidence recorded" branch).
        archived_reason: optional string stored under
            ``metadata.archived_reason`` — when present, Rule 2 must NOT
            fire even with a low confidence (case f).
        extra_metadata: additional metadata fields merged on top.

    Returns:
        Path to the written ``status.json``.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    overrides = dict(phase_statuses or {})
    phases = [
        {'name': name, 'status': overrides.get(name, 'pending')}
        for name in CANONICAL_PHASES
    ]
    metadata: dict[str, Any] = {}
    if confidence is not None:
        metadata['confidence'] = confidence
    if archived_reason is not None:
        metadata['archived_reason'] = archived_reason
    if extra_metadata:
        metadata.update(extra_metadata)

    status: dict[str, Any] = {
        'current_phase': current_phase,
        'phases': phases,
    }
    if metadata:
        status['metadata'] = metadata

    path = plan_dir / 'status.json'
    path.write_text(json.dumps(status, indent=2), encoding='utf-8')
    return path


def make_healthy_plan(plan_dir: Path) -> Path:
    """Materialize a minimum-viable healthy plan dir.

    Writes ``status.json`` (with ``current_phase`` past refine) plus a
    placeholder ``request.md`` so ``_has_any_artifact`` returns ``True``
    and Rule 1 does NOT fire. Used by the negative test for Rule 1 (case c).
    """
    make_status_json(
        plan_dir,
        current_phase='3-outline',
        phase_statuses={'1-init': 'done', '2-refine': 'done'},
        confidence=98.0,
    )
    (plan_dir / 'request.md').write_text('# Request\n', encoding='utf-8')
    return plan_dir


def make_worktree_dir(base_dir: Path, plan_id: str) -> Path:
    """Create ``base_dir/worktrees/{plan_id}/`` so Rule 3's scan visits it.

    The doctor only checks for the directory's existence — it does NOT
    open `.git`, run `git worktree list`, or inspect inner files. A bare
    mkdir is sufficient to model both "live worktree" (when the matching
    plan-dir also exists) and "dangling worktree" (when it does not).
    """
    wt_dir = base_dir / 'worktrees' / plan_id
    wt_dir.mkdir(parents=True, exist_ok=True)
    return wt_dir


def make_archived_plan(
    base_dir: Path,
    plan_id: str,
    *,
    confidence: float | None,
    phase_statuses: dict[str, str] | None = None,
    archived_reason: str | None = None,
) -> Path:
    """Create ``base_dir/archived-plans/{plan_id}/`` with a status.json shaped
    for Rule 2's predicate.

    The default ``phase_statuses`` models the stuck-low-confidence pattern:
    ``1-init`` and ``2-refine`` done, every later phase pending. Callers
    override this to model the healthy-completion shape (case g) by passing
    ``{'1-init': 'done', ..., '6-finalize': 'done'}``.
    """
    archived_dir = base_dir / 'archived-plans' / plan_id
    default_statuses = {'1-init': 'done', '2-refine': 'done'}
    make_status_json(
        archived_dir,
        current_phase='2-refine',
        phase_statuses=phase_statuses if phase_statuses is not None else default_statuses,
        confidence=confidence,
        archived_reason=archived_reason,
    )
    return archived_dir
