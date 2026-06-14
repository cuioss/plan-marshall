#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for the ``get`` subcommand of manage-lessons.py.

Covers ``cmd_get`` direct invocation: successful retrieval of metadata
fields and the not-found error path. Legacy-format-id read compatibility
for ``cmd_get`` lives in ``test_list.py`` (TestLegacyFormatCompatibility)
because the same fixtures exercise both the list and get read paths.

The ``read`` alias for ``get`` is pinned by a Tier 3 (subprocess) test in
``TestCliReadAlias``: invoking the script with ``read`` succeeds and
returns the identical payload to the canonical ``get`` subcommand.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from _lessons_helpers import SCRIPT_PATH, cmd_get
from conftest import run_script


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


def _seed_cli_lesson(tmp_path: Path, lesson_id: str, title: str) -> None:
    """Seed a minimal lesson file under ``{tmp_path}/lessons-learned``."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    (lessons_dir / f'{lesson_id}.md').write_text(
        f'id={lesson_id}\ncomponent=test-component\ncategory=bug\n'
        f'created=2025-01-01\n\n# {title}\n\nThis is the lesson body.\n',
        encoding='utf-8',
    )


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
