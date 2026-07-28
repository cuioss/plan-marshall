#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression tests for the prospective lessons-consult seam.

Deliverable 1's co-located unit tests exercise ``cmd_consult`` in isolation.
This file covers the verification scope those units cannot reach: the
plan-lifecycle wiring driven through the **real**
``python3 .plan/execute-script.py`` executor against a seeded lessons corpus
and a seeded ``solution_outline.md`` — never a ``PYTHONPATH``-constructed
import. Each invocation deliberately strips ``PYTHONPATH`` from the child
environment, so the cross-skill imports the handler depends on
(``_plan_parsing`` from ``manage-solution-outline``, ``toon_parser`` from
``ref-toon-format``) must resolve through the executor's own path setup or the
test fails.

Four cases, matching the deliverable's D3(a)-(d):

(a) A plan whose deliverables' affected files map to a component carrying an
    active lesson surfaces that lesson at the consult point. This case was
    verified to FAIL against pre-change code — invoking ``consult`` on the
    pre-change executor exits 2 with ``argument command: invalid choice:
    'consult'`` — so the test discriminates rather than passing vacuously
    both before and after the change.
(b) A plan whose components carry no active lesson completes the consult with
    ``surfaced_count: 0`` and adds no artifact, prompt, or other output beyond
    the single machine record.
(c) The surfaced set is durably recorded in ``work/lessons-consult.toon`` and
    enumerates exactly the surfaced ids; its presence with
    ``surfaced_count: 0`` is asserted to be distinguishable from its absence.
(d) A surfaced lesson is presented and NOT applied — asserted by
    mutation-freedom: the seeded lesson files are byte-identical after the
    consult, ``solution_outline.md`` is unaltered, and no Q-Gate finding is
    written.

Fixture lesson IDs are sourced verbatim from real ``manage-lessons list``
inventory output, never hand-typed.
"""

import os
import subprocess
import sys

from constants import DIR_LESSONS
from toon_parser import parse_toon

from conftest import PLAN_DIR_NAME, PROJECT_ROOT

EXECUTOR = PROJECT_ROOT / PLAN_DIR_NAME / 'execute-script.py'
NOTATION = 'plan-marshall:manage-lessons:manage-lessons'

# Real lesson IDs, taken verbatim from live ``manage-lessons list --component
# plan-marshall:phase-3-outline`` output.
INTERSECTING_LESSON_ID = '2026-06-21-02-001'
SECOND_LESSON_ID = '2026-06-24-14-002'
INTERSECTING_COMPONENT = 'plan-marshall:phase-3-outline'

# The component the intersecting plan does NOT edit — live inventory reports
# zero active lessons for it, matching the non-intersecting case.
NON_INTERSECTING_PATH = (
    'marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py'
)
INTERSECTING_PATH = 'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md'

ARTIFACT_RELPATH = ('work', 'lessons-consult.toon')


def _seed_lesson(base_dir, lesson_id, component):
    """Write one active lesson into the seeded corpus and return its path."""
    lessons_dir = base_dir / DIR_LESSONS
    lessons_dir.mkdir(parents=True, exist_ok=True)
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(
        f'id={lesson_id}\n'
        f'component={component}\n'
        f'category=bug\n'
        f'status=active\n'
        f'created=2026-01-01\n'
        f'\n'
        f'# Title for {lesson_id}\n'
        f'\n'
        f'Body.\n',
        encoding='utf-8',
    )
    return path


def _seed_outline(base_dir, plan_id, affected_paths):
    """Write a seeded solution_outline.md and return its path."""
    plan_dir = base_dir / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    bullets = '\n'.join(f'- `{p}` (write-replace)' for p in affected_paths)
    path = plan_dir / 'solution_outline.md'
    path.write_text(
        f'# Solution: Consult workflow fixture\n'
        f'\n'
        f'plan_id: {plan_id}\n'
        f'\n'
        f'## Deliverables\n'
        f'\n'
        f'### 1. Seeded deliverable\n'
        f'\n'
        f'**Affected files:**\n'
        f'{bullets}\n',
        encoding='utf-8',
    )
    return path


def _run_consult(base_dir, plan_id):
    """Invoke the consult verb through the real executor, without PYTHONPATH.

    Dropping ``PYTHONPATH`` is load-bearing: it proves the handler's
    cross-skill imports resolve under a genuine
    ``python3 .plan/execute-script.py`` invocation rather than under the test
    harness's own path construction.
    """
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['PLAN_BASE_DIR'] = str(base_dir)
    env['PLAN_DIR_NAME'] = PLAN_DIR_NAME
    return subprocess.run(
        [sys.executable, str(EXECUTOR), NOTATION, 'consult', '--plan-id', plan_id],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=120,
        env=env,
    )


def _artifact_path(base_dir, plan_id):
    """Resolve the machine record's path for a seeded plan."""
    return base_dir.joinpath('plans', plan_id, *ARTIFACT_RELPATH)


class TestIntersectingPlanSurfacesItsLesson:
    """D3(a) — an intersecting plan sees the lesson naming its component."""

    def test_intersecting_plan_surfaces_the_seeded_lesson(self, tmp_path):
        """The seeded lesson is returned through the real executor path."""
        _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        _seed_outline(tmp_path, 'intersecting-plan', [INTERSECTING_PATH])

        completed = _run_consult(tmp_path, 'intersecting-plan')

        assert completed.returncode == 0, completed.stderr
        data = parse_toon(completed.stdout)
        assert data['status'] == 'success'
        assert data['components'] == [INTERSECTING_COMPONENT]
        assert data['surfaced_count'] == 1
        assert data['surfaced'][0]['lesson_id'] == INTERSECTING_LESSON_ID

    def test_cross_skill_imports_resolve_without_pythonpath(self, tmp_path):
        """The handler's cross-skill imports resolve under the executor alone.

        ``_run_consult`` strips ``PYTHONPATH``; a successful parse of the
        deliverables section proves ``_plan_parsing`` (owned by
        ``manage-solution-outline``) was importable from ``manage-lessons``.
        """
        _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        _seed_outline(tmp_path, 'import-plan', [INTERSECTING_PATH])

        completed = _run_consult(tmp_path, 'import-plan')

        assert completed.returncode == 0, completed.stderr
        assert 'ModuleNotFoundError' not in completed.stderr
        assert 'Traceback' not in completed.stderr
        data = parse_toon(completed.stdout)
        # A non-empty components list can only come from a parsed Deliverables
        # section, so the cross-skill parser import genuinely resolved.
        assert data['components'] == [INTERSECTING_COMPONENT]

    def test_only_the_edited_component_is_surfaced(self, tmp_path):
        """A lesson on a component the plan does not edit stays out."""
        _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        _seed_lesson(tmp_path, SECOND_LESSON_ID, 'plan-marshall:phase-4-plan')
        _seed_outline(tmp_path, 'scoped-plan', [INTERSECTING_PATH])

        completed = _run_consult(tmp_path, 'scoped-plan')

        data = parse_toon(completed.stdout)
        assert [row['lesson_id'] for row in data['surfaced']] == [INTERSECTING_LESSON_ID]


class TestNonIntersectingPlanCostsNothing:
    """D3(b) — a non-intersecting plan completes with zero surfaced."""

    def test_non_intersecting_plan_reports_zero(self, tmp_path):
        """The consult succeeds with surfaced_count 0, not an error."""
        _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        _seed_outline(tmp_path, 'non-intersecting-plan', [NON_INTERSECTING_PATH])

        completed = _run_consult(tmp_path, 'non-intersecting-plan')

        assert completed.returncode == 0, completed.stderr
        data = parse_toon(completed.stdout)
        assert data['status'] == 'success'
        assert data['surfaced_count'] == 0
        assert data['total_matched'] == 0
        assert data['truncated'] is False

    def test_non_intersecting_plan_adds_only_the_machine_record(self, tmp_path):
        """No dispatch, envelope, or prompt artifact is produced — one file."""
        _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        outline = _seed_outline(tmp_path, 'quiet-plan', [NON_INTERSECTING_PATH])
        plan_dir = outline.parent

        _run_consult(tmp_path, 'quiet-plan')

        produced = sorted(
            str(p.relative_to(plan_dir)) for p in plan_dir.rglob('*') if p.is_file()
        )
        assert produced == ['solution_outline.md', 'work/lessons-consult.toon']


class TestSurfacedSetIsDurablyRecorded:
    """D3(c) — the artifact makes the surfaced set recoverable and honest."""

    def test_artifact_enumerates_exactly_the_surfaced_ids(self, tmp_path):
        """The record is readable without re-running the consult."""
        _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        _seed_lesson(tmp_path, SECOND_LESSON_ID, INTERSECTING_COMPONENT)
        _seed_outline(tmp_path, 'recorded-plan', [INTERSECTING_PATH])

        completed = _run_consult(tmp_path, 'recorded-plan')

        artifact = _artifact_path(tmp_path, 'recorded-plan')
        assert artifact.exists()
        recorded = parse_toon(artifact.read_text(encoding='utf-8'))
        returned = parse_toon(completed.stdout)
        assert [row['lesson_id'] for row in recorded['surfaced']] == [
            INTERSECTING_LESSON_ID,
            SECOND_LESSON_ID,
        ]
        assert recorded['surfaced_count'] == returned['surfaced_count']

    def test_zero_match_artifact_is_present_and_says_zero(self, tmp_path):
        """'Fired and matched nothing' is recorded, not silent."""
        _seed_outline(tmp_path, 'zero-plan', [NON_INTERSECTING_PATH])

        _run_consult(tmp_path, 'zero-plan')

        artifact = _artifact_path(tmp_path, 'zero-plan')
        assert artifact.exists()
        recorded = parse_toon(artifact.read_text(encoding='utf-8'))
        assert recorded['surfaced_count'] == 0

    def test_absent_artifact_distinguishes_a_consult_that_never_fired(self, tmp_path):
        """A plan the consult never ran against has no record at all."""
        _seed_outline(tmp_path, 'ran-plan', [NON_INTERSECTING_PATH])
        _seed_outline(tmp_path, 'never-ran-plan', [NON_INTERSECTING_PATH])

        _run_consult(tmp_path, 'ran-plan')

        assert _artifact_path(tmp_path, 'ran-plan').exists()
        assert not _artifact_path(tmp_path, 'never-ran-plan').exists()


class TestSurfacedLessonIsNotApplied:
    """D3(d) — presented, never applied: asserted by mutation-freedom."""

    def test_seeded_lesson_files_are_byte_identical(self, tmp_path):
        """The corpus is untouched by the consult."""
        first = _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        second = _seed_lesson(tmp_path, SECOND_LESSON_ID, INTERSECTING_COMPONENT)
        _seed_outline(tmp_path, 'immutable-corpus-plan', [INTERSECTING_PATH])
        before = {p: p.read_bytes() for p in (first, second)}

        _run_consult(tmp_path, 'immutable-corpus-plan')

        for path, content in before.items():
            assert path.read_bytes() == content

    def test_solution_outline_is_unaltered(self, tmp_path):
        """No deliverable is revised by the consult itself."""
        _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        outline = _seed_outline(tmp_path, 'immutable-outline-plan', [INTERSECTING_PATH])
        before = outline.read_bytes()

        _run_consult(tmp_path, 'immutable-outline-plan')

        assert outline.read_bytes() == before

    def test_no_qgate_finding_is_written(self, tmp_path):
        """The consult emits no findings — surfacing is not a quality failure."""
        _seed_lesson(tmp_path, INTERSECTING_LESSON_ID, INTERSECTING_COMPONENT)
        outline = _seed_outline(tmp_path, 'no-findings-plan', [INTERSECTING_PATH])

        _run_consult(tmp_path, 'no-findings-plan')

        assert not (outline.parent / 'artifacts').exists()
