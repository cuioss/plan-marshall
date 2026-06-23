#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""CLI plumbing tests for ``remove``, ``supersede``, and ``cleanup-superseded``.

Tier 3 (subprocess) tests covering the argparse wiring for the three
removal-related subcommands. The direct-invocation behaviours live in
``test_remove.py``, ``test_supersede.py``, and
``test_cleanup_superseded.py`` respectively — this file only pins the
shape of the CLI surface.
"""

from pathlib import Path
from unittest.mock import patch

from _lessons_helpers import SCRIPT_PATH
from conftest import run_script


def _seed_cli_lesson(tmp_path: Path, lesson_id: str, title: str, status: str = 'active') -> None:
    """Seed a minimal lesson file under ``{tmp_path}/lessons-learned``."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    (lessons_dir / f'{lesson_id}.md').write_text(
        f'id={lesson_id}\ncomponent=test\ncategory=bug\nstatus={status}\n'
        f'created=2025-01-01\n\n# {title}\n\nBody.\n',
        encoding='utf-8',
    )


class TestCliPlumbingRemoveSupersede:
    """Subprocess test for ``remove`` and ``supersede`` subcommand wiring."""

    def test_cli_remove_force(self, tmp_path):
        """``manage-lessons remove --force`` deletes the lesson via the CLI."""
        _seed_cli_lesson(tmp_path, '2025-01-01-01-001', 'Removable')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-001',
                '--reason',
                'duplicate',
                '--force',
            )

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'id: 2025-01-01-01-001' in result.stdout
        assert not (tmp_path / 'lessons-learned' / '2025-01-01-01-001.md').exists()

    def test_cli_remove_requires_reason(self, tmp_path):
        """``remove`` without ``--reason`` is rejected at argparse."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-001',
                '--force',
            )

        assert not result.success
        assert '--reason' in result.stderr

    def test_cli_supersede(self, tmp_path):
        """``manage-lessons supersede`` wires the redirect via the CLI."""
        _seed_cli_lesson(tmp_path, '2025-01-01-01-001', 'Source')
        _seed_cli_lesson(tmp_path, '2025-01-02-01-001', 'Canonical')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'supersede',
                '--lesson-id',
                '2025-01-01-01-001',
                '--by',
                '2025-01-02-01-001',
                '--reason',
                'merged',
            )

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'superseded_by: 2025-01-02-01-001' in result.stdout

    def test_cli_cleanup_superseded_rejects_combined_flags(self, tmp_path):
        """``cleanup-superseded`` rejects ``--lesson-id`` combined with ``--retention-days``.

        Argparse mutually-exclusive groups raise SystemExit(2) and write the
        error to stderr. We assert the failure is loud at the CLI boundary so
        callers cannot accidentally silently fall back to one mode.
        """
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'cleanup-superseded',
                '--lesson-id',
                '2025-07-01-01-001',
                '--retention-days',
                '7',
            )

        assert not result.success
        # argparse emits the offending option in the usage error message.
        assert 'not allowed with' in result.stderr
