#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the three-state lesson-id resolution seam.

Covers:

* ``resolve_lesson`` itself — one test per state (TestResolveLessonStates)
* The discriminator each migrated verb renders, each with the matched control
  that a genuinely absent id still reports ``not_found``
  (TestRenderedDiscriminatorPerVerb, TestSupersedeCanonicalRead)
* The two call sites that render no per-verb error pair and would otherwise
  drop an unresolvable lesson silently (TestAggregateReportsUnresolvable,
  TestCleanupSupersededUnresolvableBucket)
"""

from argparse import Namespace
from unittest.mock import patch
import pytest
from _lessons_helpers import (
    _mod,
    cmd_cleanup_superseded,
    cmd_get,
    cmd_remove,
    cmd_supersede,
    cmd_update,
)

READABLE_ID = '2026-01-01-02-001'
UNREADABLE_ID = '2026-01-01-02-002'
ABSENT_ID = '2026-01-01-02-099'


@pytest.fixture
def lessons_store(tmp_path):
    """A real lessons store on disk with the base-dir override in force."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True)
    with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
        yield lessons_dir


def _write_readable(lessons_dir, lesson_id=READABLE_ID, status='active', title='Readable Lesson'):
    """Write a lesson carrying a parseable ``key=value`` header."""
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(
        f'id={lesson_id}\n'
        f'component=plan-marshall:manage-lessons\n'
        f'category=bug\n'
        f'status={status}\n'
        f'created=2026-01-01\n'
        f'\n'
        f'# {title}\n'
        f'\n'
        f'Readable body.\n',
        encoding='utf-8',
    )
    return path


def _write_unreadable(lessons_dir, lesson_id=UNREADABLE_ID, title='Unreadable Lesson'):
    """Write a lesson file that EXISTS and yields no parseable metadata.

    The metadata parser stops at the first blank line or ``#``-leading line, so
    a file whose first line is the H1 carries no ``key=value`` header at all
    while its title and body remain perfectly readable.
    """
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(f'# {title}\n\nBody with no metadata header.\n', encoding='utf-8')
    return path


class TestResolveLessonStates:
    """``resolve_lesson`` reports which of three facts it reached."""

    def test_found_carries_the_parsed_record(self, lessons_store):
        """A lesson with a parseable header resolves to ``found``."""
        path = _write_readable(lessons_store)

        read = _mod.resolve_lesson(READABLE_ID)

        assert read.state == 'found'
        assert read.metadata['id'] == READABLE_ID
        assert read.title == 'Readable Lesson'
        assert read.body == 'Readable body.'
        assert read.path == path

    def test_absent_names_the_file_that_is_missing(self, lessons_store):
        """A lesson id with no file resolves to ``absent`` and names the path."""
        read = _mod.resolve_lesson(ABSENT_ID)

        assert read.state == 'absent'
        assert read.metadata == {}
        assert read.title == ''
        assert read.body == ''
        assert read.path == lessons_store / f'{ABSENT_ID}.md'

    def test_unreadable_keeps_the_title_and_body_it_could_read(self, lessons_store):
        """An existing file with no parseable header resolves to ``unreadable``.

        The title and body are carried through because the bytes were readable:
        the record is on disk, and a caller reporting the failure can name what
        it holds rather than reporting it as missing.
        """
        path = _write_unreadable(lessons_store)

        read = _mod.resolve_lesson(UNREADABLE_ID)

        assert read.state == 'unreadable'
        assert read.metadata == {}
        assert read.title == 'Unreadable Lesson'
        assert read.body == 'Body with no metadata header.'
        assert read.path == path
        assert 'no parseable key=value metadata header' in read.detail


def _invoke_get(lesson_id):
    return cmd_get(Namespace(lesson_id=lesson_id))


def _invoke_update(lesson_id):
    return cmd_update(Namespace(lesson_id=lesson_id, component='plan-marshall:manage-lessons', category=None))


def _invoke_remove(lesson_id):
    return cmd_remove(
        Namespace(
            lesson_id=lesson_id,
            force=True,
            reason='retired by test',
            coverage_verdict='redundant',
            covering_clause=None,
            covering_input=None,
        )
    )


def _invoke_supersede(lesson_id):
    return cmd_supersede(Namespace(lesson_id=lesson_id, by=READABLE_ID, reason='merged by test'))


MIGRATED_VERBS = [
    pytest.param(_invoke_get, id='get'),
    pytest.param(_invoke_update, id='update'),
    pytest.param(_invoke_remove, id='remove'),
    pytest.param(_invoke_supersede, id='supersede'),
]


class TestRenderedDiscriminatorPerVerb:
    """Every migrated verb renders the state it resolved, not a single value.

    Each unreadable assertion rides with the matched control that the same verb
    still reports ``not_found`` for a genuinely absent id — without the control,
    a verb that reported ``unresolvable`` for everything would pass too.
    """

    @pytest.mark.parametrize('invoke', MIGRATED_VERBS)
    def test_unreadable_lesson_reports_unresolvable(self, lessons_store, invoke):
        """An existing-but-unresolvable lesson is never reported as missing."""
        _write_readable(lessons_store)
        _write_unreadable(lessons_store)

        result = invoke(UNREADABLE_ID)

        assert result['status'] == 'error'
        assert result['error'] == 'unresolvable'
        assert result['path'] == str(lessons_store / f'{UNREADABLE_ID}.md')
        assert result['detail']

    @pytest.mark.parametrize('invoke', MIGRATED_VERBS)
    def test_absent_lesson_still_reports_not_found(self, lessons_store, invoke):
        """The matched control: a genuinely absent id keeps its error shape."""
        _write_readable(lessons_store)

        result = invoke(ABSENT_ID)

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_remove_leaves_the_unresolvable_lesson_on_disk(self, lessons_store):
        """``remove`` refusing an unresolvable lesson unlinks nothing.

        The refusal precedes the tombstone write and the unlink, so a lesson the
        verb declines to retire is still there to be retired another way.
        """
        _write_readable(lessons_store)
        path = _write_unreadable(lessons_store)
        original = path.read_text(encoding='utf-8')

        result = _invoke_remove(UNREADABLE_ID)

        assert result['error'] == 'unresolvable'
        assert path.read_text(encoding='utf-8') == original
        assert not (lessons_store / '.tombstones' / f'{UNREADABLE_ID}.json').exists()


class TestSupersedeCanonicalRead:
    """The canonical read renders its own pair of discriminators."""

    def test_unresolvable_canonical_reports_canonical_unresolvable(self, lessons_store):
        """An existing-but-unresolvable canonical is not reported as missing."""
        _write_readable(lessons_store, lesson_id=READABLE_ID)
        _write_unreadable(lessons_store)

        result = cmd_supersede(Namespace(lesson_id=READABLE_ID, by=UNREADABLE_ID, reason='merged by test'))

        assert result['status'] == 'error'
        assert result['error'] == 'canonical_unresolvable'
        assert result['path'] == str(lessons_store / f'{UNREADABLE_ID}.md')

    def test_absent_canonical_still_reports_canonical_not_found(self, lessons_store):
        """The matched control for the canonical read."""
        _write_readable(lessons_store, lesson_id=READABLE_ID)

        result = cmd_supersede(Namespace(lesson_id=READABLE_ID, by=ABSENT_ID, reason='merged by test'))

        assert result['status'] == 'error'
        assert result['error'] == 'canonical_not_found'


class TestAggregateReportsUnresolvable:
    """``aggregate`` names the corpus it read instead of shrinking it silently."""

    def _aggregate(self):
        return _mod.cmd_aggregate(Namespace(top_n=5))

    def test_unresolvable_lesson_is_reported_not_dropped(self, lessons_store):
        """A lesson that cannot be resolved appears in ``unresolvable``.

        It carries no status to filter on, so dropping it would shrink the
        substrate every count is computed over without saying so.
        """
        _write_readable(lessons_store, lesson_id=READABLE_ID)
        _write_unreadable(lessons_store)

        result = self._aggregate()

        assert result['status'] == 'success'
        assert [row['lesson_id'] for row in result['unresolvable']] == [UNREADABLE_ID]
        assert result['unresolvable'][0]['path'] == str(lessons_store / f'{UNREADABLE_ID}.md')
        assert result['lessons_scanned'] == 1

    def test_all_readable_corpus_reports_an_empty_unresolvable_list(self, lessons_store):
        """The matched control: a fully-readable corpus aggregates as before."""
        _write_readable(lessons_store, lesson_id=READABLE_ID)
        _write_readable(lessons_store, lesson_id=UNREADABLE_ID, title='Second Readable')

        result = self._aggregate()

        assert result['status'] == 'success'
        assert result['unresolvable'] == []
        assert result['lessons_scanned'] == 2


class TestCleanupSupersededUnresolvableBucket:
    """``cleanup-superseded`` never files an unresolvable lesson as tombstone-less."""

    def _write_tombstone(self, lessons_dir, lesson_id):
        tombstones = lessons_dir / '.tombstones'
        tombstones.mkdir(parents=True, exist_ok=True)
        (tombstones / f'{lesson_id}.json').write_text('{"lesson_id": "x"}\n', encoding='utf-8')

    def _cleanup(self, lesson_id):
        return cmd_cleanup_superseded(Namespace(lesson_id=[lesson_id], retention_days=None, dry_run=True))

    def test_unresolvable_lesson_with_a_tombstone_gets_its_own_outcome(self, lessons_store):
        """A tombstoned-but-unresolvable id lands in ``skipped_unresolvable``.

        The branch has already established that both the tombstone and the
        ``.md`` exist, so the ``skipped_no_tombstone`` bucket would assert the
        exact absence those two checks disproved.
        """
        _write_unreadable(lessons_store)
        self._write_tombstone(lessons_store, UNREADABLE_ID)

        result = self._cleanup(UNREADABLE_ID)

        assert result['status'] == 'success'
        assert [row['lesson_id'] for row in result['skipped_unresolvable']] == [UNREADABLE_ID]
        assert result['skipped_no_tombstone'] == []
        assert result['removed'] == []

    def test_genuinely_tombstone_less_id_still_lands_in_its_own_bucket(self, lessons_store):
        """The matched control that keeps the mislabelled-bucket fix detectable.

        Without it, a change that routed everything away from
        ``skipped_no_tombstone`` would pass just as well.
        """
        _write_readable(lessons_store, lesson_id=READABLE_ID, status='superseded')

        result = self._cleanup(READABLE_ID)

        assert result['status'] == 'success'
        assert [row['lesson_id'] for row in result['skipped_no_tombstone']] == [READABLE_ID]
        assert result['skipped_unresolvable'] == []
