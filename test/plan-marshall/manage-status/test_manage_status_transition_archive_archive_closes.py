# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_manage_status_transition_archive_fixtures import (
    Namespace,
    Path,
    _seed_two_in_progress_plan,
    cmd_archive,
    json,
)

# =============================================================================
# D2 — Archive closes EVERY in-progress phase and leaves pending phases pending.
#
# The retired closure took the first phase whose status was merely ``!= done`` and
# closed that one alone, which failed in BOTH directions at once. The two controls
# below are matched halves that pin the closure set to ``in_progress`` exactly: the
# first fails if archive closes too FEW phases, the second if it closes too MANY.
# Each seed's precondition is asserted before the act, so neither assertion can pass
# vacuously against a state that never held the property under test.
# =============================================================================


def test_archive_closes_every_in_progress_phase_not_just_one(plan_context):
    """NEGATIVE control: a plan holding TWO open phases has BOTH closed.

    This is the defect itself. With the retired single-slot closure the second
    ``in_progress`` phase stayed recorded as running in the permanent archived
    record — so the archive asserted a phase was still in flight for a plan that
    had finished. Fails against the pre-fix code; passes only once the closure
    loops over every open phase.
    """
    plan_id = 'archive-two-in-progress'
    _seed_two_in_progress_plan(plan_id)

    live_status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    open_before = [p['name'] for p in live_status['phases'] if p['status'] == 'in_progress']
    assert open_before == ['5-execute', '6-finalize'], (
        f'Seed precondition: the plan must really hold TWO open phases before '
        f'archive, otherwise the assertion below passes vacuously. Got {open_before!r}.'
    )

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', f'archive failed: {result}'

    archived_status = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
    still_open = [p['name'] for p in archived_status['phases'] if p['status'] == 'in_progress']
    assert still_open == [], (
        f'Archive left {still_open!r} recorded in_progress — the permanent record '
        f'now says a phase is still running for a finished plan.'
    )
    by_name = {p['name']: p['status'] for p in archived_status['phases']}
    for name in open_before:
        assert by_name[name] == 'done', (
            f'{name} was open before archive and must be closed after; got {by_name[name]!r}.'
        )
    assert archived_status['current_phase'] == 'complete', (
        f'With no phase left in_progress the completion gate must fire; got {archived_status["current_phase"]!r}.'
    )
