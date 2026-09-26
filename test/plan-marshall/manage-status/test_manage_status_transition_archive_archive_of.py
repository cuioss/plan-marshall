# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_manage_status_transition_archive_fixtures import (
    Namespace,
    Path,
    _seed_early_archive_plan,
    _seed_finalize_phase_plan,
    _seed_two_in_progress_plan,
    _stub_finding_queries,
    cmd_archive,
    cmd_transition,
    json,
)


def test_archive_of_an_early_abandoned_plan_leaves_pending_phases_pending(plan_context):
    """The matched other half: a phase that never started must NOT be closed.

    The retired ``!= done`` predicate also failed in this direction — a ``pending``
    phase satisfied it, so archive wrote ``done`` onto a phase that never ran,
    fabricating a fresh false record instead of closing a real one.

    ``current_phase`` must still reach ``complete`` here, because the gate is "no
    phase remains in_progress" rather than "every phase is done" — the latter could
    never hold for a plan whose pending tail must stay pending, which is why such a
    plan used to archive frozen at its last phase and never reached the
    post-finalize sentinel its dormant consumers match on.
    """
    plan_id = 'archive-early-abandoned'
    _seed_early_archive_plan(plan_id)

    live_status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    pending_before = [p['name'] for p in live_status['phases'] if p['status'] == 'pending']
    assert pending_before == ['3-outline', '4-plan', '5-execute', '6-finalize'], (
        f'Seed precondition: the plan must carry a real pending tail, otherwise the '
        f'assertion below passes vacuously. Got {pending_before!r}.'
    )

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', f'archive failed: {result}'

    archived_status = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
    by_name = {p['name']: p['status'] for p in archived_status['phases']}

    observed_tail = {name: by_name[name] for name in pending_before}
    assert all(status == 'pending' for status in observed_tail.values()), (
        f'Archive must leave every pending phase pending — writing done onto a phase '
        f'that never started fabricates a record of work that never happened. '
        f'Expected {pending_before!r} all still pending, got {observed_tail!r}.'
    )
    assert by_name['2-refine'] == 'done', (
        f'2-refine really was in_progress, so it is the one phase archive must close here; got {by_name["2-refine"]!r}.'
    )
    assert by_name['1-init'] == 'done', f'An already-done phase must stay done; got {by_name["1-init"]!r}.'
    assert archived_status['current_phase'] == 'complete', (
        f'The completion gate is "no phase remains in_progress", so a plan abandoned '
        f'mid-lifecycle must still reach the post-finalize sentinel; got '
        f'{archived_status["current_phase"]!r}.'
    )


def test_archive_of_the_same_two_open_state_proceeds_when_a_reason_is_supplied(plan_context, monkeypatch):
    """POSITIVE control: the identical state with --reason is a deliberate abandonment.

    Differs from the cell above along exactly one axis, so the refusal there is
    attributable to the gate rather than to anything about the two-open seed itself.
    """
    _stub_finding_queries(monkeypatch, {'sonar-issue': 2})
    plan_id = 'finalize-open-not-current-with-reason'
    _seed_two_in_progress_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence'))

    assert result['status'] == 'success', (
        f'A --reason archive is a deliberate abandonment and must not be blocked by pending findings: {result!r}.'
    )
    assert 'archived_to' in result, result


def test_archive_of_already_complete_plan_not_blocked_by_pending_finding(plan_context, monkeypatch):
    """The cleanup pass archives already-`complete` plans (no --reason). A stale
    pending record on such a plan must NOT wedge cleanup — the completion gate
    fires only while the plan is actively in 6-finalize, not after it completed.
    This is exactly the pre-D3 residue (a permanently-pending qgate record) whose
    cleanup a broad gate would have blocked."""
    _stub_finding_queries(monkeypatch, {})  # clean, so the plan can complete
    plan_id = 'finalize-cleanup-complete'
    _seed_finalize_phase_plan(plan_id)
    # Complete it normally (clean) → current_phase becomes 'complete'.
    done = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))
    assert done['status'] == 'success'

    # A stale pending actionable record now appears (the pre-D3 residue).
    _stub_finding_queries(monkeypatch, {'build-error': 1})

    # The cleanup archive (no --reason) of the already-complete plan must proceed.
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', (
        'A cleanup archive of an already-complete plan must not be blocked by a '
        'stale pending finding — the completion gate fires only while in 6-finalize.'
    )
    assert 'archived_to' in result
