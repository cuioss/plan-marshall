#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``add`` subcommand of manage-lessons.py.

Covers:

* Zone agreement between the id prefix and ``created`` (TestLessonIdClockZone)
* Collision-safe id allocation in ``cmd_add`` / ``cmd_from_error``
  (TestCollisionSafeAllocation) — these tests cover the
  ``_allocate_and_write_scaffold`` helper that both subcommands share;
  ``cmd_from_error`` is exercised in one regression test to pin the shared
  contract rather than be split across files.
"""


import json
import time
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
import pytest
from _lessons_helpers import (
    _FakeDatetime,
    _mod,
    cmd_add,
    cmd_from_error,
)


# =============================================================================
# Tier 2: id prefix / created-field zone agreement
# =============================================================================


@pytest.fixture
def europe_berlin_tz(monkeypatch):
    """Pin the process-local timezone to ``Europe/Berlin`` for one test.

    ``Europe/Berlin`` is UTC+2 in July (CEST), so a late-evening UTC instant
    already falls on the next local calendar day — the divergence window this
    module's zone regression needs. ``time.tzset()`` is what makes the ``TZ``
    change visible to ``datetime.astimezone()``; it must be re-run on teardown
    so the restored ``TZ`` takes effect for subsequent tests.
    """
    monkeypatch.setenv('TZ', 'Europe/Berlin')
    time.tzset()
    try:
        yield
    finally:
        monkeypatch.undo()
        time.tzset()


class TestLessonIdClockZone:
    """The id prefix date and the ``created`` field must name the same day.

    ``get_next_id`` derived its ``{date}-{hour}`` prefix from the LOCAL wall
    clock while ``cmd_add`` stamps ``created`` from UTC. For any instant inside
    the local-vs-UTC divergence window the two disagreed: frozen at
    ``2026-07-28T22:30Z`` — ``2026-07-29 00:30`` in Europe/Berlin — the id
    claimed the 29th while ``created`` said the 28th, so retention math keyed on
    ``created`` and lookups keyed on the id prefix read different dates.

    The test is zone-sensitive by construction: under a UTC host (as CI runs)
    the window does not exist and the assertion is vacuous, so the fixture pins
    a UTC-offset zone for the duration of the test.
    """

    def test_id_prefix_date_matches_created_field_inside_the_divergence_window(
        self, tmp_path, monkeypatch, europe_berlin_tz
    ):
        """The allocated id's date segment must equal the ``created`` metadata."""
        from datetime import UTC as real_utc
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        # 22:30 UTC on the 28th is 00:30 local on the 29th under CEST.
        frozen = real_datetime(2026, 7, 28, 22, 30, 0, tzinfo=real_utc)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='bug',
                    title='Zone Boundary Lesson',
                    bundle=None,
                )
            )
            metadata, _title, _body = _mod.read_lesson(result['id'])

        assert result['status'] == 'success'
        assert metadata['created'] == '2026-07-28'
        assert result['id'][:10] == metadata['created']


# =============================================================================
# Tier 2: Collision-safe id allocation in cmd_add and cmd_from_error
# =============================================================================


class TestCollisionSafeAllocation:
    """Regression tests for collision-safe lesson id allocation.

    The original ``cmd_add`` / ``cmd_from_error`` allocated an id via
    ``get_next_id()`` and wrote unconditionally — which silently overwrote any
    existing lesson file when ``get_next_id`` returned a colliding id (e.g.
    after a stale-cache filesystem read or a concurrent caller). The
    collision-safe helper uses ``open(path, "x")`` (kernel-enforced exclusive
    create) with a bounded retry of 99 attempts, logs a WARNING per collision to
    ``script-execution.log``, and returns ``error: id_exhausted`` on
    exhaustion. These tests pin that contract.
    """

    def _seed_existing_lesson(self, lessons_dir: Path, lesson_id: str, marker: str) -> Path:
        """Create a sentinel lesson file the new allocation must NOT overwrite.

        Returns the path so callers can assert the file's content is preserved.
        """
        path = lessons_dir / f'{lesson_id}.md'
        path.write_text(
            f'id={lesson_id}\ncomponent=existing\ncategory=bug\ncreated=2025-01-01\n\n# {marker}\n',
            encoding='utf-8',
        )
        return path

    def test_add_does_not_overwrite_on_id_collision(self, tmp_path, monkeypatch):
        """``cmd_add`` must allocate a fresh id when the candidate already exists.

        Pre-creates a file at ``2025-01-01-02-001.md`` (the id ``get_next_id``
        would naively return for the frozen clock), runs ``cmd_add``, and
        asserts the new lesson lands at ``-002`` while the seeded ``-001`` file
        is byte-for-byte unchanged.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        seeded = self._seed_existing_lesson(lessons_dir, '2025-01-01-02-001', 'Existing Lesson')
        seeded_content = seeded.read_text(encoding='utf-8')

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))
        # Force ``get_next_id`` to collide with the seeded file regardless of
        # the directory listing — keeps the test focused on the collision
        # branch in ``_allocate_and_write_scaffold``.
        monkeypatch.setattr(_mod, 'get_next_id', lambda: '2025-01-01-02-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='new-component',
                    category='improvement',
                    title='Fresh Lesson',
                    bundle=None,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-02-002'
        # Seeded file untouched.
        assert seeded.read_text(encoding='utf-8') == seeded_content
        # Fresh lesson written at the next sequential id.
        fresh_path = Path(result['path'])
        assert fresh_path == (lessons_dir / '2025-01-01-02-002.md').resolve()
        assert fresh_path.exists()
        assert '# Fresh Lesson' in fresh_path.read_text(encoding='utf-8')

    def test_add_logs_warning_on_collision(self, tmp_path, monkeypatch):
        """A ``[WARNING] id_collision`` line must be appended to ``script-execution.log``.

        The exact format documented in the helper docstring is
        ``[WARNING] (plan-marshall:manage-lessons) id_collision at {path} —
        retrying with seq+1`` — this test pins the message substring rather
        than the full line so the timestamp/hash prefix from
        ``format_log_entry`` does not couple the assertion.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        self._seed_existing_lesson(lessons_dir, '2025-01-01-02-001', 'Seed')

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))
        monkeypatch.setattr(_mod, 'get_next_id', lambda: '2025-01-01-02-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_add(
                Namespace(
                    component='new-component',
                    category='bug',
                    title='Fresh Lesson',
                    bundle=None,
                )
            )

            # ``log_entry`` writes to the global script-execution log because
            # we pass ``plan_id=None``. Path resolution mirrors
            # ``plan_logging.get_log_path(None, 'script')``.
            log_files = list((tmp_path / 'logs').glob('script-execution-*.log'))

        assert log_files, 'expected at least one script-execution log file'
        log_text = '\n'.join(p.read_text(encoding='utf-8') for p in log_files)
        assert '[WARNING]' in log_text
        assert '(plan-marshall:manage-lessons) id_collision' in log_text
        assert '2025-01-01-02-001.md' in log_text
        assert 'retrying with seq+1' in log_text

    def test_from_error_does_not_overwrite_on_id_collision(self, tmp_path, monkeypatch):
        """Parallel collision test for ``cmd_from_error`` — must allocate a fresh id.

        Pinned here (rather than under ``test_from_error.py``) because the
        regression covers the shared ``_allocate_and_write_scaffold`` helper —
        keeping the four collision tests in one class preserves the regression
        narrative documented in the originating bug write-up.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        seeded = self._seed_existing_lesson(lessons_dir, '2025-01-01-02-001', 'Existing')
        seeded_content = seeded.read_text(encoding='utf-8')

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))
        monkeypatch.setattr(_mod, 'get_next_id', lambda: '2025-01-01-02-001')

        error_context = json.dumps(
            {
                'component': 'maven-build',
                'error': 'Build failed',
                'solution': 'Add missing dependency',
            }
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'success'
        assert result['created_from'] == 'error_context'
        assert result['id'] == '2025-01-01-02-002'
        # Seeded file untouched — the bug under test was silent overwrite.
        assert seeded.read_text(encoding='utf-8') == seeded_content
        # Fresh from-error lesson exists at the next sequential id with the
        # error scaffold body.
        fresh_path = lessons_dir / '2025-01-01-02-002.md'
        assert fresh_path.exists()
        fresh_content = fresh_path.read_text(encoding='utf-8')
        assert '## Error' in fresh_content
        assert 'Build failed' in fresh_content

    def test_add_raises_id_exhausted_after_99_collisions(self, tmp_path, monkeypatch):
        """After ``MAX_ID_ALLOCATION_RETRIES`` collisions ``cmd_add`` must error.

        Pre-creates 99 colliding files at ``-001`` through ``-099``, forces
        ``get_next_id`` to return ``-001`` so every retry hits ``FileExistsError``,
        and asserts ``cmd_add`` returns ``status: error`` / ``error: id_exhausted``
        rather than silently overwriting ``-099`` (the original bug) or escaping
        the bound.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        seeded_content_by_id = {}
        for seq in range(1, 100):
            lesson_id = f'2025-01-01-02-{seq:03d}'
            path = self._seed_existing_lesson(lessons_dir, lesson_id, f'Seed {seq}')
            seeded_content_by_id[lesson_id] = path.read_text(encoding='utf-8')

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))
        monkeypatch.setattr(_mod, 'get_next_id', lambda: '2025-01-01-02-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='new-component',
                    category='bug',
                    title='Fresh Lesson',
                    bundle=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'id_exhausted'
        # No seeded file was overwritten — the bug under test was silent
        # clobber of ``-099`` once the retry budget was exhausted.
        for lesson_id, original in seeded_content_by_id.items():
            current = (lessons_dir / f'{lesson_id}.md').read_text(encoding='utf-8')
            assert current == original, f'lesson {lesson_id} was overwritten'
