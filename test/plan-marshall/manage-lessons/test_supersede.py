#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for the ``supersede`` subcommand of manage-lessons.py.

``cmd_supersede`` redirects a source lesson to a canonical one. The source
body becomes a ``[SUPERSEDED]`` redirect stub with ``status=superseded`` in
the frontmatter, the canonical receives a ``## Consolidated lessons`` H2
with a per-source ``### {id} — {title}`` subsection (created on first
merge, appended on subsequent merges), and a tombstone records the
``superseded_by`` redirect target.

Tests cover: the basic redirect+tombstone shape, append-to-existing
section, not-found source/canonical error paths, self-supersede rejection,
first-merge H2 creation, second-merge append behaviour, idempotency when
the subsection already exists, atomic write failure on the canonical
leaving the source intact, and the audit-log entry shape.

CLI plumbing for ``supersede`` lives in ``test_remove_supersede_cli.py``.
"""

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from _lessons_helpers import _mod, cmd_supersede


class TestCmdSupersede:
    """``cmd_supersede`` redirects a lesson to a canonical and updates both files."""

    def _seed_pair(self, lessons_dir: Path, with_consolidated_section: bool = False) -> tuple[Path, Path]:
        source = lessons_dir / '2025-01-01-01-001.md'
        source.write_text(
            'id=2025-01-01-01-001\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-01\n\n'
            '# Source Lesson\n\nSource body content.\n',
            encoding='utf-8',
        )
        canonical_body = '# Canonical Lesson\n\nCanonical body content.\n'
        if with_consolidated_section:
            canonical_body = (
                '# Canonical Lesson\n\nCanonical body content.\n\n## Consolidated from\n\n- 2024-12-31-23-099\n'
            )
        canonical = lessons_dir / '2025-01-02-01-001.md'
        canonical.write_text(
            'id=2025-01-02-01-001\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-02\n\n' + canonical_body,
            encoding='utf-8',
        )
        return source, canonical

    def test_supersede_writes_redirect_and_tombstone(self, tmp_path):
        """Source body is replaced with a redirect stub; tombstone records ``superseded_by``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        source, canonical = self._seed_pair(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='merged into canonical',
                )
            )

        assert result['status'] == 'success'
        assert result['superseded_by'] == '2025-01-02-01-001'

        # Source lesson body replaced with redirect stub and frontmatter updated.
        source_content = source.read_text(encoding='utf-8')
        assert '[SUPERSEDED]' in source_content
        assert '`2025-01-02-01-001`' in source_content
        assert 'merged into canonical' in source_content
        assert 'status=superseded' in source_content
        assert 'Source body content.' not in source_content

        # Canonical received a "Consolidated from" entry.
        canonical_content = canonical.read_text(encoding='utf-8')
        assert '## Consolidated from' in canonical_content
        assert '- 2025-01-01-01-001' in canonical_content

        # Tombstone has superseded_by populated.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert tombstone_path.exists()
        payload = json.loads(tombstone_path.read_text(encoding='utf-8'))
        assert payload['lesson_id'] == '2025-01-01-01-001'
        assert payload['status'] == 'superseded'
        assert payload['superseded_by'] == '2025-01-02-01-001'
        assert payload['reason'] == 'merged into canonical'

    def test_supersede_appends_to_existing_consolidated_section(self, tmp_path):
        """When the canonical already has a ``Consolidated from`` section, the new id is appended."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        _, canonical = self._seed_pair(lessons_dir, with_consolidated_section=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='dedup',
                )
            )

        canonical_content = canonical.read_text(encoding='utf-8')
        # Both the original entry and the new one are present.
        assert '- 2024-12-31-23-099' in canonical_content
        assert '- 2025-01-01-01-001' in canonical_content
        # Only one "Consolidated from" header — the section is reused, not duplicated.
        assert canonical_content.count('## Consolidated from') == 1

    def test_supersede_unknown_source_returns_not_found(self, tmp_path):
        """Superseding a non-existent source lesson returns ``error: not_found``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_pair(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='no-such-lesson',
                    by='2025-01-02-01-001',
                    reason='whatever',
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_supersede_unknown_canonical_returns_canonical_not_found(self, tmp_path):
        """Superseding by a non-existent canonical lesson returns ``error: canonical_not_found``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        source, _ = self._seed_pair(lessons_dir)
        original_source_content = source.read_text(encoding='utf-8')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='no-such-canonical',
                    reason='whatever',
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'canonical_not_found'
        # Source must remain untouched on canonical-missing error.
        assert source.read_text(encoding='utf-8') == original_source_content

    def test_supersede_self_is_rejected(self, tmp_path):
        """A lesson cannot supersede itself."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_pair(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-01-01-001',
                    reason='self',
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'self_supersede'

    def test_supersede_first_merge_creates_consolidated_lessons_h2(self, tmp_path):
        """First supersede creates ``## Consolidated lessons`` H2 plus a ``### {id} — {title}`` subsection."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        _, canonical = self._seed_pair(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='first merge',
                )
            )

        assert result['status'] == 'success'
        assert result['merged_bytes'] > 0

        canonical_content = canonical.read_text(encoding='utf-8')
        assert canonical_content.count('## Consolidated lessons') == 1
        assert '### 2025-01-01-01-001 — Source Lesson' in canonical_content
        assert '**Component**: `test` · **Category**: bug' in canonical_content
        # Source body is preserved in the canonical.
        assert 'Source body content.' in canonical_content

    def test_supersede_second_merge_appends_under_existing_h2(self, tmp_path):
        """A second supersede against the same canonical adds another ``### {id}`` without duplicating the H2."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        _, canonical = self._seed_pair(lessons_dir)

        # Seed a second source lesson with distinct metadata so we can assert
        # the per-source `Component`/`Category` line is rendered correctly.
        second_source = lessons_dir / '2025-01-03-01-001.md'
        second_source.write_text(
            'id=2025-01-03-01-001\n'
            'component=other\n'
            'category=improvement\n'
            'status=active\n'
            'created=2025-01-03\n\n'
            '# Second Source\n\nSecond source body.\n',
            encoding='utf-8',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='first',
                )
            )
            cmd_supersede(
                Namespace(
                    lesson_id='2025-01-03-01-001',
                    by='2025-01-02-01-001',
                    reason='second',
                )
            )

        canonical_content = canonical.read_text(encoding='utf-8')
        # Both subsections present, single H2.
        assert canonical_content.count('## Consolidated lessons') == 1
        assert '### 2025-01-01-01-001 — Source Lesson' in canonical_content
        assert '### 2025-01-03-01-001 — Second Source' in canonical_content
        # Per-source metadata line uses the second source's component/category.
        assert '**Component**: `other` · **Category**: improvement' in canonical_content
        assert 'Second source body.' in canonical_content

    def test_supersede_idempotent_when_subsection_present(self, tmp_path):
        """Re-running supersede whose ``### {id}`` already exists on the canonical is a body no-op (merged_bytes=0)."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        _, canonical = self._seed_pair(lessons_dir)

        # Pre-populate the canonical with a subsection for the source id so the
        # idempotency check fires before any append happens.
        canonical.write_text(
            'id=2025-01-02-01-001\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-02\n\n'
            '# Canonical Lesson\n\nCanonical body content.\n\n'
            '## Consolidated lessons\n\n'
            '### 2025-01-01-01-001 — Pre-existing Title\n\n'
            '**Component**: `test` · **Category**: bug\n\n'
            'pre-existing merged body\n',
            encoding='utf-8',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='retry',
                )
            )

        assert result['status'] == 'success'
        assert result['merged_bytes'] == 0

        canonical_after = canonical.read_text(encoding='utf-8')
        # H2 stays single, the pre-existing subsection is preserved, and no
        # second `### 2025-01-01-01-001` was added.
        assert canonical_after.count('## Consolidated lessons') == 1
        assert canonical_after.count('### 2025-01-01-01-001') == 1
        assert 'pre-existing merged body' in canonical_after
        # The pre-existing title is preserved verbatim — supersede did not
        # rewrite it with the source's current title.
        assert 'Pre-existing Title' in canonical_after

    def test_supersede_atomic_canonical_write_failure_leaves_source_intact(self, tmp_path, monkeypatch):
        """A failure during the canonical write leaves the source body and frontmatter unchanged."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        source, canonical = self._seed_pair(lessons_dir)
        source_before = source.read_text(encoding='utf-8')

        canonical_path_str = str(canonical)
        original_atomic_write = _mod.atomic_write_file

        def failing_atomic_write(path, content):
            # Raise only when the canonical is the target so the tombstone
            # write (which precedes the canonical write) still succeeds.
            if str(path) == canonical_path_str:
                raise OSError('simulated canonical write failure')
            return original_atomic_write(path, content)

        monkeypatch.setattr(_mod, 'atomic_write_file', failing_atomic_write)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            with pytest.raises(OSError, match='simulated canonical write failure'):
                cmd_supersede(
                    Namespace(
                        lesson_id='2025-01-01-01-001',
                        by='2025-01-02-01-001',
                        reason='atomic',
                    )
                )

        # Source body and frontmatter survive the failed canonical write.
        assert source.read_text(encoding='utf-8') == source_before

    def test_supersede_log_entry_records_merged_bytes(self, tmp_path, monkeypatch):
        """The script-execution log entry includes the appended byte count."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_pair(lessons_dir)

        captured: list[tuple] = []

        def fake_log_entry(*args, **kwargs):
            captured.append(args)

        monkeypatch.setattr(_mod, 'log_entry', fake_log_entry)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='log-test',
                )
            )

        assert result['status'] == 'success'
        merged_bytes = result['merged_bytes']
        assert merged_bytes > 0

        # cmd_supersede emits exactly one INFO log entry per success path.
        supersede_calls = [args for args in captured if 'Superseded lesson' in args[3]]
        assert len(supersede_calls) == 1
        log_message = supersede_calls[0][3]
        assert f'merged_bytes={merged_bytes}' in log_message
