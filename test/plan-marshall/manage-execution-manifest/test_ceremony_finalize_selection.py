# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_ceremony_finalize_selection.py: ceremony finalize auto."""

import sys

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _mem,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)

# =============================================================================
# Test: auto (default) — no-op
# =============================================================================


class TestCeremonyFinalizeAuto:
    """All gates default to ``auto`` → the transform is a no-op."""

    def test_absent_ceremony_block_is_no_op(self, plan_context):
        _seed_marshal()  # no finalize gate overrides at all
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-auto-absent'))

        assert result is not None
        assert result['status'] == 'success'
        gates = result['ceremony_finalize_gates']
        assert gates == {
            'functional_review': 'auto',
            'code_review': 'auto',
            'qgate': 'auto',
            'simplify': 'auto',
            'security_audit': 'auto',
        }
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []

    def test_explicit_auto_gates_are_no_op(self, plan_context):
        _seed_marshal(
            finalize_gates={
                'functional_review': 'auto',
                'code_review': 'auto',
                'qgate': 'auto',
                'simplify': 'auto',
                'security_audit': 'auto',
            }
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-auto-explicit'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []
        # On a multi_module feature plan (Row 7 default, no scope gate), the
        # ceremony steps survive the matrix untouched.
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'functional-review' in bare
        assert 'code-review' in bare
        assert 'pre-push-quality-gate' in bare


class TestCeremonyGateRoster:
    """The gate roster, the step map and the owner map name one gate set."""

    def test_the_roster_is_the_step_map_and_the_owner_map_covers_it(self):
        rules = sys.modules[_mem._apply_ceremony_finalize_selection.__module__]
        roster = rules._CEREMONY_FINALIZE_GATES

        assert roster, 'control: the ceremony gate roster must not be empty'
        assert roster == tuple(rules._CEREMONY_FINALIZE_STEP_MAP)
        assert set(rules._CEREMONY_GATE_OWNER_STEP) == set(roster)
