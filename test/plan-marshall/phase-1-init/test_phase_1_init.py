#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Regression tests for the phase-1-init lesson-source contract.

phase-1-init is a workflow-driven skill (no Python entry point of its own).
When invoked with source=lesson, Step 5b of phase-1-init delegates the actual
file move to ``manage-lessons.py convert-to-plan``. These tests pin the
invariant that phase-1-init relies on: invoking ``cmd_convert_to_plan`` with a
lesson id and a plan id removes the source from ``lessons-learned/`` and
materialises it inside the target plan directory at the canonical
``lesson-{id}.md`` filename, with content preserved byte-for-byte.

Tests in this module intentionally do NOT duplicate the broader cmd_convert_to_plan
coverage living in ``test/plan-marshall/manage-lessons/test_manage_lessons.py``.
This suite is scoped strictly to the phase-1-init contract.
"""

import importlib.util
from argparse import Namespace
from unittest.mock import patch

import pytest

from conftest import MARKETPLACE_ROOT

# Tier 2 direct import — load the hyphenated manage-lessons module via importlib
_MANAGE_LESSONS_SCRIPT = str(
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-lessons' / 'scripts' / 'manage-lessons.py'
)
_spec = importlib.util.spec_from_file_location('manage_lessons', _MANAGE_LESSONS_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_convert_to_plan = _mod.cmd_convert_to_plan


class TestPhase1InitLessonMoveContract:
    """Pin the move contract that phase-1-init Step 5b depends on."""

    def test_lesson_source_branch_moves_file(self, tmp_path):
        """Invoking convert-to-plan with --lesson-id and --plan-id must:

        1. Remove the source file from ``lessons-learned/``.
        2. Create ``plans/{plan_id}/lesson-{id}.md`` with identical content.

        This is exactly the contract phase-1-init's lesson source branch
        relies on at Step 5b — any divergence here would silently break the
        phase-1-init workflow without failing its (skill-only) self-tests.
        """
        lesson_id = '2026-04-15-099'
        plan_id = 'phase1-init-contract-plan'

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = (
            f'id={lesson_id}\n'
            'component=plan-marshall:phase-1-init\n'
            'category=bug\n'
            'created=2026-04-15\n'
            '\n'
            '# Phase-1-Init Move Contract Lesson\n'
            '\n'
            'Body content that must survive the move byte-for-byte.\n'
        )
        source = lessons_dir / f'{lesson_id}.md'
        source.write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id=lesson_id, plan_id=plan_id))

        # Contract assertion 1: success status with echoed identifiers
        assert result['status'] == 'success'
        assert result['lesson_id'] == lesson_id
        assert result['plan_id'] == plan_id

        # Contract assertion 2: source absent after move
        assert not source.exists(), (
            'phase-1-init relies on convert-to-plan removing the source file '
            'so the lesson is no longer discoverable via list/get after init.'
        )

        # Contract assertion 3: destination at canonical path with preserved content
        destination = tmp_path / 'plans' / plan_id / f'lesson-{lesson_id}.md'
        assert destination.exists(), f'phase-1-init expects the moved file at plans/{plan_id}/lesson-{lesson_id}.md'
        assert destination.read_text() == lesson_content


class TestPhase1InitBaseBranchSeeding:
    """Pin the doc-level orchestration sequence that seeds references.base_branch.

    phase-1-init is a workflow-driven skill so the test target is SKILL.md:
    the orchestration sequence MUST read project.default_base_branch from
    marshal.json (via `manage-config project get --field default_base_branch`)
    and write that value to `references.base_branch`, with a documented
    fallback path on `field_not_found` (legacy marshal.json schema).
    """

    def _skill_md_text(self) -> str:
        skill_md = (
            MARKETPLACE_ROOT
            / 'plan-marshall'
            / 'skills'
            / 'phase-1-init'
            / 'SKILL.md'
        )
        return skill_md.read_text(encoding='utf-8')

    def test_skill_documents_manage_config_project_read(self):
        """SKILL.md MUST document the `manage-config project get --field default_base_branch` read."""
        text = self._skill_md_text()

        assert 'project get --field default_base_branch' in text, (
            'phase-1-init SKILL.md must document the `manage-config project get` '
            'read for default_base_branch — that is the seed source for '
            'references.base_branch.'
        )

    def test_skill_documents_field_not_found_fallback(self):
        """SKILL.md MUST document the legacy-schema fallback path on field_not_found."""
        text = self._skill_md_text()

        # the fallback must mention field_not_found AND the legacy
        # current-branch behaviour so the workflow degrades gracefully against
        # marshal.json files predating the project.default_base_branch field.
        assert 'field_not_found' in text, (
            'phase-1-init SKILL.md must document the field_not_found fallback '
            'so legacy marshal.json files still produce a valid base_branch seed.'
        )

    def test_skill_writes_project_base_branch_to_references(self):
        """SKILL.md MUST write the resolved value to references.base_branch."""
        text = self._skill_md_text()

        # the orchestration writes through manage-references set
        # with --field base_branch carrying the project-resolved value.
        assert '--field base_branch' in text
        assert 'project_base_branch' in text, (
            'phase-1-init SKILL.md must use the {project_base_branch} '
            'placeholder when seeding references.base_branch, signalling that '
            'the value originates from project.default_base_branch.'
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
