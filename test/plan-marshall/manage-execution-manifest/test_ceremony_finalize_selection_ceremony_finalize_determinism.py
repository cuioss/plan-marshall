# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _compose_ns,
    _manifest_phase_6_steps,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)

# =============================================================================
# Test: determinism — same inputs → same selection
# =============================================================================


class TestCeremonyFinalizeDeterminism:
    """Re-composing with identical inputs yields an identical ceremony selection."""

    def test_repeated_compose_is_deterministic(self, plan_context):
        _seed_marshal(finalize_gates={'self_review': 'minimal', 'qgate': 'off', 'simplify': 'standard'})
        _stub_footprint(_FOOTPRINT)

        ns1 = _compose_ns(plan_id='ceremony-determinism', scope_estimate='surgical', change_type='bug_fix')
        first = cmd_compose(ns1)
        steps_first = _manifest_phase_6_steps(first)

        ns2 = _compose_ns(plan_id='ceremony-determinism', scope_estimate='surgical', change_type='bug_fix')
        second = cmd_compose(ns2)
        steps_second = _manifest_phase_6_steps(second)

        assert steps_first == steps_second
        assert first['ceremony_finalize_gates'] == second['ceremony_finalize_gates']
        assert first['ceremony_finalize_forced_in'] == second['ceremony_finalize_forced_in']
        assert first['ceremony_finalize_forced_out'] == second['ceremony_finalize_forced_out']
