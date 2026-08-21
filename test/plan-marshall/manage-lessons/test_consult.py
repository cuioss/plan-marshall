#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``consult`` subcommand of manage-lessons.py."""


from _consult_fixtures import (
    OUTLINE_COMPONENT,
    OUTLINE_LESSON_IDS,
    OUTLINE_SKILL_PATH,
    PLAN_ID,
    TEST_PATH,
    _consult,
    _seed_lesson,
    _write_outline,
)
from _lessons_helpers import SCRIPT_PATH

from conftest import run_script


class TestConsultOutlineResolution:
    """The outline is the sole input; a missing one is a hard, fail-closed error."""

    def test_missing_outline_returns_outline_not_found(self, tmp_path):
        """A plan with no solution_outline.md errors instead of succeeding empty."""
        (tmp_path / 'plans' / PLAN_ID).mkdir(parents=True)

        result = _consult(tmp_path)

        assert result['status'] == 'error'
        assert result['error'] == 'outline_not_found'
        assert result['plan_id'] == PLAN_ID
        assert 'surfaced' not in result

    def test_missing_plan_dir_returns_outline_not_found(self, tmp_path):
        """A plan directory that does not exist yields the same fail-closed error."""
        result = _consult(tmp_path)

        assert result['status'] == 'error'
        assert result['error'] == 'outline_not_found'

    def test_plan_id_with_traversal_is_rejected(self, tmp_path):
        """A plan_id carrying path separators is refused before any path build."""
        result = _consult(tmp_path, plan_id='../escape')

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_id'


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


class TestPathToComponentMapping:
    """Affected-file paths map to bundle:skill components; leftovers are disclosed."""

    def test_skill_path_maps_to_bundle_skill_component(self, tmp_path):
        """A marketplace skill path derives the {bundle}:{skill} component."""
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path)

        assert result['status'] == 'success'
        assert result['components'] == [OUTLINE_COMPONENT]

    def test_non_matching_path_is_reported_as_unmapped(self, tmp_path):
        """A path outside marketplace/bundles/*/skills/*/ lands in unmapped_paths."""
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH, TEST_PATH])

        result = _consult(tmp_path)

        assert result['components'] == [OUTLINE_COMPONENT]
        assert result['unmapped_paths'] == [TEST_PATH]

    def test_skill_directory_root_without_child_is_unmapped(self, tmp_path):
        """A path that stops at the skill directory names no file inside it."""
        skill_dir = 'marketplace/bundles/plan-marshall/skills/phase-3-outline'
        _write_outline(tmp_path, [skill_dir])

        result = _consult(tmp_path)

        assert result['components'] == []
        assert result['unmapped_paths'] == [skill_dir]

    def test_duplicate_paths_yield_one_component(self, tmp_path):
        """Two files in the same skill collapse to a single component entry."""
        sibling = 'marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md'
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH, sibling])

        result = _consult(tmp_path)

        assert result['components'] == [OUTLINE_COMPONENT]
