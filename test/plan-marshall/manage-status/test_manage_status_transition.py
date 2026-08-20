#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back."""


import os
from argparse import Namespace
from pathlib import Path

from _manage_status_transition_fixtures import SCRIPT_PATH, _lifecycle, cmd_delete_plan

from conftest import load_script_module, run_script


def test_delete_plan_destination_claim_does_not_rely_on_an_exists_probe(
    plan_context, monkeypatch
):
    """The incumbent survives even when an ``exists()`` probe reports absence.

    ``destination.exists()`` and the move were a TOCTOU pair: a destination
    created between the two was silently overwritten and the incumbent lesson
    lost. Lying about ``exists()`` simulates exactly that window — the claim
    must be a no-replace create, so the collision is caught by the claim itself
    and reported as the ordinary ``destination_exists`` skip.
    """
    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    incumbent = lessons_dir / '2025-08-08-008.md'
    incumbent.write_text('id=2025-08-08-008\n\n# Incumbent\n\nCorpus copy.\n')

    plan_dir = plan_context.plan_dir_for('toctou-carry-back')
    (plan_dir / 'lesson-2025-08-08-008.md').write_text(
        'id=2025-08-08-008\ncomponent=foo\ncategory=bug\ncreated=2025-08-08\n\n# Carried\n\nPlan copy.\n'
    )

    original_exists = Path.exists

    def lying_exists(self, *args, **kwargs):
        # Scoped to the one destination path, matched on name rather than
        # equality so a symlinked fixture root (macOS /tmp) still hits.
        if self.name == incumbent.name and self.parent.name == lessons_dir.name:
            return False
        return original_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'exists', lying_exists)

    result = cmd_delete_plan(Namespace(plan_id='toctou-carry-back', no_restore_lessons=False))

    assert result['status'] == 'error'
    assert result['error'] == 'lesson_carry_back_incomplete'
    assert result['skipped_lessons'] == [
        {'lesson_id': '2025-08-08-008', 'reason': 'destination_exists'}
    ]
    assert result['restored_lesson_ids'] == []

    monkeypatch.undo()
    assert 'Corpus copy.' in incumbent.read_text(), (
        'The incumbent corpus lesson was overwritten — the destination claim '
        'is still gated on a separate exists() probe instead of a no-replace '
        'create, so a destination appearing inside the window is clobbered.'
    )
    # The veto held: the plan directory still holds its only copy.
    assert plan_dir.exists()
    assert (plan_dir / 'lesson-2025-08-08-008.md').exists()


def test_delete_plan_writes_through_the_claim_instead_of_reopening_by_path(
    plan_context, monkeypatch
):
    """The claimed destination is written THROUGH its fd, never reopened by path.

    ``O_EXCL`` buys an atomic collision test, and closing the claim fd to hand
    the PATH back to a copy helper gives that guarantee straight back: the
    reopen is a SECOND name lookup, so an entry substituted under the name in
    between is what gets written — and a ``'wb'`` open follows a symlink,
    truncating whatever it points at. The claim then protects the collision test
    and not the write it exists to make safe.

    The substitution is made deterministic rather than raced: closing a
    descriptor that IS the claimed destination replaces that destination with a
    symlink to an external victim. Only an implementation that closes the claim
    and then addresses the destination by NAME can reach that swap; one that
    writes through the descriptor addresses the claimed inode, which no later
    substitution of the name can redirect.
    """
    victim = plan_context.fixture_dir / 'victim-outside-the-corpus.md'
    victim.write_text('# Victim\n\nAn unrelated file the carry-back has no claim on.\n')

    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    destination = lessons_dir / '2025-09-09-009.md'

    plan_dir = plan_context.plan_dir_for('claim-writethrough')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-09-09-009.md').write_text(
        'id=2025-09-09-009\ncomponent=foo\ncategory=bug\ncreated=2025-09-09\n\n# Carried\n\nPlan copy.\n'
    )

    real_close = os.close

    def swapping_close(fd):
        # Scoped to a descriptor open on the claimed destination itself, so the
        # swap is reachable only by an implementation that closes the claim
        # before writing. Every unrelated close falls through untouched.
        try:
            claimed = (
                not destination.is_symlink()
                and os.fstat(fd).st_ino == destination.stat().st_ino
            )
        except OSError:
            claimed = False
        if claimed:
            destination.unlink()
            destination.symlink_to(victim)
        return real_close(fd)

    monkeypatch.setattr(os, 'close', swapping_close)

    result = cmd_delete_plan(Namespace(plan_id='claim-writethrough', no_restore_lessons=False))

    monkeypatch.undo()

    assert result['status'] == 'success'
    assert result['lesson_carry_back_action'] == 'restored'
    assert result['restored_lesson_ids'] == ['2025-09-09-009']

    assert '# Victim' in victim.read_text(), (
        'The carry-back reopened the claimed destination by path, followed a '
        'symlink substituted under that name, and truncated an unrelated file — '
        'the copy must be written through the claim descriptor, which names the '
        'claimed inode and cannot be redirected.'
    )
    # The lesson landed on the claimed inode, not through a substituted name.
    assert not destination.is_symlink()
    assert '# Carried' in destination.read_text()
    assert not plan_dir.exists()


def test_carry_back_vocabulary_agrees_with_restore_from_plan(plan_context):
    """The relationship is a STRICT superset by exactly one value.

    ``CARRY_BACK_ACTIONS`` is now DERIVED as
    ``RESTORE_ACTIONS | {'not_attempted'}``, so "the shared four agree" holds by
    construction and asserting it here would be vacuous. What the construction
    does NOT guarantee is that the union is strict: were ``not_attempted`` ever
    added upstream to ``RESTORE_ACTIONS``, the union would silently become a
    no-op and the two surfaces would claim the false identity the docstring
    explicitly warns against. The strictness and the exact-by-one cardinality
    are what this test pins — they also catch a regression to re-listed
    literals that drop or gain a member.
    """
    lessons_query = load_script_module(
        'plan-marshall', 'manage-lessons', '_lessons_query.py', '_transition_lessons_query'
    )

    # The one thing the union cannot enforce about itself: that it adds a value.
    assert 'not_attempted' not in lessons_query.RESTORE_ACTIONS, (
        'not_attempted leaked into RESTORE_ACTIONS, collapsing the union into a '
        'no-op and making the two vocabularies equal — the identity claim the '
        'CARRY_BACK_ACTIONS docstring exists to deny.'
    )
    assert len(_lifecycle.CARRY_BACK_ACTIONS) == len(lessons_query.RESTORE_ACTIONS) + 1
    assert _lifecycle.CARRY_BACK_ACTIONS > lessons_query.RESTORE_ACTIONS

    # ``restored`` is the value the two used to define incompatibly.
    assert 'restored' in _lifecycle.CARRY_BACK_ACTIONS
    assert 'restore_incomplete' in _lifecycle.CARRY_BACK_ACTIONS


def test_unresolvable_store_over_an_empty_plan_dir_is_still_the_benign_zero(
    plan_context, monkeypatch
):
    """Store-unresolved does NOT force ``plan_dir_unresolved`` unconditionally.

    The mirror of the carried-lesson case above. The directory WAS scanned and
    held no ``lesson-*.md``, so nothing needed to land and ``no_lesson_file`` is
    the honest action even though the corpus was never reached. The
    could-not-look half is carried by ``lesson_store_resolution: unresolved``.

    Pins the precedence the ``CARRY_BACK_ACTIONS`` docstring states: the two
    fields answer different questions — ``action`` says what the scan found,
    ``store_resolution`` says whether the corpus was reachable — and a consumer
    reading either alone gets a wrong answer on this branch.
    """
    import _lessons_io

    monkeypatch.setattr(
        _lessons_io,
        'resolve_lesson_store',
        lambda subpath=_lessons_io.DIR_LESSONS: _lessons_io.LessonStore(
            None, 'unresolved', 'cannot resolve the main-anchored store (test stub)'
        ),
    )

    plan_dir = plan_context.plan_dir_for('unresolved-store-empty-plan')
    (plan_dir / 'request.md').write_text('# Request')

    result = cmd_delete_plan(
        Namespace(plan_id='unresolved-store-empty-plan', no_restore_lessons=False)
    )

    # No lesson was at risk, so the veto does not fire and the delete proceeds.
    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_carry_back_action'] == 'no_lesson_file'
    assert result['lesson_carry_back_action'] != 'plan_dir_unresolved'
    # The could-not-look fact still rides the payload on the other field.
    assert result['lesson_store_resolution'] == 'unresolved'
    assert result['lessons_dir'] == ''
    assert result['skipped_lessons'] == []
    assert not plan_dir.exists()


def test_cli_transition_not_found_exits_zero(plan_context):
    """Regression: transition with missing status.json exits 0 with TOON error output."""
    result = run_script(SCRIPT_PATH, 'transition', '--plan-id', 'nonexistent', '--completed', '1-init')
    assert result.success, f'Should exit 0, got: {result.stderr}'
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


def test_collect_modified_files_helper_is_removed():
    """The ``_collect_modified_files`` producer no longer exists.

    The footprint ledger was deleted in favour of the on-demand
    compute-footprint verb; the seeding helper must be gone so no code
    path can re-introduce a persisted modified_files write at transition.
    """
    assert not hasattr(_lifecycle, '_collect_modified_files'), (
        '_collect_modified_files must be deleted — the 5-execute transition '
        'no longer seeds references.modified_files (footprint is derived '
        'on-demand via manage-references compute-footprint).'
    )
