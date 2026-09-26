# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _phase_6_with_ceremony_steps,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    _write_execution_profile,
    cmd_compose,
)

# =============================================================================
# Test: ceremony pre-filter drop of an operator-selected step surfaces a
# lane_warnings[] entry (second producer on the lane_warnings channel)
#
# The API-Sheriff live case: full posture (operator keeps everything), a ceremony
# pre-filter fires, and the drop was previously SILENT — the lane said "keep", yet
# the step vanished with only the omission field as evidence. The composer now
# appends a {step, warning} entry naming the ceremony pre-filter — not the lane —
# as the remover. The per-pre-filter omission fields are unchanged in meaning:
# ``simplify_omitted`` is a boolean, ``security_class_omitted`` a {step, reason} list.
# =============================================================================


class TestCeremonyPrefilterLaneWarnings:
    """A fired ceremony pre-filter over an operator-selected step warns via lane_warnings."""

    def test_warning_emitted_when_prefilter_drops_posture_included_step(self, plan_context):
        # Full posture keeps everything, so both ceremony steps are
        # operator-selected. Zero affected files AND an empty footprint is the one
        # shape that fires BOTH pre-filters at once.
        plan_id = 'ceremony-prefilter-warning'
        _seed_marshal()  # all ceremony gates default to auto
        _stub_footprint([])
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(_compose_ns(plan_id=plan_id, change_type='analysis', affected_files_count=0))

        assert result is not None
        assert result['status'] == 'success'
        # Each pre-filter's own omission signal, unchanged in meaning.
        assert result['simplify_omitted'] is True
        assert [r['step'] for r in result['security_class_omitted']] == ['finalize-step-security-audit']
        # The silent-drop scenario now yields a non-empty lane_warnings naming
        # the ceremony pre-filter as the remover for BOTH dropped steps.
        warned = {w['step']: w['warning'] for w in result['lane_warnings']}
        assert 'finalize-step-simplify' in warned
        assert 'finalize-step-security-audit' in warned
        assert 'ceremony pre-filter' in warned['finalize-step-simplify']
        assert 'ceremony pre-filter' in warned['finalize-step-security-audit']
        # Each warning must name the gate that ACTUALLY fired. The two pre-filters
        # no longer share a condition, so a shared message would misreport the
        # security-class drop as change_type-gated. A substring check on the common
        # prefix alone cannot catch that — assert the discriminating clause, and
        # assert the wrong one is absent.
        assert 'change_type/affected_files gate' in warned['finalize-step-simplify']
        assert 'zero-change-surface gate' not in warned['finalize-step-simplify']
        assert 'zero-change-surface gate' in warned['finalize-step-security-audit']
        assert 'change_type' not in warned['finalize-step-security-audit']
        # The steps are genuinely gone from the composed list.
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' not in bare
        assert 'finalize-step-security-audit' not in bare

    def test_no_warning_when_step_never_a_candidate(self, plan_context):
        # The ceremony steps are absent from the candidate set → the pre-filter
        # never fires (a no-op over an absent step) → no warning entry.
        plan_id = 'ceremony-prefilter-no-candidate'
        candidates = [
            s
            for s in _phase_6_with_ceremony_steps().split(',')
            if s not in ('finalize-step-simplify', 'finalize-step-security-audit')
        ]
        # finalize_gates={} still seeds the authoritative steps map from the
        # candidate list (no gate overrides).
        _seed_marshal(finalize_gates={}, candidates=candidates)
        _stub_footprint([])
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='analysis',
                affected_files_count=0,
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        # Pre-filters are no-ops over an absent step.
        assert result['simplify_omitted'] is False
        assert result['security_class_omitted'] == []
        warned_steps = {w['step'] for w in result['lane_warnings']}
        assert 'finalize-step-simplify' not in warned_steps
        assert 'finalize-step-security-audit' not in warned_steps

    def test_no_warning_when_always_gate_readds_the_step(self, plan_context):
        # The simplify gate `always` (lane: minimal) re-adds the step the
        # pre-filter dropped — the step IS present, so no ceremony-pre-filter
        # warning fires for it. The security step is kept by its own pre-filter
        # (the non-empty footprint is a change surface), so it does not warn either.
        plan_id = 'ceremony-prefilter-always-readd'
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(_compose_ns(plan_id=plan_id, change_type='analysis'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in bare
        assert 'finalize-step-security-audit' in bare
        warned = {w['step']: w['warning'] for w in result['lane_warnings']}
        assert 'finalize-step-simplify' not in warned
        assert 'finalize-step-security-audit' not in warned
