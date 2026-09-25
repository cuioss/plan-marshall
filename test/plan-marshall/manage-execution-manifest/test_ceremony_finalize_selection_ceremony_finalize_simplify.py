# SPDX-License-Identifier: FSL-1.1-ALv2
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
# Test: simplify gate — symmetric peer of the other three finalize gates
# =============================================================================


class TestCeremonyFinalizeSimplify:
    """The ``simplify`` gate forces ``finalize-step-simplify`` in/out, with
    ``auto`` deferring to the matrix-time ``simplify_inactive`` pre-filter. It is
    the symmetric peer of the other two finalize gates (self_review / qgate).

    ``finalize-step-simplify`` is a member of ``DEFAULT_PHASE_6_STEPS``; the
    ``simplify_inactive`` pre-filter keeps it only when
    ``change_type ∈ {feature, bug_fix, tech_debt, enhancement}`` AND
    ``affected_files > 0``. The default ``_compose_ns``
    (``change_type='feature'``, ``affected_files_count=5``) therefore keeps the
    step in the ``auto`` baseline. ``analysis`` / ``verification`` are the
    still-excluded change types used as the canonical 'gate fails' fixtures.
    """

    def test_auto_defers_to_prefilter_keep_branch(self, plan_context):
        # change_type=feature, files>0 → simplify_inactive keeps the step;
        # auto is a no-op, so it survives.
        _seed_marshal(finalize_gates={'simplify': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-auto-keep'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['simplify'] == 'auto'
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []
        assert 'finalize-step-simplify' in _bare(_manifest_phase_6_steps(result))

    def test_auto_defers_to_prefilter_drop_branch(self, plan_context):
        # change_type=analysis is outside the simplify activation set
        # ({feature, bug_fix, tech_debt, enhancement}) → the simplify_inactive
        # pre-filter drops the step; auto does NOT re-add it. On a multi_module
        # analysis plan (Row 7 default) the rest of phase_6 is retained.
        _seed_marshal(finalize_gates={'simplify': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-auto-drop', change_type='analysis'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['simplify'] == 'auto'
        # auto never force-includes — the pre-filter's drop stands.
        assert 'finalize-step-simplify' not in result['ceremony_finalize_forced_in']
        assert 'finalize-step-simplify' not in _bare(_manifest_phase_6_steps(result))

    def test_never_drops_simplify_step(self, plan_context):
        # Baseline keeps the step (feature + files>0); never must drop it.
        _seed_marshal(finalize_gates={'simplify': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-never'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-simplify' not in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in result['ceremony_finalize_forced_out']

    def test_never_is_no_op_when_already_dropped_by_prefilter(self, plan_context):
        # analysis change_type → simplify_inactive already dropped the step;
        # never simplify is then a no-op (no double-drop, no forced_out entry).
        _seed_marshal(finalize_gates={'simplify': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-never-absent', change_type='analysis'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-simplify' not in result['ceremony_finalize_forced_out']
        assert 'finalize-step-simplify' not in _bare(_manifest_phase_6_steps(result))

    def test_always_readds_simplify_dropped_by_prefilter(self, plan_context):
        # analysis change_type → simplify_inactive drops the step; always
        # must re-add it regardless, overriding the pre-filter.
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-always-readd', change_type='analysis'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-simplify' in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in result['ceremony_finalize_forced_in']

    def test_always_is_no_op_when_step_already_present(self, plan_context):
        # feature + files>0 → the step survives the matrix; always is a no-op.
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-always-present'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert 'finalize-step-simplify' in _bare(_manifest_phase_6_steps(result))

    def test_always_inserts_before_plan_mutating_tail(self, plan_context):
        # analysis drops the step; always re-adds it before the
        # plan-mutating tail.
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-always-order', change_type='analysis'))

        assert result is not None
        steps = _manifest_phase_6_steps(result)
        bare_seq = [next(iter(_bare([s]))) for s in steps]
        assert 'finalize-step-simplify' in bare_seq
        assert 'archive-plan' in bare_seq
        assert bare_seq.index('finalize-step-simplify') < bare_seq.index('archive-plan')
