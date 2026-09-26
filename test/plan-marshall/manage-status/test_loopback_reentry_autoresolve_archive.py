# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_loopback_reentry_autoresolve_fixtures import (
    Namespace,
    Path,
    _read_status,
    _seed_plan,
    _stub_metadata,
    _stubbed_invariants,
    cmd_archive,
    cmd_set_phase,
    json,
)

# =============================================================================
# (e) Archive is the SECOND consumption point for the SAME marker
#
# The pair below differs along exactly one axis — whether a re-entry is open at
# archive time — so the contrast is attributable to that and nothing else. The
# control is the load-bearing half: without it the first cell is equally consistent
# with archive writing the outcome record unconditionally, which would assert that a
# loop-back ended without completing on a plan that never looped back at all.
# =============================================================================


def test_archive_consumes_an_open_marker_and_records_it_never_completed(
    plan_context, _stubbed_invariants, _stub_metadata
):
    """A plan archived mid-re-entry: the marker is cleared and the outcome recorded.

    Such a plan never reaches the guarded boundary where ``cmd_transition`` would
    consume the marker, so without this second consumption point the marker rides
    into the permanent archived record still asserting that a loop-back is in flight
    for a plan that has finished.

    Clearing alone would not be enough either — the outcome record is what keeps the
    re-entry's end from being silently dropped: it really did end, and it ended
    WITHOUT completing.
    """
    plan_id = 'loopback-archived-mid-reentry'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})

    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    marker = _read_status(status_path)['metadata'].get('loop_back_reentry')
    assert marker is not None, (
        'Precondition: the re-entry must really be OPEN at archive time, '
        'otherwise every assertion below passes vacuously.'
    )

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', f'archive failed: {result}'

    archived_metadata = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8')).get(
        'metadata', {}
    )

    assert 'loop_back_reentry' not in archived_metadata, (
        f'The permanent record must not carry a still-open loop-back marker; got {archived_metadata!r}.'
    )

    outcome = archived_metadata.get('loop_back_reentry_outcome')
    assert outcome is not None, (
        'Consuming the marker is not sufficient — archive must RECORD that the '
        're-entry ended without completing, or the fact is lost with the marker.'
    )
    assert outcome['outcome'] == 'ended_without_completing', outcome
    assert outcome['from_phase'] == marker['from_phase'], (
        f"The outcome must carry the consumed marker's own phases; got {outcome!r} against marker {marker!r}."
    )
    assert outcome['to_phase'] == marker['to_phase'], outcome
    assert outcome['scheduled_at'] == marker['at'], (
        f"scheduled_at must be the marker's own timestamp, not the consumption time; got {outcome!r}."
    )
    assert outcome['consumed_by'] == 'archive', (
        f'The record must name WHICH consumption point fired, since there are two; got {outcome!r}.'
    )
    assert outcome['consumed_at'], 'The outcome must say when the marker was consumed.'


def test_archive_without_an_open_marker_records_no_outcome(plan_context, _stubbed_invariants, _stub_metadata):
    """Matched control: no marker at archive time ⇒ no outcome key at all.

    This is the half that gives the cell above its meaning. A verb that wrote the
    outcome record unconditionally would pass that assertion while claiming a
    loop-back ended without completing on a plan that never had one.
    """
    plan_id = 'loopback-archived-no-marker'
    status_path = _seed_plan(plan_context, plan_id, {'use_worktree': False})
    assert 'loop_back_reentry' not in _read_status(status_path).get('metadata', {}), (
        "Precondition: this plan must carry NO marker, so the absence asserted below is the verb's own answer."
    )

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', f'archive failed: {result}'

    archived_metadata = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8')).get(
        'metadata', {}
    )
    assert 'loop_back_reentry_outcome' not in archived_metadata, (
        f'A plan that never looped back must carry no re-entry outcome; got {archived_metadata!r}.'
    )
