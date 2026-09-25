# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_manage_status_transition_fixtures import Namespace, cmd_delete_plan


def test_unresolvable_store_over_an_empty_plan_dir_is_still_the_benign_zero(plan_context, monkeypatch):
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

    result = cmd_delete_plan(Namespace(plan_id='unresolved-store-empty-plan', no_restore_lessons=False))

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
