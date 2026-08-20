#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``add`` subcommand of manage-lessons.py.

Covers:

* ``cmd_add`` direct invocation (TestCmdAdd)
* Hour-aware id generation backing ``cmd_add`` (TestGetNextIdHourAware)
"""


import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
from _lessons_helpers import (
    _FakeDatetime,
    _mod,
    cmd_add,
    get_next_id,
)


# =============================================================================
# Tier 2: cmd_add
# =============================================================================


class TestCmdAdd:
    """Test cmd_add direct invocation."""

    def test_add_allocates_lesson_file_and_returns_path(self, tmp_path):
        """Should create a lesson file with metadata header + title and return its absolute path."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='bug',
                    title='Test Lesson',
                    bundle=None,
                )
            )

        assert result['status'] == 'success'
        assert result['component'] == 'test-component'
        assert result['category'] == 'bug'
        assert 'id' in result
        assert 'path' in result

        path = Path(result['path'])
        assert path.is_absolute()
        assert path.parent == lessons_dir.resolve()
        assert path.exists()

        content = path.read_text(encoding='utf-8')
        assert f'id={result["id"]}' in content
        assert 'component=test-component' in content
        assert 'category=bug' in content
        assert '# Test Lesson' in content
        # Body is empty — the section after the title should be whitespace only
        body = content.split('# Test Lesson', 1)[1]
        assert body.strip() == ''

    def test_add_with_invalid_category_fails(self, tmp_path):
        """Should fail when using invalid category."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='invalid-category',
                    title='Test',
                    bundle=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_category'

    def test_add_with_bundle_reference(self, tmp_path):
        """Should accept optional bundle reference and persist it in the metadata header."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='improvement',
                    title='Test Lesson',
                    bundle='pm-dev-java',
                )
            )

        assert result['status'] == 'success'
        content = Path(result['path']).read_text(encoding='utf-8')
        assert 'bundle=pm-dev-java' in content


# =============================================================================
# Tier 2: get_next_id (hour-aware ID generation)
# =============================================================================


class TestGetNextIdHourAware:
    """Deterministic tests for hour-aware ID generation in ``get_next_id``."""

    def test_get_next_id_resets_per_hour(self, tmp_path, monkeypatch):
        """Counter must reset to 001 when the hour changes.

        Seeds the lessons dir with a lesson from hour 01, freezes ``datetime.now``
        to the UTC instant ``2025-01-01 02:15:00+00:00``, then asserts that
        ``get_next_id`` returns ``2025-01-01-02-001`` — the hour prefix rolls
        forward and the sequence number resets because no prior lesson exists
        for hour 02. The instant is aware-UTC so the asserted hour bucket is the
        same on every host timezone.
        """
        from datetime import UTC as real_utc
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        # Legacy-format-for-hour-scheme fixture from hour 01.
        (lessons_dir / '2025-01-01-01-001.md').write_text(
            'id=2025-01-01-01-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# seed\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 15, 0, tzinfo=real_utc)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-001'

    def test_get_next_id_increments_within_same_hour(self, tmp_path, monkeypatch):
        """Sequence number must increment when multiple lessons share an hour."""
        from datetime import UTC as real_utc
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        (lessons_dir / '2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# seed\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 30, 0, tzinfo=real_utc)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-002'

    def test_get_next_id_ignores_legacy_ids_when_computing_hour_sequence(self, tmp_path, monkeypatch):
        """Legacy ``YYYY-MM-DD-NNN`` files must not collide with a new hour prefix.

        Seeds a legacy lesson ``2025-01-01-005.md`` (no hour segment), freezes
        ``now`` to UTC hour 03, and asserts ``get_next_id`` returns
        ``2025-01-01-03-001`` rather than reading the legacy counter. The legacy
        file must remain on disk untouched — this test only covers the
        generation path.
        """
        from datetime import UTC as real_utc
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        legacy_path = lessons_dir / '2025-01-01-005.md'
        legacy_content = 'id=2025-01-01-005\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# legacy seed\n'
        legacy_path.write_text(legacy_content)

        frozen = real_datetime(2025, 1, 1, 3, 0, 0, tzinfo=real_utc)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-03-001'
        # Legacy file remains readable and untouched.
        assert legacy_path.exists()
        assert legacy_path.read_text() == legacy_content


# =============================================================================
# Tier 2: get_next_id collision detection across tombstones + plan dirs
# =============================================================================


class TestGetNextIdUnionScan:
    """``get_next_id`` must union live lessons, tombstones, and plan-derived dirs.

    The original ``get_next_id`` scanned only ``lessons-learned/{prefix}-*.md``,
    so a sequence number consumed by ``convert-to-plan`` (relocated into a plan
    dir) or recorded only as a tombstone could be re-issued — a silent id
    collision. These tests pin the union-scan fix: the next id must clear the
    max sequence across all three sources.
    """

    def test_get_next_id_skips_plan_derived_directory(self, tmp_path, monkeypatch):
        """A ``plans/lesson-{prefix}-001/`` dir must reserve sequence 001.

        Seeds a plan-derived directory (the shape produced by
        ``convert-to-plan``) with no live ``.md`` in ``lessons-learned/``, freezes
        the clock to the same prefix, and asserts ``get_next_id`` returns
        ``-002`` rather than re-issuing ``-001``.
        """
        from datetime import UTC as real_utc
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        plan_dir = tmp_path / 'plans' / 'lesson-2025-01-01-02-001'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# converted\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 30, 0, tzinfo=real_utc)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-002'

    def test_get_next_id_skips_tombstone_only_id(self, tmp_path, monkeypatch):
        """A ``.tombstones/{prefix}-001.json`` must reserve sequence 001.

        Seeds a tombstone with no live ``.md`` and no plan dir, freezes the clock
        to the same prefix, and asserts ``get_next_id`` returns ``-002``.
        """
        from datetime import UTC as real_utc
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        tombstones_dir = lessons_dir / '.tombstones'
        tombstones_dir.mkdir(parents=True)
        (tombstones_dir / '2025-01-01-02-001.json').write_text(
            json.dumps(
                {
                    'lesson_id': '2025-01-01-02-001',
                    'removed_at': '2025-01-01T02:00:00+00:00',
                    'reason': 'duplicate',
                    'status': 'removed',
                }
            )
        )

        frozen = real_datetime(2025, 1, 1, 2, 30, 0, tzinfo=real_utc)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-002'
