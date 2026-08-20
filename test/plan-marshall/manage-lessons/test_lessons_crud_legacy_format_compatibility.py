#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the trivial getter/setter CRUD subcommands of manage-lessons.py."""


from argparse import Namespace
from unittest.mock import patch
from _lessons_helpers import cmd_get, cmd_list


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
