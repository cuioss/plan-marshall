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
    TEST_PATH,
    _consult,
    _seed_lesson,
    _write_outline,
)


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


class TestComponentFiltering:
    """Only active lessons whose component is EXACTLY a derived one are surfaced."""

    def test_matching_component_lesson_is_surfaced(self, tmp_path):
        """A lesson naming the derived component appears in surfaced[]."""
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path)

        assert result['surfaced_count'] == 1
        row = result['surfaced'][0]
        assert row['lesson_id'] == OUTLINE_LESSON_IDS[0]
        assert row['component'] == OUTLINE_COMPONENT
        assert row['title'] == f'Title for {OUTLINE_LESSON_IDS[0]}'

    def test_bare_bundle_component_is_not_surfaced(self, tmp_path):
        """Matching is exact string equality — a bare bundle does not expand."""
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], 'plan-marshall')
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path)

        assert result['surfaced_count'] == 0
        assert result['total_matched'] == 0

    def test_different_skill_component_is_not_surfaced(self, tmp_path):
        """A lesson on a sibling skill the plan does not edit is excluded."""
        _seed_lesson(tmp_path, SOLUTION_OUTLINE_LESSON_ID, SOLUTION_OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path)

        assert result['surfaced_count'] == 0

    def test_superseded_lesson_is_not_surfaced(self, tmp_path):
        """Only active lessons are surfaced; a superseded stub is skipped."""
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[0], OUTLINE_COMPONENT, status='superseded')
        _seed_lesson(tmp_path, OUTLINE_LESSON_IDS[1], OUTLINE_COMPONENT)
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path)

        assert [row['lesson_id'] for row in result['surfaced']] == [OUTLINE_LESSON_IDS[1]]

    def test_missing_corpus_returns_zero_surfaced(self, tmp_path):
        """A plan whose components carry no lessons completes with zero surfaced."""
        _write_outline(tmp_path, [OUTLINE_SKILL_PATH])

        result = _consult(tmp_path)

        assert result['status'] == 'success'
        assert result['surfaced'] == []
        assert result['surfaced_count'] == 0
        assert result['truncated'] is False
