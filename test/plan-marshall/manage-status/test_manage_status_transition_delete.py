#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back.

Split from test_manage_status.py: covers cmd_transition (incl. inline
strict-verify guard for guarded boundaries, and last-phase symmetry with
cmd_archive), cmd_archive (incl. --reason flag), cmd_delete_plan (incl. the main-anchored
lesson carry-back, its five-value ``lesson_carry_back_action`` and that
vocabulary's stated relationship to ``_lessons_query.RESTORE_ACTIONS``, and the
veto that refuses the deletion when a carried lesson did not land), cmd_list (incl.
worktree moved-in plan discovery), cmd_list_orphans, and cmd_mark_step_done
loop-back target validation.
"""


from argparse import Namespace

import pytest
from _manage_status_transition_fixtures import _lifecycle, cmd_delete_plan

from conftest import load_script_module

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
