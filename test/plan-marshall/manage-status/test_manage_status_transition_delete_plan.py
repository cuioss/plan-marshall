#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back."""


import os
from argparse import Namespace
from pathlib import Path

from _manage_status_transition_fixtures import cmd_delete_plan


def test_delete_plan_refuses_when_carried_lesson_collides(plan_context):
    """A colliding lesson id is a reported skip AND vetoes the deletion.

    The sharpest edge on the lesson path: the plan directory holds the only copy
    of the carried lesson, so a silent per-file skip followed by an
    unconditional delete destroys it with no signal. The veto is what makes that
    unreachable — the directory MUST survive.

    The same arrangement pins the action vocabulary: ``restored`` asserts every
    carried lesson landed, and here none did, so the honest value is
    ``restore_incomplete``. Reporting ``restored`` over an empty
    ``restored_lesson_ids`` is the same overclaim ``restore-from-plan`` made on
    a first-file collision, and the two surfaces must answer it the same way.
    """
    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    (lessons_dir / '2025-03-03-003.md').write_text('id=2025-03-03-003\n\n# Incumbent\n\nCorpus copy.\n')

    plan_dir = plan_context.plan_dir_for('collide-plan')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-03-03-003.md').write_text(
        'id=2025-03-03-003\ncomponent=foo\ncategory=bug\ncreated=2025-03-03\n\n# Carried\n\nPlan copy.\n'
    )

    result = cmd_delete_plan(Namespace(plan_id='collide-plan', no_restore_lessons=False))

    assert result['status'] == 'error'
    assert result['error'] == 'lesson_carry_back_incomplete'
    assert result['action'] == 'refused'
    assert result['lesson_carry_back_action'] == 'restore_incomplete'
    assert result['lesson_carry_back_action'] != 'restored'
    assert result['skipped_lessons'] == [
        {'lesson_id': '2025-03-03-003', 'reason': 'destination_exists'}
    ]
    assert result['restored_lesson_ids'] == []

    # The veto held: the plan directory and its only copy of the lesson survive.
    assert plan_dir.exists()
    assert (plan_dir / 'lesson-2025-03-03-003.md').exists()
    # The incumbent corpus entry was not clobbered either.
    assert 'Corpus copy.' in (lessons_dir / '2025-03-03-003.md').read_text()


def test_delete_plan_reports_unresolvable_store_instead_of_nothing_to_restore(
    plan_context, monkeypatch
):
    """An unresolvable store reports could-not-look, and vetoes the deletion.

    Distinct from the collision case above: here the carry-back cannot reach the
    corpus at all. Reporting that as a benign "nothing to restore" and deleting
    anyway is the fail-open direction this site carried; the carried lesson is
    un-landed, so the veto must fire on this path too.
    """
    import _lessons_io

    monkeypatch.setattr(
        _lessons_io,
        'resolve_lesson_store',
        lambda subpath=_lessons_io.DIR_LESSONS: _lessons_io.LessonStore(
            None, 'unresolved', 'cannot resolve the main-anchored store (test stub)'
        ),
    )

    plan_dir = plan_context.plan_dir_for('unresolved-store-plan')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-04-04-004.md').write_text(
        'id=2025-04-04-004\ncomponent=foo\ncategory=bug\ncreated=2025-04-04\n\n# Carried\n\nBody.\n'
    )

    result = cmd_delete_plan(Namespace(plan_id='unresolved-store-plan', no_restore_lessons=False))

    assert result['status'] == 'error'
    assert result['error'] == 'lesson_carry_back_incomplete'
    assert result['lesson_carry_back_action'] == 'plan_dir_unresolved'
    assert result['lesson_store_resolution'] == 'unresolved'
    assert result['skipped_lessons'] == [
        {'lesson_id': '2025-04-04-004', 'reason': 'store_unresolved'}
    ]

    # The plan directory holding the only copy survives the failure to look.
    assert plan_dir.exists()
    assert (plan_dir / 'lesson-2025-04-04-004.md').exists()


def test_delete_plan_refuses_symlinked_lesson_and_spares_its_target(plan_context):
    """A symlinked lesson-*.md is rejected, and its target is left where it is.

    Deriving the id from a RESOLVED path let a symlink walk the carry-back out
    of the plan directory: the traversal guard then inspected the target's stem
    (which is perfectly well-formed), and the move relocated — i.e. REMOVED —
    an arbitrary external file, on the path whose caller deletes the plan
    directory next. The rejection must be a REPORTED skip, so it fires the veto
    rather than dropping the entry silently.
    """
    outside = plan_context.fixture_dir / 'outside-the-plan.md'
    outside.write_text('id=2025-06-06-006\n\n# External\n\nNot the plan to move.\n')

    plan_dir = plan_context.plan_dir_for('symlink-carry-back')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-06-06-006.md').symlink_to(outside)

    result = cmd_delete_plan(Namespace(plan_id='symlink-carry-back', no_restore_lessons=False))

    assert result['status'] == 'error'
    assert result['error'] == 'lesson_carry_back_incomplete'
    assert result['lesson_carry_back_action'] == 'restore_incomplete'
    assert result['skipped_lessons'] == [
        {'lesson_id': '2025-06-06-006', 'reason': 'unsafe_source'}
    ]
    assert result['restored_lesson_ids'] == []

    # The external target is an ordinary file the plan has no claim on; it must
    # still be there, with its content untouched.
    assert outside.exists(), (
        'The carry-back followed a symlink out of the plan directory and moved '
        'the external target away — the id must be derived from the MATCHED '
        'name and non-regular entries rejected before any move.'
    )
    assert '# External' in outside.read_text()
    # Nothing was written into the corpus under that id either.
    assert not (plan_context.fixture_dir / 'lessons-learned' / '2025-06-06-006.md').exists()
    # The veto held.
    assert plan_dir.exists()


def test_delete_plan_refuses_non_regular_lesson_entry(plan_context):
    """A non-regular ``lesson-*.md`` entry is an ``unsafe_source`` skip.

    The glob matches by name, so a directory (or FIFO, or device node) named
    ``lesson-*.md`` reaches the move loop exactly as a file would. Pins the
    second branch of the regular-file guard, not just the symlink one.
    """
    plan_dir = plan_context.plan_dir_for('nonregular-carry-back')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-07-07-007.md').mkdir()

    result = cmd_delete_plan(Namespace(plan_id='nonregular-carry-back', no_restore_lessons=False))

    assert result['status'] == 'error'
    assert result['error'] == 'lesson_carry_back_incomplete'
    assert result['skipped_lessons'] == [
        {'lesson_id': '2025-07-07-007', 'reason': 'unsafe_source'}
    ]
    assert plan_dir.exists()


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
