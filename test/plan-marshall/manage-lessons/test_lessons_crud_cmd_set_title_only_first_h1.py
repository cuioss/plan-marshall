#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the trivial getter/setter CRUD subcommands of manage-lessons.py."""


from argparse import Namespace
from unittest.mock import patch
from _lessons_crud_fixtures import _seed_active_lesson, cmd_set_title


# =============================================================================
# Tier 2: cmd_set_title — only first H1 rewritten (case f)
# =============================================================================


class TestCmdSetTitleOnlyFirstH1:
    """Only the first H1 outside fenced code blocks is rewritten — case (f).

    Three sub-cases:
    - A second ``# `` line later in the body must remain untouched.
    - A ``# `` line inside a triple-backtick fenced code block must be
      ignored entirely (not picked as the H1, not rewritten).
    - When the first ``# `` line is inside a fence and a real ``# `` H1
      follows after the fence closes, the post-fence H1 is rewritten and
      the in-fence ``# `` line stays verbatim.
    """

    def test_only_first_h1_in_body_is_rewritten(self, tmp_path):
        """A document with two ``# `` lines (both outside fences) — only the
        first must be rewritten.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        path = _seed_active_lesson(
            lessons_dir,
            lesson_id='2025-01-01-01-005',
            title='First Title',
            body='Some intro.\n\n# Second H1 In Body\n\nMore content.\n',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-005', title='Rewritten First')
            )

        assert result['status'] == 'success'
        assert result['old_title'] == 'First Title'
        assert result['new_title'] == 'Rewritten First'

        updated = path.read_text(encoding='utf-8')
        # First H1 rewritten
        assert '# Rewritten First' in updated
        assert '# First Title' not in updated
        # Second ``# `` in body MUST remain untouched
        assert '# Second H1 In Body' in updated

    def test_h1_inside_fenced_code_block_is_skipped(self, tmp_path):
        """A ``# `` line inside a triple-backtick fenced code block must NOT
        be picked as the H1; the rewriter must seek the next outside-fence
        ``# `` line.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        path = lessons_dir / '2025-01-01-01-006.md'
        # Construct a lesson where a fenced code block APPEARS before the
        # real H1 — the rewriter must close the fence first, then find the
        # real H1 line.
        content = (
            'id=2025-01-01-01-006\n'
            'component=test-component\n'
            'category=bug\n'
            'created=2025-01-01\n'
            'status=active\n'
            '\n'
            '```\n'
            '# This Looks Like H1 But Is Code\n'
            '```\n'
            '\n'
            '# Real H1 Title\n'
            '\n'
            'Body text.\n'
        )
        path.write_text(content, encoding='utf-8')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-006', title='Real Rewritten')
            )

        assert result['status'] == 'success'
        assert result['old_title'] == 'Real H1 Title'
        assert result['new_title'] == 'Real Rewritten'

        updated = path.read_text(encoding='utf-8')
        # In-fence ``# `` line preserved verbatim
        assert '# This Looks Like H1 But Is Code' in updated
        # Real H1 rewritten
        assert '# Real Rewritten' in updated
        assert '# Real H1 Title' not in updated

    def test_first_outside_fence_h1_when_multiple_fences(self, tmp_path):
        """A document with multiple fenced blocks containing ``# `` lines —
        the rewriter must only touch the first OUTSIDE-FENCE ``# `` line.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        path = lessons_dir / '2025-01-01-01-007.md'
        content = (
            'id=2025-01-01-01-007\n'
            'component=test-component\n'
            'category=bug\n'
            'created=2025-01-01\n'
            'status=active\n'
            '\n'
            '# Outside H1\n'
            '\n'
            '```\n'
            '# Inside Fence A\n'
            '```\n'
            '\n'
            '## Sub-section\n'
            '\n'
            '```python\n'
            '# Inside Fence B\n'
            '```\n'
            '\n'
            '# Another Outside H1\n'
        )
        path.write_text(content, encoding='utf-8')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-007', title='Rewritten')
            )

        assert result['status'] == 'success'
        assert result['old_title'] == 'Outside H1'

        updated = path.read_text(encoding='utf-8')
        # First outside-fence H1 rewritten
        assert '# Rewritten' in updated
        assert '# Outside H1' not in updated
        # In-fence ``# `` lines preserved verbatim
        assert '# Inside Fence A' in updated
        assert '# Inside Fence B' in updated
        # Second outside-fence H1 untouched
        assert '# Another Outside H1' in updated


# =============================================================================
# Tier 2: cmd_set_title — malformed lesson (no H1)
# =============================================================================


class TestCmdSetTitleMalformed:
    """A lesson markdown file with no ``# `` H1 line cannot be rewritten."""

    def test_lesson_without_h1_returns_malformed_error(self, tmp_path):
        """When the lesson has no outside-fence H1 line, ``cmd_set_title``
        must return ``status: error, error: malformed_lesson`` instead of
        appending a new H1 or silently succeeding.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        path = lessons_dir / '2025-01-01-01-008.md'
        # No H1 anywhere — only frontmatter and a body paragraph.
        path.write_text(
            'id=2025-01-01-01-008\n'
            'component=test-component\n'
            'category=bug\n'
            'created=2025-01-01\n'
            '\n'
            'Body without title.\n',
            encoding='utf-8',
        )
        original_content = path.read_text(encoding='utf-8')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-008', title='New Title')
            )

        assert result['status'] == 'error'
        assert result['error'] == 'malformed_lesson'
        assert result['lesson_id'] == '2025-01-01-01-008'

        # File must remain unchanged
        assert path.read_text(encoding='utf-8') == original_content
