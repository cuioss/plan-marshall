#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the trivial getter/setter CRUD subcommands of manage-lessons.py."""


from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
from _lessons_crud_fixtures import _seed_active_lesson, _seed_superseded_lesson, cmd_set_title


# =============================================================================
# Tier 2: cmd_set_title — happy paths
# =============================================================================


class TestCmdSetTitleActive:
    """Happy path on an active lesson — case (a)."""

    def test_rewrites_h1_on_active_lesson(self, tmp_path):
        """Rewriting the H1 of an active lesson must update only the H1 line.

        Returns ``{status, lesson_id, old_title, new_title, file}``. The
        on-disk content must keep frontmatter and body verbatim while
        replacing the H1 line.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        path = _seed_active_lesson(
            lessons_dir,
            lesson_id='2025-01-01-01-001',
            title='Old Title',
            body='Body paragraph one.\n',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-001', title='New Title')
            )

        assert result['status'] == 'success'
        assert result['lesson_id'] == '2025-01-01-01-001'
        assert result['old_title'] == 'Old Title'
        assert result['new_title'] == 'New Title'
        assert Path(result['file']) == path.resolve()

        updated = path.read_text(encoding='utf-8')
        # New H1 present
        assert '# New Title' in updated
        # Old H1 gone
        assert '# Old Title' not in updated
        # Body preserved verbatim
        assert 'Body paragraph one.' in updated


# =============================================================================
# Tier 2: cmd_set_title — superseded lifecycle (case b)
# =============================================================================


class TestCmdSetTitleSuperseded:
    """Happy path on a superseded lesson — case (b)."""

    def test_rewrites_h1_on_superseded_lesson(self, tmp_path):
        """Superseded lessons remain rewriteable.

        ``cmd_set_title`` does not gate on lifecycle status — only ``not_found``
        and malformed-lesson states fail. The superseded stub's H1 must be
        rewriteable so aggregate workflows can rename absorbed stubs.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        path = _seed_superseded_lesson(
            lessons_dir,
            lesson_id='2025-01-01-01-002',
            title='Old Superseded',
            superseded_by='2025-01-01-01-099',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-002', title='Renamed Stub')
            )

        assert result['status'] == 'success'
        assert result['old_title'] == 'Old Superseded'
        assert result['new_title'] == 'Renamed Stub'

        updated = path.read_text(encoding='utf-8')
        assert '# Renamed Stub' in updated
        # Frontmatter still flags the lesson as superseded
        assert 'status=superseded' in updated
        assert 'superseded_by=2025-01-01-01-099' in updated


# =============================================================================
# Tier 2: cmd_set_title — error path (case c)
# =============================================================================


class TestCmdSetTitleNotFound:
    """Unknown lesson id returns ``status: error, error: not_found`` — case (c)."""

    def test_unknown_lesson_id_returns_not_found(self, tmp_path):
        """When the lesson markdown file does not exist on disk, the function
        must surface ``status: error`` and ``error: not_found`` rather than
        creating a new file.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_title(
                Namespace(lesson_id='9999-12-31-23-999', title='Whatever')
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'
        assert result['lesson_id'] == '9999-12-31-23-999'
        # No file should have been created
        assert not (lessons_dir / '9999-12-31-23-999.md').exists()


# =============================================================================
# Tier 2: cmd_set_title — idempotency (case d)
# =============================================================================


class TestCmdSetTitleIdempotency:
    """Running with the same title twice must be a no-op — case (d)."""

    def test_same_title_twice_is_noop(self, tmp_path):
        """Idempotent re-run: the second call returns ``status: success`` with
        ``old_title == new_title`` and does not rewrite the file (mtime
        preserved).
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        path = _seed_active_lesson(
            lessons_dir,
            lesson_id='2025-01-01-01-003',
            title='Stable Title',
            body='Body content.\n',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            first = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-003', title='Stable Title')
            )

        # Capture mtime AFTER the first (no-op) call so the comparison
        # measures whether the SECOND call writes — the first call may or
        # may not write depending on the implementation, but the second
        # must not.
        mtime_after_first = path.stat().st_mtime_ns

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            second = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-003', title='Stable Title')
            )

        assert first['status'] == 'success'
        assert first['old_title'] == 'Stable Title'
        assert first['new_title'] == 'Stable Title'

        assert second['status'] == 'success'
        assert second['old_title'] == 'Stable Title'
        assert second['new_title'] == 'Stable Title'

        # Second call MUST NOT rewrite the file — mtime unchanged
        assert path.stat().st_mtime_ns == mtime_after_first

        # Body preserved
        updated = path.read_text(encoding='utf-8')
        assert '# Stable Title' in updated
        assert 'Body content.' in updated


# =============================================================================
# Tier 2: cmd_set_title — frontmatter preservation (case e)
# =============================================================================


class TestCmdSetTitleFrontmatterUntouched:
    """Frontmatter must not be touched by the H1 rewrite — case (e)."""

    def test_frontmatter_is_not_modified(self, tmp_path):
        """All ``key=value`` frontmatter lines, blank separator line, and
        body content surrounding the H1 must round-trip byte-for-byte except
        for the rewritten H1 line itself.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        # Use extra frontmatter to verify multi-line frontmatter survives
        path = _seed_active_lesson(
            lessons_dir,
            lesson_id='2025-01-01-01-004',
            title='Old',
            body='Existing body.\n\n## Section\n\nMore content.\n',
            extra_frontmatter='bundle=plan-marshall\nseverity=high\n',
        )
        original_content = path.read_text(encoding='utf-8')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_title(
                Namespace(lesson_id='2025-01-01-01-004', title='New')
            )

        assert result['status'] == 'success'

        updated = path.read_text(encoding='utf-8')
        # Verify frontmatter preserved verbatim by checking each key=value line
        for fm_line in (
            'id=2025-01-01-01-004',
            'component=test-component',
            'category=bug',
            'created=2025-01-01',
            'status=active',
            'bundle=plan-marshall',
            'severity=high',
        ):
            assert fm_line in updated, f'frontmatter line missing: {fm_line}'

        # Body preserved verbatim
        assert 'Existing body.' in updated
        assert '## Section' in updated
        assert 'More content.' in updated

        # The only diff between original and updated should be the H1 swap
        assert '# Old' not in updated
        assert '# New' in updated

        # Stronger check: replacing the new H1 with the old H1 should yield
        # the original content byte-for-byte.
        round_tripped = updated.replace('# New', '# Old', 1)
        assert round_tripped == original_content
