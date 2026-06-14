#!/usr/bin/env python3
"""Tests for the ``convert-to-plan`` subcommand of manage-lessons.py.

``cmd_convert_to_plan`` moves a lesson file from the global lessons-learned
directory into a plan-local directory (``plans/{plan_id}/lesson-{id}.md``).
Tests cover the happy path, missing-source error, on-the-fly plan-directory
creation, and path-traversal rejection on both ``lesson_id`` and ``plan_id``.
"""

import json
from argparse import Namespace
from unittest.mock import patch

import pytest
from _lessons_helpers import _FakeDatetime, _mod, cmd_convert_to_plan, get_next_id

# Path-separator / traversal sequences that must be rejected on either identifier.
_TRAVERSAL_IDS = ('../escape', 'sub/dir', 'back\\slash')


class TestCmdConvertToPlan:
    """Test cmd_convert_to_plan direct invocation."""

    def test_convert_to_plan_moves_file(self, tmp_path):
        """Should move lesson file from lessons-learned into plan directory."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson

Body content here.
"""
        source = lessons_dir / '2025-01-01-001.md'
        source.write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id='2025-01-01-001', plan_id='my-plan'))

        assert result['status'] == 'success'
        assert result['lesson_id'] == '2025-01-01-001'
        assert result['plan_id'] == 'my-plan'

        # Source file no longer exists
        assert not source.exists()

        # Destination exists with identical content
        destination = tmp_path / 'plans' / 'my-plan' / 'lesson-2025-01-01-001.md'
        assert destination.exists()
        assert destination.read_text() == lesson_content

    def test_convert_to_plan_missing_source(self, tmp_path):
        """Should return error when source lesson does not exist."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id='nonexistent-id', plan_id='my-plan'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_convert_to_plan_creates_plan_dir_if_missing(self, tmp_path):
        """Should create the plan directory on the fly when it does not exist."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson

Body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        plan_dir = tmp_path / 'plans' / 'fresh-plan'
        assert not plan_dir.exists()

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id='2025-01-01-001', plan_id='fresh-plan'))

        assert result['status'] == 'success'
        assert plan_dir.exists()
        assert (plan_dir / 'lesson-2025-01-01-001.md').exists()

    @pytest.mark.parametrize('bad_id', _TRAVERSAL_IDS)
    def test_convert_to_plan_rejects_lesson_id_traversal(self, tmp_path, bad_id):
        """Should reject a lesson_id containing path separators or traversal sequences."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id=bad_id, plan_id='p'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_id'

    @pytest.mark.parametrize('bad_plan', _TRAVERSAL_IDS)
    def test_convert_to_plan_rejects_plan_id_traversal(self, tmp_path, bad_plan):
        """Should reject a plan_id containing path separators or traversal sequences."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id='good-id', plan_id=bad_plan))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_id'


class TestConvertToPlanTombstoneReservation:
    """``convert-to-plan`` must reserve the consumed id with a tombstone.

    Unlike ``remove``/``supersede``, ``convert-to-plan`` keeps the lesson alive
    (relocated into a plan dir), but the consumed id must stay reserved so
    ``get_next_id`` never re-issues it. A ``converted-to-plan`` tombstone records
    the reservation and survives deletion of the plan dir.
    """

    def test_convert_to_plan_writes_converted_tombstone(self, tmp_path):
        """A ``{id}.json`` tombstone with ``status: converted-to-plan`` must be written."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        (lessons_dir / '2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# Test\n'
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id='2025-01-01-02-001', plan_id='my-plan'))

        assert result['status'] == 'success'
        tombstone = lessons_dir / '.tombstones' / '2025-01-01-02-001.json'
        assert tombstone.exists()
        payload = json.loads(tombstone.read_text())
        assert payload['status'] == 'converted-to-plan'
        assert payload['reason'] == 'converted-to-plan'
        assert payload['lesson_id'] == '2025-01-01-02-001'

    def test_converted_tombstone_reserves_id_in_get_next_id(self, tmp_path, monkeypatch):
        """End-to-end: with the source relocated, the tombstone alone reserves the slot.

        After ``convert-to-plan`` the live ``.md`` is gone from ``lessons-learned/``
        (it moved into the plan dir), so only the tombstone and the plan dir keep
        the id reserved. Freezing the clock to the same prefix, ``get_next_id``
        must return ``-002`` — proving the reservation path is honoured.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        (lessons_dir / '2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# Test\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            convert_result = cmd_convert_to_plan(
                Namespace(lesson_id='2025-01-01-02-001', plan_id='my-plan')
            )
            assert convert_result['status'] == 'success'
            # Source .md has been relocated out of lessons-learned/.
            assert not (lessons_dir / '2025-01-01-02-001.md').exists()

            next_id = get_next_id()

        assert next_id == '2025-01-01-02-002'
