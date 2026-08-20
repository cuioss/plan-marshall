#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the trivial getter/setter CRUD subcommands of manage-lessons.py."""


from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
from _lessons_helpers import cmd_get, cmd_list
from _lessons_crud_fixtures import _seed_lesson_with_status


# =============================================================================
# Tier 2: cmd_get
# =============================================================================


class TestCmdGet:
    """Test cmd_get direct invocation."""

    def test_get_existing_lesson(self, tmp_path):
        """Should return lesson details."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson Title

This is the lesson body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_get(Namespace(lesson_id='2025-01-01-001'))

        assert result['status'] == 'success'
        assert result['component'] == 'test-component'
        assert result['category'] == 'bug'
        assert result['title'] == 'Test Lesson Title'

    def test_get_nonexistent_lesson(self, tmp_path):
        """Should return error for non-existent lesson."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_get(Namespace(lesson_id='nonexistent-id'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'


# =============================================================================
# Tier 2: cmd_list
# =============================================================================


class TestCmdList:
    """Test cmd_list direct invocation."""

    def test_list_empty_directory(self, tmp_path):
        """Should return empty list when no lessons exist."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        assert result['status'] == 'success'
        assert result['total'] == 0
        assert result['filtered'] == 0

    def test_list_with_lessons(self, tmp_path):
        """Should list existing lessons."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson Title

This is the lesson body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        assert result['status'] == 'success'
        assert result['total'] == 1
        assert result['filtered'] == 1

    def test_list_filter_by_component(self, tmp_path):
        """Should filter lessons by component."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson1 = """id=2025-01-01-001
component=component-a
category=bug
created=2025-01-01

# Lesson A
"""
        lesson2 = """id=2025-01-01-002
component=component-b
category=bug
created=2025-01-01

# Lesson B
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson1)
        (lessons_dir / '2025-01-01-002.md').write_text(lesson2)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component='component-a', category=None, full=False))

        assert result['status'] == 'success'
        assert result['total'] == 2
        assert result['filtered'] == 1

    def test_list_filter_by_category(self, tmp_path):
        """Should filter lessons by category."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson1 = """id=2025-01-01-001
component=test
category=bug
created=2025-01-01

# Bug Lesson
"""
        lesson2 = """id=2025-01-01-002
component=test
category=improvement
created=2025-01-01

# Improvement Lesson
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson1)
        (lessons_dir / '2025-01-01-002.md').write_text(lesson2)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category='bug', full=False))

        assert result['status'] == 'success'
        assert result['filtered'] == 1

    def test_list_full_includes_body_content(self, tmp_path):
        """Should include lesson body content when --full is set."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson Title

This is the lesson body with details.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=True))

        assert result['status'] == 'success'
        assert result['filtered'] == 1
        assert 'content' in result['lessons'][0]
        assert 'This is the lesson body with details.' in result['lessons'][0]['content']

    def test_list_without_full_excludes_body(self, tmp_path):
        """Should not include body content without --full."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson Title

Body content here.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        assert result['status'] == 'success'
        assert 'content' not in result['lessons'][0]


# =============================================================================
# Tier 2: cmd_list --status filter
# =============================================================================

class TestCmdListStatusFilter:
    """``cmd_list --status`` filter behaviour."""

    def _seed_three_statuses(self, lessons_dir: Path) -> None:
        _seed_lesson_with_status(lessons_dir, '2025-01-01-01-001', 'active', 'Active Lesson')
        _seed_lesson_with_status(lessons_dir, '2025-01-01-01-002', 'superseded', 'Superseded Lesson')
        _seed_lesson_with_status(lessons_dir, '2025-01-01-01-003', None, 'Legacy No Status')

    def test_default_excludes_superseded(self, tmp_path):
        """Default filter (``status=active``) hides superseded lessons; absent status treated as active."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_three_statuses(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, status='active', full=False))

        assert result['status'] == 'success'
        listed_ids = {entry['id'] for entry in result['lessons']}
        assert '2025-01-01-01-001' in listed_ids
        assert '2025-01-01-01-003' in listed_ids  # absent status ⇒ active
        assert '2025-01-01-01-002' not in listed_ids  # superseded hidden

    def test_status_all_returns_every_lesson(self, tmp_path):
        """``--status all`` returns every lesson regardless of lifecycle status."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_three_statuses(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, status='all', full=False))

        listed_ids = {entry['id'] for entry in result['lessons']}
        assert listed_ids == {
            '2025-01-01-01-001',
            '2025-01-01-01-002',
            '2025-01-01-01-003',
        }

    def test_status_superseded_returns_only_superseded(self, tmp_path):
        """``--status superseded`` returns only lessons with frontmatter ``status=superseded``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_three_statuses(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, status='superseded', full=False))

        listed_ids = {entry['id'] for entry in result['lessons']}
        assert listed_ids == {'2025-01-01-01-002'}

    def test_legacy_namespace_without_status_attr_defaults_to_active(self, tmp_path):
        """Backwards compatibility: a Namespace without a ``status`` attribute must default to ``active``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_three_statuses(lessons_dir)

        # Legacy Namespace without status field — older callers must still work.
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        listed_ids = {entry['id'] for entry in result['lessons']}
        assert '2025-01-01-01-002' not in listed_ids  # superseded still hidden
        assert '2025-01-01-01-001' in listed_ids
