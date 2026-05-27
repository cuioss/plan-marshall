#!/usr/bin/env python3
"""Tests for the ``from-error`` subcommand of manage-lessons.py.

Covers ``cmd_from_error`` direct invocation: successful creation of a
lesson from a JSON error context, and the invalid-JSON error path.
``status=active`` frontmatter seeding for the from-error path is covered
under ``test_add.py`` (TestStatusFrontmatterOnAdd), and the collision-safe
id-allocation regression for from-error lives in ``test_add.py``
(TestCollisionSafeAllocation) — both belong with the shared
``_allocate_and_write_scaffold`` contract.
"""

import json
from argparse import Namespace
from unittest.mock import patch

from _lessons_helpers import cmd_from_error


class TestCmdFromError:
    """Test cmd_from_error direct invocation."""

    def test_from_error_creates_lesson(self, tmp_path):
        """Should create lesson from error context JSON."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps(
            {
                'component': 'maven-build',
                'error': 'Build failed due to missing dependency',
                'solution': 'Add the missing dependency to pom.xml',
            }
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'success'
        assert result['created_from'] == 'error_context'

    def test_from_error_invalid_json_fails(self, tmp_path):
        """Should fail with invalid JSON context."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context='not valid json'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_json'
