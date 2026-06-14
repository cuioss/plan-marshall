#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for the ``add`` subcommand of manage-lessons.py.

Covers:

* ``cmd_add`` direct invocation (TestCmdAdd)
* ``cmd_add`` CLI plumbing via subprocess (TestCliPlumbingAdd)
* ``status=active`` frontmatter seeding on add (TestStatusFrontmatterOnAdd)
* Hour-aware id generation backing ``cmd_add`` (TestGetNextIdHourAware)
* Collision-safe id allocation in ``cmd_add`` / ``cmd_from_error``
  (TestCollisionSafeAllocation) — these tests cover the
  ``_allocate_and_write_scaffold`` helper that both subcommands share;
  ``cmd_from_error`` is exercised in one regression test to pin the shared
  contract rather than be split across files.
"""

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from _lessons_helpers import (
    SCRIPT_PATH,
    _FakeDatetime,
    _mod,
    cmd_add,
    cmd_from_error,
    get_next_id,
)
from conftest import run_script


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
        to a local-aware instant at ``2025-01-01 02:15:00``, then asserts that
        ``get_next_id`` returns ``2025-01-01-02-001`` — the hour prefix rolls
        forward and the sequence number resets because no prior lesson exists
        for hour 02.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        # Legacy-format-for-hour-scheme fixture from hour 01.
        (lessons_dir / '2025-01-01-01-001.md').write_text(
            'id=2025-01-01-01-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# seed\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 15, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-001'

    def test_get_next_id_increments_within_same_hour(self, tmp_path, monkeypatch):
        """Sequence number must increment when multiple lessons share an hour."""
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        (lessons_dir / '2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# seed\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-002'

    def test_get_next_id_ignores_legacy_ids_when_computing_hour_sequence(self, tmp_path, monkeypatch):
        """Legacy ``YYYY-MM-DD-NNN`` files must not collide with a new hour prefix.

        Seeds a legacy lesson ``2025-01-01-005.md`` (no hour segment), freezes
        ``now`` to hour 03, and asserts ``get_next_id`` returns ``2025-01-01-03-001``
        rather than reading the legacy counter. The legacy file must remain
        on disk untouched — this test only covers the generation path.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        legacy_path = lessons_dir / '2025-01-01-005.md'
        legacy_content = 'id=2025-01-01-005\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# legacy seed\n'
        legacy_path.write_text(legacy_content)

        frozen = real_datetime(2025, 1, 1, 3, 0, 0)
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
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        plan_dir = tmp_path / 'plans' / 'lesson-2025-01-01-02-001'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# converted\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-002'

    def test_get_next_id_skips_tombstone_only_id(self, tmp_path, monkeypatch):
        """A ``.tombstones/{prefix}-001.json`` must reserve sequence 001.

        Seeds a tombstone with no live ``.md`` and no plan dir, freezes the clock
        to the same prefix, and asserts ``get_next_id`` returns ``-002``.
        """
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

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-002'


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


# =============================================================================
# Tier 2: status frontmatter on new lessons
# =============================================================================


class TestStatusFrontmatterOnAdd:
    """``cmd_add`` and ``cmd_from_error`` must seed ``status=active``."""

    def test_add_writes_status_active(self, tmp_path):
        """Newly added lessons must include ``status=active`` in the metadata header."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='bug',
                    title='Status Active Default',
                    bundle=None,
                )
            )

        assert result['status'] == 'success'
        content = Path(result['path']).read_text(encoding='utf-8')
        assert 'status=active' in content

    def test_from_error_writes_status_active(self, tmp_path):
        """Error-context lessons must include ``status=active`` in the metadata header."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps({'component': 'cmpt', 'error': 'boom', 'solution': 'fix it'})

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'success'
        # Locate the file by id in the lessons dir.
        lesson_path = next(lessons_dir.glob(f'{result["id"]}.md'))
        assert 'status=active' in lesson_path.read_text(encoding='utf-8')


# =============================================================================
# Tier 3: CLI plumbing (subprocess) - kept for end-to-end coverage
# =============================================================================


class TestCliPlumbingAdd:
    """Subprocess test for add subcommand CLI plumbing."""

    def test_cli_add_creates_lesson(self, tmp_path):
        """Should create a lesson via CLI and produce TOON output with an absolute path."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component',
                'test-component',
                '--category',
                'bug',
                '--title',
                'Test Lesson',
            )

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'component: test-component' in result.stdout
        assert 'category: bug' in result.stdout
        assert 'path: ' in result.stdout
        assert 'file: ' not in result.stdout

    def test_cli_invalid_category_rejected_by_argparse(self, tmp_path):
        """Should reject invalid category at argparse level."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component',
                'test-component',
                '--category',
                'invalid-category',
                '--title',
                'Test',
            )

        assert not result.success
        assert 'invalid choice' in result.stderr

    def test_cli_detail_flag_rejected(self, tmp_path):
        """Should reject the legacy --detail flag at argparse level."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component',
                'test-component',
                '--category',
                'bug',
                '--title',
                'Test Lesson',
                '--detail',
                'Legacy inline body that must no longer be accepted',
            )

        assert not result.success
        assert 'unrecognized arguments' in result.stderr


# =============================================================================
# Tier 2: main-anchored lessons corpus via the shared utility (deliverable 3)
# =============================================================================


class TestLessonsCorpusMainAnchoring:
    """The lessons corpus resolves to the MAIN checkout via
    ``resolve_main_anchored_path`` regardless of caller cwd (deliverable 3).

    Audit finding: phase-5 ``execute-task`` records lessons with cwd pinned to a
    worktree. With the corpus main-anchored, a ``cmd_add`` from a worktree cwd
    lands the lesson under MAIN's ``lessons-learned``, NOT the worktree's empty
    corpus. The override-first branch keeps every PLAN_BASE_DIR-based test green.
    """

    def test_add_writes_lesson_under_main_base_from_worktree_cwd(self, tmp_path, monkeypatch):
        """``cmd_add`` from a worktree cwd lands the lesson under MAIN's corpus."""
        # PLAN_BASE_DIR = main-checkout stand-in; cwd pinned into a
        # worktree fixture that owns its OWN .plan/local (empty corpus).
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'lessons-learned').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local' / 'lessons-learned').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        result = cmd_add(
            Namespace(
                component='worktree-cwd-component',
                category='bug',
                title='Worktree-recorded Lesson',
                bundle=None,
            )
        )

        # the lesson landed under MAIN's lessons-learned, NOT the worktree.
        assert result['status'] == 'success'
        path = Path(result['path'])
        assert path.parent == (main_base / 'lessons-learned').resolve()
        assert path.exists()
        assert not list((worktree / '.plan' / 'local' / 'lessons-learned').glob('*.md'))
        # The corpus resolver itself anchors at MAIN regardless of cwd.
        assert _mod.get_lessons_dir() == (main_base / 'lessons-learned')

    def test_get_next_id_scans_main_plans_corpus_from_worktree_cwd(self, tmp_path, monkeypatch):
        """id-allocation scans MAIN's plans corpus, not the worktree's.

        Seeds a plan-derived lesson reserving sequence 001 under MAIN's corpus;
        from a worktree cwd ``get_next_id`` must clear that reservation and
        return ``-002``, proving the ``plans`` scan is main-anchored.
        """
        from datetime import datetime as real_datetime

        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'lessons-learned').mkdir(parents=True)
        plan_dir = main_base / 'plans' / 'lesson-2025-01-01-02-001'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# converted\n'
        )
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        next_id = get_next_id()

        # the main-anchored plans scan reserved 001 → next is 002.
        assert next_id == '2025-01-01-02-002'
