#!/usr/bin/env python3
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
        """Invoking convert-to-plan with --id and --plan-id must:

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
            result = cmd_convert_to_plan(
                Namespace(id=lesson_id, plan_id=plan_id)
            )

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
        assert destination.exists(), (
            f'phase-1-init expects the moved file at plans/{plan_id}/lesson-{lesson_id}.md'
        )
        assert destination.read_text() == lesson_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
