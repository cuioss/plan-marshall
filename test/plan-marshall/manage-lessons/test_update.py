#!/usr/bin/env python3
"""Tests for the ``update`` subcommand of manage-lessons.py.

Covers ``cmd_update`` direct invocation: updating the ``component`` field
in-place and the not-found error path.
"""

from argparse import Namespace
from unittest.mock import patch

from _lessons_helpers import cmd_update


class TestCmdUpdate:
    """Test cmd_update direct invocation."""

    def test_update_component(self, tmp_path):
        """Should update component field."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=old-component
category=bug
created=2025-01-01

# Test Lesson

Body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_update(Namespace(lesson_id='2025-01-01-001', component='new-component', category=None))

        assert result['status'] == 'success'
        assert result['field'] == 'component'
        assert result['value'] == 'new-component'

        # Verify file was updated
        updated_content = (lessons_dir / '2025-01-01-001.md').read_text()
        assert 'component=new-component' in updated_content

    def test_update_nonexistent_lesson_fails(self, tmp_path):
        """Should fail when updating non-existent lesson."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_update(Namespace(lesson_id='nonexistent', component='x', category=None))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'
