# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import (
    _ns_route,
    _write_marshal,
    _write_orchestrator_request,
    _write_references,
    _write_status,
    cmd_planning_lane_route,
)

# =============================================================================
# D0/D3(b) — the orchestrator-spec plan_source bridge (end-to-end via the router)
# =============================================================================


def test_d3b_orchestrator_spec_resolves_plan_source_nonnull(plan_context):
    """(b) An orchestrator-spec-sourced request resolves ``plan_source`` non-null.

    ``status.metadata`` carries NO ``plan_source`` (the file-pointer branch never
    seeds it). The router bridges the retained ``request.md`` ``source_id`` pointer,
    so ``plan_source`` resolves to that pointer instead of null — and therefore
    counts as resolved in the confidence split.
    """
    plan_dir = plan_context.plan_dir_for('pl-d3b')
    spec_id = '.plan/orchestrator/some-slug/plans/PLAN-07-do-a-thing.md'
    _write_orchestrator_request(plan_dir, spec_id, 'Implement the four targets in pkg/a.py.')
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-d3b'))

    assert result['signals']['plan_source'] == spec_id
    assert 'plan_source' not in result['confidence']['null_signals']
