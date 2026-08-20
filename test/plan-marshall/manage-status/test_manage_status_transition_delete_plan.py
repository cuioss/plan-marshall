#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back."""


from argparse import Namespace

import pytest
from _manage_status_transition_fixtures import _lifecycle, cmd_delete_plan

# =============================================================================
# Test: Delete Plan
# =============================================================================


def test_delete_plan_success(plan_context):
    """Test deleting an existing plan directory."""
    plan_dir = plan_context.plan_dir_for('delete-test')
    # Create some files in the plan
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'references.json').write_text('{"branch": "main"}')
    (plan_dir / 'tasks').mkdir()
    (plan_dir / 'tasks' / 'TASK-001.toon').write_text('title: Test')

    result = cmd_delete_plan(Namespace(plan_id='delete-test'))
    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['plan_id'] == 'delete-test'
    assert result['files_removed'] == 3  # request.md, references.json, ``TASK-001.toon``
    # Verify directory was deleted
    assert not plan_dir.exists()


def test_delete_plan_not_found(plan_context):
    """Test deleting a plan that doesn't exist."""
    result = cmd_delete_plan(Namespace(plan_id='nonexistent-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'


def test_delete_plan_invalid_id(plan_context):
    """Test delete-plan rejects invalid plan IDs (sys.exit(1) from require_valid_plan_id)."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_delete_plan(Namespace(plan_id='Invalid_Plan'))
    assert exc_info.value.code == 0


def test_delete_plan_auto_restores_lesson(plan_context):
    """delete-plan moves a lesson-{id}.md back to lessons-learned/ before deletion."""
    plan_dir = plan_context.plan_dir_for('lesson-2025-01-01-001')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-01-01-001.md').write_text(
        'id=2025-01-01-001\ncomponent=foo\ncategory=bug\ncreated=2025-01-01\n\n# Lesson\n\nBody.\n'
    )

    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    # Pre-emptively confirm the destination does not exist
    if lessons_dir.exists():
        (lessons_dir / '2025-01-01-001.md').unlink(missing_ok=True)

    result = cmd_delete_plan(Namespace(plan_id='lesson-2025-01-01-001', no_restore_lessons=False))

    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_carry_back_action'] == 'restored'
    assert result['lesson_restored'] is True
    assert result['restored_lesson_ids'] == ['2025-01-01-001']
    assert result['skipped_lessons'] == []
    # The payload names the substrate the lesson was restored INTO, so a
    # worktree-pinned run cannot silently report success against a store the
    # caller did not expect.
    assert result['lesson_store_resolution'] in ('main_anchored', 'override')
    assert result['lessons_dir'].endswith('lessons-learned')

    # Plan dir was deleted
    assert not plan_dir.exists()
    # Lesson file lives in lessons-learned/ again
    restored = plan_context.fixture_dir / 'lessons-learned' / '2025-01-01-001.md'
    assert restored.exists()
    assert '# Lesson' in restored.read_text()


def test_delete_plan_no_lesson_file_reports_the_benign_zero(plan_context):
    """A plan dir carrying no lesson file reports the SCANNED zero.

    ``lesson_carry_back_action: no_lesson_file`` says the directory was looked
    at and held nothing — distinct from ``plan_dir_unresolved``, which says the
    carry-back never looked. The count fields ride every branch unconditionally,
    so a consumer never has to test for their presence.
    """
    plan_dir = plan_context.plan_dir_for('delete-no-lesson')
    (plan_dir / 'request.md').write_text('# Request')

    result = cmd_delete_plan(Namespace(plan_id='delete-no-lesson', no_restore_lessons=False))

    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_carry_back_action'] == 'no_lesson_file'
    assert result['lesson_restored'] is False
    assert result['restored_lesson_ids'] == []
    assert result['skipped_lessons'] == []
    assert not plan_dir.exists()


def test_delete_plan_no_restore_lessons_flag_skips_restoration(plan_context):
    """--no-restore-lessons opts out of the carry-back, and therefore its veto."""
    plan_dir = plan_context.plan_dir_for('lesson-2025-01-01-002')
    (plan_dir / 'lesson-2025-01-01-002.md').write_text(
        'id=2025-01-01-002\ncomponent=foo\ncategory=bug\ncreated=2025-01-01\n\n# Lesson\n\nBody.\n'
    )

    result = cmd_delete_plan(Namespace(plan_id='lesson-2025-01-01-002', no_restore_lessons=True))

    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_restored'] is False
    # The lesson file was discarded along with the plan dir
    assert not plan_dir.exists()
    assert not (plan_context.fixture_dir / 'lessons-learned' / '2025-01-01-002.md').exists()


def test_delete_plan_no_restore_lessons_does_not_claim_the_benign_zero(plan_context):
    """The opt-out path may claim neither a scan nor a resolution it never did.

    ``no_lesson_file`` is defined as "the plan directory was SCANNED and carried
    none — the benign zero", and ``main_anchored`` asserts a resolution
    performed. This branch scans nothing and never calls
    ``resolve_lesson_store``, yet it is the ONE branch that can silently
    discard a carried lesson. Reporting the verified-benign zero for it leaves
    an auditor unable to tell "deleted a plan that verifiably carried no
    lesson" from "deleted a plan whose lessons went unexamined" — the same
    could-not-look-reports-benign collapse, in the opt-out path of its own fix.

    The lesson file below is deliberately present: the payload must not read as
    a clean scan while the carry-back is discarding a real lesson.
    """
    import _lessons_io

    plan_dir = plan_context.plan_dir_for('optout-2025-05-05-005')
    (plan_dir / 'lesson-2025-05-05-005.md').write_text(
        'id=2025-05-05-005\ncomponent=foo\ncategory=bug\ncreated=2025-05-05\n\n# Lesson\n\nBody.\n'
    )

    result = cmd_delete_plan(
        Namespace(plan_id='optout-2025-05-05-005', no_restore_lessons=True)
    )

    assert result['status'] == 'success'
    assert result['lesson_carry_back_action'] == 'not_attempted'
    assert result['lesson_carry_back_action'] != 'no_lesson_file'
    assert result['lesson_carry_back_action'] in _lifecycle.CARRY_BACK_ACTIONS
    # No resolution was performed, so none may be reported.
    assert result['lesson_store_resolution'] == 'unresolved'
    assert result['lesson_store_resolution'] in _lessons_io.STORE_RESOLUTIONS
    assert result['lessons_dir'] == ''
    assert result['restored_lesson_ids'] == []


def test_delete_plan_restores_all_lesson_files(plan_context):
    """delete-plan restores every lesson-*.md file in the plan dir (multi-lesson plans)."""
    plan_dir = plan_context.plan_dir_for('consolidate-multi')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-02-01-001.md').write_text(
        'id=2025-02-01-001\ncomponent=foo\ncategory=bug\ncreated=2025-02-01\n\n# One\n'
    )
    (plan_dir / 'lesson-2025-02-01-002.md').write_text(
        'id=2025-02-01-002\ncomponent=bar\ncategory=bug\ncreated=2025-02-01\n\n# Two\n'
    )

    result = cmd_delete_plan(Namespace(plan_id='consolidate-multi', no_restore_lessons=False))

    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_restored'] is True
    assert result['restored_lesson_ids'] == ['2025-02-01-001', '2025-02-01-002']

    # Both lesson files exist in lessons-learned/
    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    assert (lessons_dir / '2025-02-01-001.md').exists()
    assert (lessons_dir / '2025-02-01-002.md').exists()
    assert not plan_dir.exists()


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
