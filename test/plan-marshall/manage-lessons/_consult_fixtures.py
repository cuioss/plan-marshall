#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``consult`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the ``consult`` subcommand of manage-lessons.py.

``cmd_consult`` is the corpus's prospective read side: it derives the plan's
``{bundle}:{skill}`` component set from its ``solution_outline.md``
``**Affected files:**`` paths, returns every ACTIVE lesson whose ``component``
exactly equals one of them, and writes the machine record to
``work/lessons-consult.toon``.

Coverage: path-to-component mapping (matching and non-matching paths),
``unmapped_paths[]`` population, exact-match component filtering (no prefix or
fuzzy expansion), active-only filtering, deterministic ``(component,
lesson_id)`` ordering, ``--max-per-component`` cap binding with the
``truncated`` / ``total_matched`` disclosure, the fail-closed
``outline_not_found`` contract, plan-id traversal rejection, the artifact
write (including the ``surfaced_count: 0`` present-artifact form), the
mutation-freedom invariant, and the CLI plumbing including the documented
default cap.

Fixture lesson IDs are sourced verbatim from real ``manage-lessons list``
inventory output — never hand-typed — per the live-anchoring discipline the
lesson-ID scanner enforces.
"""


from argparse import Namespace
from unittest.mock import patch

from _lessons_helpers import cmd_consult
from constants import DIR_LESSONS

# Real lesson IDs, taken verbatim from live ``manage-lessons list --component
# plan-marshall:phase-3-outline`` output.
OUTLINE_LESSON_IDS = (
    '2026-06-21-02-001',
    '2026-06-24-14-002',
    '2026-06-28-17-002',
    '2026-06-29-02-001',
    '2026-06-29-16-001',
)


# Real lesson ID from live ``manage-lessons list --component
# plan-marshall:manage-solution-outline`` output.
SOLUTION_OUTLINE_LESSON_ID = '2026-07-26-16-001'


OUTLINE_COMPONENT = 'plan-marshall:phase-3-outline'


SOLUTION_OUTLINE_COMPONENT = 'plan-marshall:manage-solution-outline'


OUTLINE_SKILL_PATH = 'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md'


SOLUTION_OUTLINE_SKILL_PATH = (
    'marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md'
)


TEST_PATH = 'test/plan-marshall/manage-lessons/test_consult.py'


PLAN_ID = 'consult-fixture-plan'


def _seed_lesson(tmp_path, lesson_id, component, status='active', category='improvement'):
    """Write one lesson file into the fixture corpus and return its path."""
    lessons_dir = tmp_path / DIR_LESSONS
    lessons_dir.mkdir(parents=True, exist_ok=True)
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(
        f'id={lesson_id}\n'
        f'component={component}\n'
        f'category={category}\n'
        f'status={status}\n'
        f'created=2026-01-01\n'
        f'\n'
        f'# Title for {lesson_id}\n'
        f'\n'
        f'Body.\n',
        encoding='utf-8',
    )
    return path


def _write_outline(tmp_path, affected_paths, plan_id=PLAN_ID):
    """Write a minimal solution_outline.md carrying one deliverable."""
    plan_dir = tmp_path / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    bullets = '\n'.join(f'- `{p}` (write-replace)' for p in affected_paths)
    outline = (
        f'# Solution: Consult fixture\n'
        f'\n'
        f'plan_id: {plan_id}\n'
        f'\n'
        f'## Deliverables\n'
        f'\n'
        f'### 1. Fixture deliverable\n'
        f'\n'
        f'**Affected files:**\n'
        f'{bullets}\n'
    )
    path = plan_dir / 'solution_outline.md'
    path.write_text(outline, encoding='utf-8')
    return path


def _consult(tmp_path, plan_id=PLAN_ID, max_per_component=25):
    """Invoke cmd_consult against the fixture corpus rooted at tmp_path."""
    args = Namespace(plan_id=plan_id, max_per_component=max_per_component)
    with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
        return cmd_consult(args)
