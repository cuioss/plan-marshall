#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the trivial getter/setter CRUD subcommands of manage-lessons.py.

This module absorbs the four single-verb suites whose bodies were each small
enough that a dedicated file cost more navigation than it bought:

* ``get`` — ``cmd_get`` direct invocation (metadata retrieval, not-found) plus
  the Tier 3 subprocess check pinning ``read`` as an alias for ``get``
  (TestCmdGet, TestCliReadAlias).
* ``list`` — core ``cmd_list`` behaviour (empty dir, basic listing,
  component/category filters, ``--full`` body inclusion, default no-body
  exclusion), the ``--status`` filter matrix, and legacy ``YYYY-MM-DD-NNN``
  filename compatibility across both the list and get read paths
  (TestCmdList, TestLegacyFormatCompatibility, TestCmdListStatusFilter).
* ``set-title`` — ``cmd_set_title`` H1 rewriting: active and superseded
  lessons, the not-found and malformed-lesson error paths, idempotency,
  frontmatter preservation, and first-outside-fence-H1 selection
  (TestCmdSetTitle*).
* ``set-body`` — ``cmd_set_body`` body overwrite via the canonical ``--file``
  form and the secondary ``--content`` form, the mutual-exclusion guard, the
  file-not-found / file-read-error guards, and frontmatter preservation
  (TestCmdSetBody).

The complex-verb suites (``supersede``, ``convert_to_plan``,
``restore_from_plan``, ``from_error``, ``add``, ``remove``, ``update``) keep
their own files — only the trivial getter/setter verbs are co-located here.

All four absorbed suites now share ONE module-load path: ``_lessons_helpers``
loads ``manage-lessons.py`` exactly once and re-exports the ``cmd_*``
callables. ``cmd_set_title`` is not among the helper's re-exports, so it is
resolved off the shared ``_mod`` handle rather than by re-loading the script —
the previous ``test_set_title.py`` paid a second ``spec_from_file_location``
load of the same production module under a separate name.
"""


from argparse import Namespace
from unittest.mock import patch
from _lessons_helpers import SCRIPT_PATH, cmd_get, cmd_list
from conftest import run_script
from _lessons_crud_fixtures import _seed_cli_lesson


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


class TestCliReadAlias:
    """Subprocess test pinning ``read`` as an alias for the ``get`` subcommand."""

    def test_cli_read_alias_succeeds(self, tmp_path):
        """``manage-lessons read`` succeeds via the CLI for an existing lesson."""
        _seed_cli_lesson(tmp_path, '2025-01-01-01-001', 'Test Lesson Title')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'read',
                '--lesson-id',
                '2025-01-01-01-001',
            )

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'title: Test Lesson Title' in result.stdout

    def test_cli_read_alias_matches_get(self, tmp_path):
        """``read`` and ``get`` produce identical payloads for the same lesson."""
        _seed_cli_lesson(tmp_path, '2025-01-01-01-001', 'Test Lesson Title')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            read_result = run_script(
                SCRIPT_PATH,
                'read',
                '--lesson-id',
                '2025-01-01-01-001',
            )
            get_result = run_script(
                SCRIPT_PATH,
                'get',
                '--lesson-id',
                '2025-01-01-01-001',
            )

        assert read_result.returncode == 0
        assert get_result.returncode == 0
        assert read_result.returncode == get_result.returncode
        assert read_result.stdout == get_result.stdout


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
