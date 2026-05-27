#!/usr/bin/env python3
"""Tests for the ``remove`` subcommand of manage-lessons.py.

``cmd_remove`` deletes a lesson file, writes a tombstone capturing the
reason, and emits an INFO audit entry to script-execution.log. Tests cover
the ``--force`` happy path, the not-found error path, interactive-cancel
behaviour (``input()`` returning ``n``), and the audit-log emission shape.

CLI plumbing (subprocess) tests for the ``remove`` subcommand live in
``test_remove_supersede_cli.py``.
"""

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from _lessons_helpers import _mod, cmd_remove


class TestCmdRemove:
    """``cmd_remove`` deletes the lesson, writes a tombstone, and logs an audit entry."""

    def _seed_lesson(self, lessons_dir: Path, lesson_id: str = '2025-01-01-01-001') -> Path:
        content = (
            f'id={lesson_id}\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-01\n\n'
            f'# {lesson_id} Title\n\nBody.\n'
        )
        path = lessons_dir / f'{lesson_id}.md'
        path.write_text(content, encoding='utf-8')
        return path

    def test_remove_force_deletes_file_and_writes_tombstone(self, tmp_path):
        """``--force`` skips the prompt; the lesson file is deleted and a tombstone is written."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = self._seed_lesson(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='duplicate of 2025-01-02-01-001',
                    force=True,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-01-001'
        assert result['reason'] == 'duplicate of 2025-01-02-01-001'

        # Lesson file is gone.
        assert not seeded.exists()

        # Tombstone exists with the expected payload.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert tombstone_path.exists()
        payload = json.loads(tombstone_path.read_text(encoding='utf-8'))
        assert payload['lesson_id'] == '2025-01-01-01-001'
        assert payload['reason'] == 'duplicate of 2025-01-02-01-001'
        assert payload['status'] == 'removed'
        assert 'removed_at' in payload
        assert 'superseded_by' not in payload

    def test_remove_unknown_lesson_returns_not_found(self, tmp_path):
        """Removing a lesson that does not exist returns ``error: not_found``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(Namespace(lesson_id='nope', reason='gone', force=True))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_remove_declined_via_input_keeps_file(self, tmp_path, monkeypatch):
        """Without ``--force``, an answer other than ``y/yes`` cancels removal."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = self._seed_lesson(lessons_dir)

        # Stub builtins.input on the manage-lessons module to simulate "no".
        # The remove subcommand writes the prompt to stderr separately, then
        # calls input() with no arguments — so the stub takes none.
        monkeypatch.setattr(_mod, 'input', lambda: 'n', raising=False)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(Namespace(lesson_id='2025-01-01-01-001', reason='maybe', force=False))

        assert result['status'] == 'cancelled'
        # File preserved.
        assert seeded.exists()
        # No tombstone written.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert not tombstone_path.exists()

    def test_remove_logs_audit_entry(self, tmp_path):
        """``cmd_remove --force`` emits an INFO audit entry to script-execution.log."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_lesson(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='dedup',
                    force=True,
                )
            )

            log_files = list((tmp_path / 'logs').glob('script-execution-*.log'))

        assert log_files, 'expected at least one script-execution log file'
        log_text = '\n'.join(p.read_text(encoding='utf-8') for p in log_files)
        assert '[INFO]' in log_text
        assert '(plan-marshall:manage-lessons) Removed lesson 2025-01-01-01-001' in log_text
        assert 'dedup' in log_text
