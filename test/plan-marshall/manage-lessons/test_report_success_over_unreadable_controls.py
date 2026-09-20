#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Matched controls for the report-success-over-unreadable failure shape.

One control pair per member of the fixed population: a NEGATIVE control on the
path that used to lie, and a matched POSITIVE control proving the healthy path
on the same verb still reports success unchanged. A control that cannot fail
proves nothing, and a fix that broke every path would satisfy the negative half
on its own — the pairing is what makes each member's remedy detectable.

Every test drives the real ``manage-lessons.py`` argparse surface through
``run_script``, which is what keeps this suite disjoint from the handler-level
unit tests in ``test_lesson_id_resolution.py``, ``test_remove.py`` and
``test_add.py``: those pin the handlers, this pins what a CLI caller observes.
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest
from _lessons_helpers import SCRIPT_PATH
from conftest import run_script

READABLE_ID = '2026-02-02-03-001'
UNREADABLE_ID = '2026-02-02-03-002'
ABSENT_ID = '2026-02-02-03-099'

#: The members this suite carries a control pair for — the open members the
#: gate published whose remedy shipped in deliverables 2 to 4. Deliverable 2
#: closes two members through one code path (the collapsed resolver and the
#: two-meaning ``not_found``), so it contributes two rows rather than one.
CONTROLLED_MEMBERS = (
    'collapsed_resolver_read',
    'two_meaning_not_found',
    'stuck_lesson_retirement',
    'body_less_add',
)

#: The gate's published count of open members whose remedy this plan ships.
#: The suite asserts its own table against this number so a member that loses
#: its control pair is a red test rather than a silently smaller suite.
GATE_OPEN_MEMBER_COUNT = 4

# ⛔ Vacuity guard — an emptied member table would collect zero cases below and
# still report green.
assert CONTROLLED_MEMBERS, 'CONTROLLED_MEMBERS is empty'


def test_every_published_open_member_carries_a_control_pair():
    """The suite's member table matches the gate's published open-member count."""
    assert len(CONTROLLED_MEMBERS) == GATE_OPEN_MEMBER_COUNT
    assert len(set(CONTROLLED_MEMBERS)) == len(CONTROLLED_MEMBERS)


@pytest.fixture
def corpus(tmp_path):
    """A lessons store holding one readable and one unresolvable lesson."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True)
    (lessons_dir / f'{READABLE_ID}.md').write_text(
        f'id={READABLE_ID}\n'
        f'component=plan-marshall:manage-lessons\n'
        f'category=bug\n'
        f'status=active\n'
        f'created=2026-02-02\n'
        f'\n'
        f'# Readable Lesson\n'
        f'\n'
        f'Readable body.\n',
        encoding='utf-8',
    )
    (lessons_dir / f'{UNREADABLE_ID}.md').write_text(
        '# Unreadable Lesson\n\nBody with no metadata header.\n', encoding='utf-8'
    )
    with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
        yield lessons_dir


def _run(*argv):
    """Invoke the real CLI and return its result."""
    return run_script(SCRIPT_PATH, *argv)


class TestCollapsedResolverRead:
    """Member ``collapsed_resolver_read``: a read no longer reports a present file as missing."""

    def test_negative_control_unreadable_read_reports_unresolvable(self, corpus):
        """The path that lied: ``get`` against a present-but-unresolvable lesson."""
        result = _run('get', '--lesson-id', UNREADABLE_ID)

        assert 'status: error' in result.stdout
        assert 'error: unresolvable' in result.stdout
        assert 'not_found' not in result.stdout
        assert UNREADABLE_ID in result.stdout

    def test_positive_control_readable_read_still_succeeds(self, corpus):
        """The healthy twin: a resolvable lesson reads back unchanged."""
        result = _run('get', '--lesson-id', READABLE_ID)

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'unresolvable' not in result.stdout


class TestTwoMeaningNotFound:
    """Member ``two_meaning_not_found``: ``not_found`` means absent, and only absent."""

    def test_negative_control_the_two_states_render_differently(self, corpus):
        """An unresolvable lesson and an absent one no longer share one value."""
        unresolvable = _run('update', '--lesson-id', UNREADABLE_ID, '--category', 'bug')
        absent = _run('update', '--lesson-id', ABSENT_ID, '--category', 'bug')

        assert 'error: unresolvable' in unresolvable.stdout
        assert 'error: not_found' in absent.stdout

    def test_positive_control_a_readable_update_still_succeeds(self, corpus):
        """The healthy twin: updating a resolvable lesson is unaffected."""
        result = _run('update', '--lesson-id', READABLE_ID, '--category', 'improvement')

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout


class TestStuckLessonRetirement:
    """Member ``stuck_lesson_retirement``: a stuck lesson has an exit, and it is explicit."""

    def test_negative_control_refused_without_the_flag_and_retired_with_it(self, corpus):
        """Both halves of the opt-in: refused by default, retired on request.

        The refusal must leave the file in place — a refusal that still unlinked
        it would be the silent loss this member exists to close — and the
        retirement must leave a tombstone, which is what makes it auditable.
        """
        lesson_path = corpus / f'{UNREADABLE_ID}.md'
        tombstone = corpus / '.tombstones' / f'{UNREADABLE_ID}.json'

        refused = _run(
            'remove', '--lesson-id', UNREADABLE_ID, '--reason', 'stuck', '--coverage-verdict', 'obsolete', '--force'
        )

        assert 'error: unresolvable' in refused.stdout
        assert lesson_path.exists()
        assert not tombstone.exists()

        retired = _run(
            'remove',
            '--lesson-id',
            UNREADABLE_ID,
            '--reason',
            'stuck',
            '--coverage-verdict',
            'obsolete',
            '--force',
            '--allow-unreadable',
        )

        assert 'status: success' in retired.stdout
        assert not lesson_path.exists()
        assert tombstone.exists()
        payload = json.loads(tombstone.read_text(encoding='utf-8'))
        assert payload['lesson_state'] == 'unreadable'
        assert payload['coverage_verdict'] == 'obsolete'

    def test_positive_control_a_readable_lesson_retires_without_the_flag(self, corpus):
        """The healthy twin: the ordinary retirement needs no opt-in.

        Its tombstone carries no ``lesson_state``, so the marker names the
        unreadable route specifically rather than every retirement.
        """
        result = _run(
            'remove', '--lesson-id', READABLE_ID, '--reason', 'covered', '--coverage-verdict', 'redundant', '--force'
        )

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert not (corpus / f'{READABLE_ID}.md').exists()

        payload = json.loads((corpus / '.tombstones' / f'{READABLE_ID}.json').read_text(encoding='utf-8'))
        assert payload['coverage_verdict'] == 'redundant'
        assert 'lesson_state' not in payload


class TestBodyLessAdd:
    """Member ``body_less_add``: allocation reports the body state it left behind."""

    def _added_path(self, corpus: Path, stdout: str) -> Path:
        """Resolve the allocated lesson path from the CLI's TOON output."""
        for line in stdout.splitlines():
            if line.startswith('path: '):
                return Path(line.split('path: ', 1)[1].strip())
        raise AssertionError(f'no path line in add output: {stdout}')

    def test_negative_control_allocation_names_its_absent_body(self, corpus):
        """The path that lied: ``add`` reported a bare success over an empty record."""
        result = _run('add', '--component', 'test-component', '--category', 'bug', '--title', 'Fresh Stub')

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'body_state: absent' in result.stdout
        assert 'body_bytes: 0' in result.stdout

    def test_positive_control_a_filled_record_reports_the_written_state(self, corpus):
        """The healthy twin: once a body lands, the state flips and success is unchanged."""
        added = _run('add', '--component', 'test-component', '--category', 'bug', '--title', 'Stub To Fill')
        added_path = self._added_path(corpus, added.stdout)
        body_file = corpus.parent / 'body.md'
        body_file.write_text('A real body.\n', encoding='utf-8')

        filled = _run('set-body', '--lesson-id', added_path.stem, '--file', str(body_file))

        assert filled.success, f'Script failed: {filled.stderr}'
        assert 'status: success' in filled.stdout
        assert 'body_state: written' in filled.stdout
