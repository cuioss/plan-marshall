#!/usr/bin/env python3
"""
Tests for the ``set-title`` subcommand of manage-lessons.py.

``cmd_set_title`` rewrites the first ``^# `` H1 line of a lesson markdown
file in place. The rewrite must:

- succeed on active lessons (a) and superseded lessons (b)
- return ``status: error, error: not_found`` for unknown ids (c)
- be idempotent — re-running with the same title is a no-op (d)
- never touch the ``key=value`` frontmatter header (e)
- only rewrite the FIRST H1, skipping ``# `` lines that appear inside
  fenced code blocks (f)

The tests use Tier 2 (direct import) invocation to exercise the function
without subprocess overhead. Lessons live under ``{tmp_path}/lessons-learned/``
which is the path returned by ``get_lessons_dir()`` when ``PLAN_BASE_DIR``
points at ``tmp_path``.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from conftest import MARKETPLACE_ROOT

# Tier 2 direct import - load hyphenated module via importlib
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-lessons' / 'scripts' / 'manage-lessons.py'

_spec = importlib.util.spec_from_file_location('manage_lessons_set_title', str(SCRIPT_PATH))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_set_title = _mod.cmd_set_title


# =============================================================================
# Test fixtures helpers
# =============================================================================


def _seed_active_lesson(
    lessons_dir: Path,
    lesson_id: str = '2025-01-01-01-001',
    title: str = 'Original Title',
    body: str = '',
    extra_frontmatter: str = '',
) -> Path:
    """Create an active lesson markdown file with frontmatter, H1 title, and body.

    The shape mirrors what ``cmd_add`` produces: ``key=value`` lines, a blank
    line, the ``# {title}`` H1, then optional body content.
    """
    path = lessons_dir / f'{lesson_id}.md'
    frontmatter = (
        f'id={lesson_id}\n'
        'component=test-component\n'
        'category=bug\n'
        'created=2025-01-01\n'
        'status=active\n'
    )
    if extra_frontmatter:
        frontmatter += extra_frontmatter
    content = f'{frontmatter}\n# {title}\n'
    if body:
        content += f'\n{body}'
    path.write_text(content, encoding='utf-8')
    return path


def _seed_superseded_lesson(
    lessons_dir: Path,
    lesson_id: str = '2025-01-01-01-002',
    title: str = 'Superseded Title',
    superseded_by: str = '2025-01-01-01-099',
) -> Path:
    """Create a superseded lesson stub. Superseded lessons remain on disk but
    have ``status=superseded`` and a ``superseded_by`` pointer in frontmatter.
    """
    path = lessons_dir / f'{lesson_id}.md'
    content = (
        f'id={lesson_id}\n'
        'component=test-component\n'
        'category=bug\n'
        'created=2025-01-01\n'
        'status=superseded\n'
        f'superseded_by={superseded_by}\n'
        '\n'
        f'# {title}\n'
    )
    path.write_text(content, encoding='utf-8')
    return path


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
