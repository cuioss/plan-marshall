#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``consult`` subcommand of manage-lessons.py.

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


from _consult_fixtures import (
    OUTLINE_COMPONENT,
    OUTLINE_LESSON_IDS,
    OUTLINE_SKILL_PATH,
    PLAN_ID,
    SOLUTION_OUTLINE_COMPONENT,
    SOLUTION_OUTLINE_LESSON_ID,
    SOLUTION_OUTLINE_SKILL_PATH,
    _consult,
    _seed_lesson,
    _write_outline,
)
from _lessons_helpers import SCRIPT_PATH
from toon_parser import parse_toon

from conftest import run_script


class TestDeterministicOrdering:
    """The union is ordered by (component, lesson_id) — never filesystem order."""

    def test_ordered_by_component_then_lesson_id(self, tmp_path):
        """Components sort ascending; lessons sort ascending within a component."""
        # Seed in reverse of the expected output order.
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[2], OUTLINE_COMPONENT)
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], OUTLINE_COMPONENT)
        _seed_lesson(tmp_path, SOLUTION_OUTLINE_LESSON_ID, SOLUTION_OUTLINE_COMPONENT)
        # Declare the phase-3-outline path FIRST so document order differs from
        # the sorted component order the result must carry.
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH, SOLUTION_OUTLINE_SKILL_PATH])

        result = _consult(tmp_path)

        assert result['components'] == [SOLUTION_OUTLINE_COMPONENT, OUTLINE_COMPONENT]
        assert [(row['component'], row['lesson_id']) for row in result['surfaced']] == [
            (SOLUTION_OUTLINE_COMPONENT, SOLUTION_OUTLINE_LESSON_ID),
            (OUTLINE_COMPONENT, OUTLINE_LESSON_IDS[0]),
            (OUTLINE_COMPONENT, OUTLINE_LESSON_IDS[2]),
        ]


class TestCapDisclosure:
    """A binding cap always discloses truncation plus the untruncated total."""

    def test_binding_cap_reports_truncated_and_total_matched(self, tmp_path):
        """Three matches capped at two report truncated with total_matched=3."""
        for lesson_id in OUTLINE_LESSON_IDS[:3]:
            _seed_lesson(tmp_path, lesson_id, OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path, max_per_component=2)

        assert result['truncated'] is True
        assert result['total_matched'] == 3
        assert result['surfaced_count'] == 2

    def test_binding_cap_keeps_the_deterministic_head(self, tmp_path):
        """Truncation keeps the lowest lesson ids, not an arbitrary subset."""
        for lesson_id in OUTLINE_LESSON_IDS[:3]:
            _seed_lesson(tmp_path, lesson_id, OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path, max_per_component=2)

        assert [row['lesson_id'] for row in result['surfaced']] == list(OUTLINE_LESSON_IDS[:2])

    def test_non_binding_cap_reports_untruncated(self, tmp_path):
        """A cap above the match count leaves truncated false and the set whole."""
        for lesson_id in OUTLINE_LESSON_IDS[:3]:
            _seed_lesson(tmp_path, lesson_id, OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path, max_per_component=25)

        assert result['truncated'] is False
        assert result['total_matched'] == 3
        assert result['surfaced_count'] == 3

    def test_cap_is_per_component_not_global(self, tmp_path):
        """The cap binds per component, so two components each keep their head."""
        for lesson_id in OUTLINE_LESSON_IDS[:2]:
            _seed_lesson(tmp_path, lesson_id, OUTLINE_COMPONENT)
        _seed_lesson(tmp_path, SOLUTION_OUTLINE_LESSON_ID, SOLUTION_OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH, SOLUTION_OUTLINE_SKILL_PATH])

        result = _consult(tmp_path, max_per_component=1)

        assert result['surfaced_count'] == 2
        assert result['total_matched'] == 3
        assert result['truncated'] is True

    def test_negative_cap_is_rejected_fail_closed(self, tmp_path):
        """A negative cap is a structured error, never a silently-clamped run.

        Without the guard, ``len(rows) > -1`` is true for an empty list (so
        ``truncated`` is set spuriously) and ``rows[:-1]`` drops the trailing
        row instead of capping from the front — a green-looking result that
        silently under-reports. Fail closed instead (ADR-009).
        """
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path, max_per_component=-1)

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_cap'
        assert 'surfaced' not in result


class TestArtifactWrite:
    """The machine record is written and distinguishes 'no match' from 'no consult'."""

    def test_artifact_enumerates_exactly_the_surfaced_ids(self, tmp_path):
        """work/lessons-consult.toon carries the same ids as the return value."""
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], OUTLINE_COMPONENT)
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[1], OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path)

        artifact = tmp_path / 'plans' / PLAN_ID / 'work' / 'lessons-consult.toon'
        assert artifact.exists()
        assert result['artifact_path'] == str(artifact.resolve())
        recorded = parse_toon(artifact.read_text(encoding='utf-8'))
        assert [row['lesson_id'] for row in recorded['surfaced']] == [
            row['lesson_id'] for row in result['surfaced']
        ]

    def test_zero_match_still_writes_the_artifact(self, tmp_path):
        """A present artifact with surfaced_count 0 means 'fired, matched nothing'."""
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        _consult(tmp_path)

        artifact = tmp_path / 'plans' / PLAN_ID / 'work' / 'lessons-consult.toon'
        assert artifact.exists()
        recorded = parse_toon(artifact.read_text(encoding='utf-8'))
        assert recorded['surfaced_count'] == 0

    def test_no_artifact_when_outline_is_missing(self, tmp_path):
        """The fail-closed path writes nothing, so absence still means 'never fired'."""
        (tmp_path / 'plans' / PLAN_ID).mkdir(parents=True)

        _consult(tmp_path)

        artifact = tmp_path / 'plans' / PLAN_ID / 'work' / 'lessons-consult.toon'
        assert not artifact.exists()


class TestMutationFreedom:
    """The consult is read-only over the corpus and over the outline."""

    def test_lesson_files_and_outline_are_unchanged(self, tmp_path):
        """Neither the seeded lessons nor the outline are rewritten."""
        lesson_path = _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], OUTLINE_COMPONENT)
        outline_path = _write_outline(tmp_path, [OUTLINE_SKILL_PATH])
        lesson_before = lesson_path.read_bytes()
        outline_before = outline_path.read_bytes()

        _consult(tmp_path)

        assert lesson_path.read_bytes() == lesson_before
        assert outline_path.read_bytes() == outline_before

    def test_no_findings_are_written(self, tmp_path):
        """The consult emits no Q-Gate findings — its only write is the artifact."""
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        _consult(tmp_path)

        findings_dir = tmp_path / 'plans' / PLAN_ID / 'artifacts' / 'findings'
        assert not findings_dir.exists()


class TestConsultCli:
    """CLI plumbing: the subcommand is registered and carries the documented default."""

    def test_cli_surfaces_matching_lesson(self, tmp_path):
        """The consult verb round-trips through the argparse entry point."""
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = run_script(
            SCRIPT_PATH,
            'consult',
            '--plan-id',
            PLAN_ID,
            env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['surfaced_count'] == 1
        assert data['components'] == [OUTLINE_COMPONENT]

    def test_cli_default_cap_is_twenty_five(self, tmp_path):
        """Omitting --max-per-component applies the documented default of 25."""
        for lesson_id in OUTLINE_LESSON_IDS:
            _seed_lesson(tmp_path, lesson_id, OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = run_script(
            SCRIPT_PATH,
            'consult',
            '--plan-id',
            PLAN_ID,
            env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
        )

        data = result.toon()
        assert data['surfaced_count'] == len(OUTLINE_LESSON_IDS)
        assert data['truncated'] is False

    def test_cli_honours_explicit_cap(self, tmp_path):
        """An explicit --max-per-component binds and discloses truncation."""
        for lesson_id in OUTLINE_LESSON_IDS[:3]:
            _seed_lesson(tmp_path, lesson_id, OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = run_script(
            SCRIPT_PATH,
            'consult',
            '--plan-id',
            PLAN_ID,
            '--max-per-component',
            '1',
            env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
        )

        data = result.toon()
        assert data['truncated'] is True
        assert data['total_matched'] == 3
        assert data['surfaced_count'] == 1

    def test_cli_rejects_invalid_plan_id(self, tmp_path):
        """A malformed plan_id is rejected by the canonical validator."""
        result = run_script(
            SCRIPT_PATH,
            'consult',
            '--plan-id',
            'Not A Plan',
            env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
        )

        data = result.toon_or_error()
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_plan_id'
