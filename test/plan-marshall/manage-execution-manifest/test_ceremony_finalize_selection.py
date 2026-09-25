# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_ceremony_finalize_selection.py: ceremony finalize auto."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
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
            'self_review': 'auto',
            'qgate': 'auto',
            'simplify': 'auto',
            'security_audit': 'auto',
        }
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []

    def test_explicit_auto_gates_are_no_op(self, plan_context):
        _seed_marshal(
            finalize_gates={
                'self_review': 'auto',
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
        # ceremony steps survive the matrix untouched. The default:-prefixed
        # candidate survives and is normalized to its bare
        # pre-submission-self-review form.
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'pre-submission-self-review' in bare
        assert 'pre-push-quality-gate' in bare
