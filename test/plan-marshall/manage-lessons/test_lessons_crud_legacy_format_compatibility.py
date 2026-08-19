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
from _lessons_helpers import cmd_get, cmd_list
from _lessons_crud_fixtures import (
    _seed_active_lesson,
    _seed_lesson_with_status,
    _seed_superseded_lesson,
    cmd_set_title,
)


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
