# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_planning_lane_corroboration_fixtures import (
    _ns_route,
    _write_marshal,
    _write_plaintext_request,
    _write_references,
    _write_status,
    cmd_planning_lane_route,
)


def test_plaintext_description_does_not_resolve_orchestrator_provenance(plan_context):
    """A plain-text ``description`` (no ``source_id``) stays free-form — plan_source null.

    The bridge is scoped to the file-pointer shape; a plain-text description is
    genuinely free-form and must keep a null ``plan_source`` so S1 continues to
    treat it as such.
    """
    plan_dir = plan_context.plan_dir_for('pl-d3b-plain')
    _write_plaintext_request(plan_dir, 'Make the thing better somehow.')
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate='single_module')
    _write_marshal(plan_context.fixture_dir)

    result = cmd_planning_lane_route(_ns_route('pl-d3b-plain'))

    assert result['signals']['plan_source'] is None
    assert 'plan_source' in result['confidence']['null_signals']
