# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_planning_lane_corroboration_fixtures import (
    _ns_route,
    _write_marshal,
    _write_plaintext_request,
    _write_references,
    _write_status,
    cmd_planning_lane_route,
)


def test_pathless_single_module_band_does_not_suppress_s7(plan_context):
    """A ``single_module`` band that counted NO path cannot contradict the author.

    The body carries a ``manage-*`` notation (so S5 reads it as concrete and S7 stays
    the sole fired signal) but no ``dir/name.ext`` path at all, so the band table
    falls through to ``pathless_non_empty_body`` — ``single_module`` by default,
    measured from nothing. The plain-text request shape is what makes that reachable:
    the orchestrator-spec header carries a path-shaped ``source_id`` the whole-body
    read would count. The warning therefore keeps the lane: ``deep``, with an EMPTY
    suppressed set.
    """
    plan_dir = plan_context.plan_dir_for('pl-pathless')
    _write_plaintext_request(
        plan_dir,
        'Rework the manage-status router. This is foundation work the rest builds on.',
    )
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-pathless'))

    assert result['scope_provenance']['band_rule'] == 'pathless_non_empty_body'
    assert result['signals']['risk_prose'] is True
    assert result['planning_lane'] == 'deep'
    assert result['fired_signals'] == ['S7:risk_prose']
    assert result['suppressed_signals'] == []
