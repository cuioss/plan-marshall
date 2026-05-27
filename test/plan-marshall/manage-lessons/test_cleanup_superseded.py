#!/usr/bin/env python3
"""Tests for the ``cleanup-superseded`` subcommand of manage-lessons.py.

``cmd_cleanup_superseded`` prunes redirect stubs left behind by
``cmd_supersede`` while preserving the tombstones (which are the
authoritative audit trail). Two operating modes: age-filtered via
``--retention-days`` (only stubs older than the cutoff), or explicit-list
via ``--lesson-id`` (no age filter). ``--dry-run`` reports candidates
without deleting.

Tests cover: retention-based filtering, explicit-id ignores age,
tombstone preservation, idempotency on already-removed, the
``skipped_no_tombstone`` guard against acting on orphan stubs, and
``--dry-run`` behaviour. CLI plumbing for the mutual-exclusion guard
between ``--lesson-id`` and ``--retention-days`` lives in
``test_remove_supersede_cli.py``.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from _lessons_helpers import cmd_cleanup_superseded, cmd_supersede


class TestCmdCleanupSuperseded:
    """``cmd_cleanup_superseded`` prunes redirect stubs while preserving tombstones."""

    def _seed_superseded(
        self,
        lessons_dir: Path,
        lesson_id: str,
        canonical_id: str = '2025-12-31-23-001',
        title: str = 'Source',
    ) -> Path:
        """Create a lesson and immediately supersede it via ``cmd_supersede``.

        Returns the path of the redirect stub so callers can assert on it
        directly. Reuses production ``cmd_supersede`` rather than handcrafting
        the on-disk shape so the test exercises the real coupling between
        supersede and cleanup.
        """
        canonical_path = lessons_dir / f'{canonical_id}.md'
        if not canonical_path.exists():
            canonical_path.write_text(
                f'id={canonical_id}\n'
                'component=test\n'
                'category=bug\n'
                'status=active\n'
                'created=2025-12-31\n\n'
                '# Canonical\n\nCanonical body.\n',
                encoding='utf-8',
            )
        source = lessons_dir / f'{lesson_id}.md'
        source.write_text(
            f'id={lesson_id}\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-01\n\n'
            f'# {title}\n\nSource body.\n',
            encoding='utf-8',
        )
        cmd_supersede(Namespace(lesson_id=lesson_id, by=canonical_id, reason='merged into canonical'))
        return source

    def test_cleanup_superseded_retention_filter_removes_only_old_stubs(self, tmp_path):
        """Age-filtered mode prunes only stubs whose mtime is older than the threshold."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            old_stub = self._seed_superseded(lessons_dir, '2025-01-01-01-001', title='Old')
            fresh_stub = self._seed_superseded(lessons_dir, '2025-01-01-01-002', title='Fresh')

            # Backdate the old stub past the 7-day cutoff.
            import os as _os

            old_mtime = old_stub.stat().st_mtime - (10 * 86400)
            _os.utime(old_stub, (old_mtime, old_mtime))

            result = cmd_cleanup_superseded(Namespace(lesson_id=None, retention_days=7, dry_run=False))

        assert result['status'] == 'success'
        assert result['retention_days_effective'] == 7
        removed_ids = {entry['lesson_id'] for entry in result['removed']}
        assert removed_ids == {'2025-01-01-01-001'}
        assert not old_stub.exists()
        assert fresh_stub.exists()
        # Fresh stub's tombstone is also untouched.
        assert (lessons_dir / '.tombstones' / '2025-01-01-01-002.json').exists()

    def test_cleanup_superseded_explicit_lesson_ids_ignore_age(self, tmp_path):
        """Explicit ``--lesson-id`` removes the stub regardless of file age."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            stub = self._seed_superseded(lessons_dir, '2025-02-01-01-001')

            # File is fresh (no mtime backdating); explicit-id mode should still remove it.
            result = cmd_cleanup_superseded(
                Namespace(lesson_id=['2025-02-01-01-001'], retention_days=None, dry_run=False)
            )

        assert result['status'] == 'success'
        assert {entry['lesson_id'] for entry in result['removed']} == {'2025-02-01-01-001'}
        assert not stub.exists()

    def test_cleanup_superseded_preserves_tombstones(self, tmp_path):
        """The matching ``.tombstones/{id}.json`` survives every removal mode byte-for-byte."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            self._seed_superseded(lessons_dir, '2025-03-01-01-001')
            tombstone_path = lessons_dir / '.tombstones' / '2025-03-01-01-001.json'
            tombstone_bytes_before = tombstone_path.read_bytes()

            cmd_cleanup_superseded(Namespace(lesson_id=['2025-03-01-01-001'], retention_days=None, dry_run=False))

        assert tombstone_path.exists()
        assert tombstone_path.read_bytes() == tombstone_bytes_before

    def test_cleanup_superseded_idempotent_on_already_removed(self, tmp_path):
        """Re-running with the same id reports it under ``already_removed`` (not error)."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            self._seed_superseded(lessons_dir, '2025-04-01-01-001')

            first = cmd_cleanup_superseded(
                Namespace(lesson_id=['2025-04-01-01-001'], retention_days=None, dry_run=False)
            )
            second = cmd_cleanup_superseded(
                Namespace(lesson_id=['2025-04-01-01-001'], retention_days=None, dry_run=False)
            )

        assert first['status'] == 'success'
        assert {e['lesson_id'] for e in first['removed']} == {'2025-04-01-01-001'}

        assert second['status'] == 'success'
        assert second['removed'] == []
        assert {e['lesson_id'] for e in second['already_removed']} == {'2025-04-01-01-001'}

    def test_cleanup_superseded_skips_files_without_tombstone(self, tmp_path):
        """A ``status: superseded`` file lacking a tombstone is reported under ``skipped_no_tombstone``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        # Handcraft a superseded-style stub WITHOUT writing a tombstone.
        orphan = lessons_dir / '2025-05-01-01-001.md'
        orphan.write_text(
            'id=2025-05-01-01-001\n'
            'component=test\n'
            'category=bug\n'
            'status=superseded\n'
            'created=2025-05-01\n\n'
            '# Orphan Stub\n\n[SUPERSEDED]\n',
            encoding='utf-8',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_cleanup_superseded(
                Namespace(lesson_id=['2025-05-01-01-001'], retention_days=None, dry_run=False)
            )

        assert result['status'] == 'success'
        assert result['removed'] == []
        assert {e['lesson_id'] for e in result['skipped_no_tombstone']} == {'2025-05-01-01-001'}
        # The .md must still be on disk — refusing to act preserves the audit trail.
        assert orphan.exists()

    def test_cleanup_superseded_dry_run_does_not_delete(self, tmp_path):
        """``--dry-run`` reports candidates under ``removed[]`` but leaves the .md on disk."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            stub = self._seed_superseded(lessons_dir, '2025-06-01-01-001')

            result = cmd_cleanup_superseded(
                Namespace(lesson_id=['2025-06-01-01-001'], retention_days=None, dry_run=True)
            )

        assert result['status'] == 'success'
        assert result['dry_run'] is True
        assert {e['lesson_id'] for e in result['removed']} == {'2025-06-01-01-001'}
        # File remains on disk under dry-run.
        assert stub.exists()
