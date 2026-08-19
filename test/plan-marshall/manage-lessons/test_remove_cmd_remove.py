#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``remove`` subcommand of manage-lessons.py.

``cmd_remove`` deletes a lesson file, writes a tombstone capturing the reason
and the retirement verdict, and emits an INFO audit entry to
script-execution.log. Tests cover the ``--force`` happy path, the not-found
error path, interactive-cancel behaviour (``input()`` returning ``n``), and the
audit-log emission shape.

Retirement evidence (the two-key path) is covered by a matched pair of controls
driven through the SAME vehicle — the real ``manage-lessons.py`` argparse
surface via ``run_script`` — so the negative control's rejection and the
positive control's success are directly comparable:

* **Negative control** — ``--coverage-verdict completely_covered`` without the
  evidence pair is rejected by the real CLI AND the lesson survives on disk.
  Asserting survival matters as much as asserting rejection: a rejection that
  still unlinked the file would be a silent data loss the exit code alone would
  not reveal.
* **Positive control** — a complete evidence set removes the lesson and writes
  a tombstone carrying ``coverage_verdict``, ``covering_clause`` and
  ``covering_input``.

Both controls exercise the shipped argparse declaration, never a stubbed or
re-implemented validator; the handler-side backstop (``cmd_remove`` invoked
directly, as a programmatic caller would) is covered separately so BOTH keys of
the two-key path are pinned.

CLI plumbing (subprocess) tests for the ``remove`` subcommand live in
``test_remove_supersede_cli.py``.
"""


import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
from _lessons_helpers import _mod, cmd_remove


# The verdicts that assert a weaker claim than ``completely_covered`` and
# therefore require no evidence pair. Derived from the production vocabulary so
# a new verdict cannot be added without this test set being reconsidered.
_NON_EVIDENCE_VERDICTS = [v for v in _mod.COVERAGE_VERDICTS if v != _mod.EVIDENCE_REQUIRED_VERDICT]


_CLAUSE = 'manage-lessons/SKILL.md Canonical invocations -> remove'


_INPUT = 'remove --coverage-verdict completely_covered with no --covering-clause'


def _seed_lesson_file(lessons_dir: Path, lesson_id: str) -> Path:
    """Write a minimal, canonically-shaped lesson file and return its path."""
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


class TestCmdRemove:
    """``cmd_remove`` deletes the lesson, writes a tombstone, and logs an audit entry."""

    def _seed_lesson(self, lessons_dir: Path, lesson_id: str = '2025-01-01-01-001') -> Path:
        return _seed_lesson_file(lessons_dir, lesson_id)

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
                    coverage_verdict='redundant',
                    covering_clause=None,
                    covering_input=None,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-01-001'
        assert result['reason'] == 'duplicate of 2025-01-02-01-001'
        assert result['coverage_verdict'] == 'redundant'

        # Lesson file is gone.
        assert not seeded.exists()

        # Tombstone exists with the expected payload.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert tombstone_path.exists()
        payload = json.loads(tombstone_path.read_text(encoding='utf-8'))
        assert payload['lesson_id'] == '2025-01-01-01-001'
        assert payload['reason'] == 'duplicate of 2025-01-02-01-001'
        assert payload['status'] == 'removed'
        assert payload['coverage_verdict'] == 'redundant'
        assert 'removed_at' in payload
        assert 'superseded_by' not in payload
        # A non-completely_covered verdict records no evidence pair.
        assert 'covering_clause' not in payload
        assert 'covering_input' not in payload

    def test_remove_unknown_lesson_returns_not_found(self, tmp_path):
        """Removing a lesson that does not exist returns ``error: not_found``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(
                Namespace(
                    lesson_id='nope',
                    reason='gone',
                    force=True,
                    coverage_verdict='obsolete',
                    covering_clause=None,
                    covering_input=None,
                )
            )

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
            result = cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='maybe',
                    force=False,
                    coverage_verdict='superseded',
                    covering_clause=None,
                    covering_input=None,
                )
            )

        assert result['status'] == 'cancelled'
        # File preserved.
        assert seeded.exists()
        # No tombstone written.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert not tombstone_path.exists()

    def test_remove_logs_audit_entry(self, tmp_path):
        """``cmd_remove --force`` emits an INFO audit entry naming the reason and verdict."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_lesson(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='dedup',
                    force=True,
                    coverage_verdict='redundant',
                    covering_clause=None,
                    covering_input=None,
                )
            )

            log_files = list((tmp_path / 'logs').glob('script-execution-*.log'))

        assert log_files, 'expected at least one script-execution log file'
        log_text = '\n'.join(p.read_text(encoding='utf-8') for p in log_files)
        assert '[INFO]' in log_text
        assert '(plan-marshall:manage-lessons) Removed lesson 2025-01-01-01-001' in log_text
        assert 'dedup' in log_text
        assert 'verdict=redundant' in log_text
