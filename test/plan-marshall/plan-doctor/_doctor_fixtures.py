#!/usr/bin/env python3
"""Local test fixtures for plan-doctor tests.

This module is named ``_fixtures.py`` (NOT ``conftest.py``) per the repo's
fixture-discovery convention documented in ``dev-general-module-testing``:
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
