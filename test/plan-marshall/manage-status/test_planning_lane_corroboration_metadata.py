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


def test_metadata_plan_source_wins_over_the_bridge(plan_context):
    """A lesson/recipe-seeded ``plan_source`` is never overwritten by the bridge.

    The bridge fills a null only. When ``status.metadata.plan_source`` is present it
    wins, even if ``request.md`` also carries a ``source_id``.
    """
    plan_dir = plan_context.plan_dir_for('pl-d3b-meta')
    _write_orchestrator_request(plan_dir, '.plan/orchestrator/x/plans/PLAN-01-x.md', 'Implement pkg/a.py.')
    _write_status(plan_dir, metadata={'plan_source': '2026-05-11-08-004'})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-d3b-meta'))

    assert result['signals']['plan_source'] == '2026-05-11-08-004'
