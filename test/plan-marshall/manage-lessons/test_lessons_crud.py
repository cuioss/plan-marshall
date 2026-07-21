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
from pathlib import Path
from unittest.mock import patch

from _lessons_helpers import SCRIPT_PATH, _mod, cmd_get, cmd_list, cmd_set_body
from conftest import run_script

# ``cmd_set_title`` is not re-exported by ``_lessons_helpers`` (that module is
# owned elsewhere and is not modified by this suite), so it is bound off the
# shared module handle. This keeps the single-load contract intact.
cmd_set_title = _mod.cmd_set_title


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
# Tier 2: legacy-format compatibility (read paths)
# =============================================================================


class TestLegacyFormatCompatibility:
    """Legacy ``YYYY-MM-DD-NNN`` lessons must remain readable through read APIs."""

    def test_legacy_ids_remain_readable_and_listable(self, tmp_path):
        """``cmd_get`` and ``cmd_list`` must surface legacy-format lessons.

        Seeds the lessons dir with a legacy ``2025-01-01-001.md`` fixture (the
        pre-hour-aware filename layout) and asserts:

        * ``cmd_get(lesson_id='2025-01-01-001')`` returns ``status: success`` and
          surfaces the metadata fields intact.
        * ``cmd_list`` enumerates the legacy entry alongside any hour-aware
          entries and does not drop it.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        legacy_content = """id=2025-01-01-001
component=legacy-component
category=improvement
created=2025-01-01

# Legacy Lesson Title

Legacy body content.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(legacy_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            get_result = cmd_get(Namespace(lesson_id='2025-01-01-001'))
            list_result = cmd_list(Namespace(component=None, category=None, full=False))

        # cmd_get surfaces the legacy entry with full metadata.
        assert get_result['status'] == 'success'
        assert get_result['id'] == '2025-01-01-001'
        assert get_result['component'] == 'legacy-component'
        assert get_result['category'] == 'improvement'
        assert get_result['title'] == 'Legacy Lesson Title'

        # cmd_list enumerates the legacy file.
        assert list_result['status'] == 'success'
        assert list_result['total'] == 1
        assert list_result['filtered'] == 1
        listed_ids = [entry['id'] for entry in list_result['lessons']]
        assert '2025-01-01-001' in listed_ids

    def test_legacy_and_hour_aware_ids_coexist_in_list(self, tmp_path):
        """``cmd_list`` must enumerate both legacy and hour-aware lessons together."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        (lessons_dir / '2025-01-01-001.md').write_text(
            'id=2025-01-01-001\ncomponent=a\ncategory=bug\ncreated=2025-01-01\n\n# Legacy\n'
        )
        (lessons_dir / '2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=b\ncategory=bug\ncreated=2025-01-01\n\n# Hour-aware\n'
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        assert result['status'] == 'success'
        assert result['total'] == 2
        assert result['filtered'] == 2
        listed_ids = {entry['id'] for entry in result['lessons']}
        assert '2025-01-01-001' in listed_ids
        assert '2025-01-01-02-001' in listed_ids


# =============================================================================
# Tier 2: cmd_list --status filter
# =============================================================================


def _seed_lesson_with_status(lessons_dir: Path, lesson_id: str, status: str | None, title: str) -> Path:
    """Write a minimal lesson file with optional ``status`` frontmatter."""
    metadata_lines = [
        f'id={lesson_id}',
        'component=test',
        'category=bug',
        'created=2025-01-01',
    ]
    if status is not None:
        metadata_lines.insert(3, f'status={status}')
    content = '\n'.join(metadata_lines) + f'\n\n# {title}\n\nBody.\n'
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(content, encoding='utf-8')
    return path


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


# =============================================================================
# cmd_set_title fixture helpers
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


# =============================================================================
# Tier 2: cmd_set_body
# =============================================================================


class TestCmdSetBody:
    """Test cmd_set_body direct invocation."""

    _STUB_TEMPLATE = 'id={lesson_id}\ncomponent=test-component\ncategory=bug\ncreated=2025-01-01\n\n# {title}\n\n'

    def _seed_stub(self, lessons_dir: Path, lesson_id: str, title: str = 'Stub Title') -> Path:
        """Create a fresh lesson stub mirroring the shape produced by ``cmd_add``."""
        path = lessons_dir / f'{lesson_id}.md'
        path.write_text(
            self._STUB_TEMPLATE.format(lesson_id=lesson_id, title=title),
            encoding='utf-8',
        )
        return path

    def test_set_body_with_file_input_overwrites_body(self, tmp_path):
        """``--file`` form must read the file and replace the lesson body.

        Seeds an empty stub, writes a multi-line markdown body to a sidecar
        file, and asserts the resulting lesson has the new body, the original
        frontmatter intact, and the success TOON shape with the byte count
        matching the body source's UTF-8 length.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_stub(lessons_dir, '2025-01-01-02-001', 'My Lesson')

        body_file = tmp_path / 'body.md'
        body_text = '## Context\n\nMulti-line body with `code` and a list:\n\n- item one\n- item two\n'
        body_file.write_text(body_text, encoding='utf-8')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=str(body_file),
                    content=None,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-02-001'
        assert Path(result['path']) == (lessons_dir / '2025-01-01-02-001.md').resolve()
        assert result['body_bytes_written'] == len(body_text.encode('utf-8'))

        updated = (lessons_dir / '2025-01-01-02-001.md').read_text(encoding='utf-8')
        # Body content present
        assert '## Context' in updated
        assert '- item one' in updated
        # Frontmatter and H1 still present
        assert 'id=2025-01-01-02-001' in updated
        assert 'component=test-component' in updated
        assert '# My Lesson' in updated

    def test_set_body_with_content_input_overwrites_body(self, tmp_path):
        """``--content`` form must use the inline string as the new body.

        This covers the secondary inline form used for tiny payloads. The
        function must return the same TOON shape as the ``--file`` form and
        the byte count must reflect the inline string's UTF-8 length.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_stub(lessons_dir, '2025-01-01-02-001', 'Inline Lesson')

        inline_body = 'Short inline body.\n'

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=None,
                    content=inline_body,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-02-001'
        assert result['body_bytes_written'] == len(inline_body.encode('utf-8'))

        updated = (lessons_dir / '2025-01-01-02-001.md').read_text(encoding='utf-8')
        assert 'Short inline body.' in updated
        assert '# Inline Lesson' in updated

    def test_set_body_missing_lesson_returns_not_found(self, tmp_path):
        """Calling ``cmd_set_body`` against a non-existent stub must error out.

        The stub-existence check runs before any body source is read, so the
        error code is ``not_found`` regardless of which input form was used.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='nonexistent-id',
                    file=None,
                    content='whatever',
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'
        assert result['id'] == 'nonexistent-id'

    def test_set_body_rejects_neither_or_both_inputs(self, tmp_path):
        """Mutual-exclusion guard must reject both-supplied and neither-supplied calls.

        The CLI layer enforces ``--file`` vs. ``--content`` exclusivity via
        argparse's ``add_mutually_exclusive_group(required=True)``, but the
        underlying function still guards against direct programmatic misuse —
        both branches must return ``invalid_input``. We check the
        neither-supplied branch (both ``None``) and the both-supplied branch
        because the implementation uses ``(file is None) == (content is None)``,
        which catches both shapes with one comparison.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_stub(lessons_dir, '2025-01-01-02-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            neither_result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=None,
                    content=None,
                )
            )
            both_result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file='/tmp/some-file.md',
                    content='inline body',
                )
            )

        assert neither_result['status'] == 'error'
        assert neither_result['error'] == 'invalid_input'
        assert both_result['status'] == 'error'
        assert both_result['error'] == 'invalid_input'

    def test_set_body_with_directory_path_returns_file_not_found(self, tmp_path):
        """``--file`` form must reject a path that is a directory, not a regular file.

        Mirrors the ``_tasks_crud.py`` ``--tasks-file`` guard: ``Path.is_file()``
        is stricter than ``Path.exists()`` and rejects directories, broken
        symlinks, and special files. The error code must be ``file_not_found``
        and the message must surface the offending path so callers can react.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_stub(lessons_dir, '2025-01-01-02-001', 'Dir Test')

        # A directory exists at this path — ``Path.exists()`` would return True
        # but ``is_file()`` returns False, which the guard must surface as
        # ``file_not_found`` rather than crashing in ``read_text``.
        bogus_dir = tmp_path / 'not-a-file-dir'
        bogus_dir.mkdir()

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=str(bogus_dir),
                    content=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'
        assert result['id'] == '2025-01-01-02-001'
        assert str(bogus_dir) in result['message']

    def test_set_body_with_unreadable_file_returns_file_read_error(self, tmp_path):
        """``--file`` form must surface ``OSError`` from ``read_text`` as ``file_read_error``.

        Simulates a transient I/O failure (permission flip, EIO, vanished mount)
        by monkeypatching ``Path.read_text`` to raise ``PermissionError`` (an
        ``OSError`` subclass). The guard must trap the exception, leave the
        target lesson stub on disk untouched, and return a structured error
        payload with ``error: file_read_error`` and the offending path
        reflected in the message — never let the exception propagate.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        stub_path = self._seed_stub(lessons_dir, '2025-01-01-02-001', 'Read Error Test')
        stub_content_before = stub_path.read_text(encoding='utf-8')

        body_file = tmp_path / 'body.md'
        body_file.write_text('Body that cannot be read.', encoding='utf-8')

        original_read_text = Path.read_text

        def _raising_read_text(self, *args, **kwargs):
            # Only raise for the body source; allow reads on the lesson stub
            # (the function reads the original lesson via ``target.read_text``
            # AFTER the body source). We restrict to the exact body file path.
            if self == body_file:
                raise PermissionError('simulated read failure')
            return original_read_text(self, *args, **kwargs)

        with (
            patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}),
            patch.object(Path, 'read_text', _raising_read_text),
        ):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=str(body_file),
                    content=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'file_read_error'
        assert result['id'] == '2025-01-01-02-001'
        assert str(body_file) in result['message']
        # The lesson stub on disk must be untouched — the failure happened
        # before the rewrite stage, so no atomic write should have run.
        assert stub_path.read_text(encoding='utf-8') == stub_content_before

    def test_set_body_preserves_frontmatter_across_overwrite(self, tmp_path):
        """Frontmatter block and H1 title must survive a body overwrite verbatim.

        Seeds a stub with a richer frontmatter (including an optional
        ``bundle`` field) and a populated body, runs ``cmd_set_body`` to
        replace the body, and asserts:

        * Every original frontmatter line is present in the rewritten file in
          its original order.
        * The H1 title line is unchanged.
        * The original body content is gone — i.e. the overwrite is a true
          replacement, not an append.
        * The new body is present.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        original_lesson = (
            'id=2025-01-01-02-001\n'
            'component=preserved-component\n'
            'category=improvement\n'
            'bundle=pm-dev-java\n'
            'created=2025-01-01\n'
            '\n'
            '# Preserved Title\n'
            '\n'
            'Original body that must be discarded.\n'
            'Second line of original body.\n'
        )
        target = lessons_dir / '2025-01-01-02-001.md'
        target.write_text(original_lesson, encoding='utf-8')

        new_body = 'Replacement body — original lines must be gone.\n'

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=None,
                    content=new_body,
                )
            )

        assert result['status'] == 'success'

        rewritten = target.read_text(encoding='utf-8')

        # Frontmatter lines preserved verbatim, in order.
        rewritten_lines = rewritten.split('\n')
        for expected in (
            'id=2025-01-01-02-001',
            'component=preserved-component',
            'category=improvement',
            'bundle=pm-dev-java',
            'created=2025-01-01',
        ):
            assert expected in rewritten_lines, f'frontmatter line missing: {expected}'

        # Frontmatter ordering preserved (header lines appear before the H1).
        h1_index = rewritten_lines.index('# Preserved Title')
        for expected in (
            'id=2025-01-01-02-001',
            'component=preserved-component',
            'category=improvement',
            'bundle=pm-dev-java',
            'created=2025-01-01',
        ):
            assert rewritten_lines.index(expected) < h1_index

        # Original body is gone — the overwrite is a replacement, not an append.
        assert 'Original body that must be discarded.' not in rewritten
        assert 'Second line of original body.' not in rewritten

        # New body is present.
        assert 'Replacement body' in rewritten
