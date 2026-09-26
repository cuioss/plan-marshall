# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    _write_execution_profile,
    cmd_compose,
)

# =============================================================================
# Test: enhancement gate activation — enhancement is code-touching by definition
# =============================================================================


class TestEnhancementGateActivation:
    """``enhancement`` is a member of ``simplify_inactive``'s code-touching
    activation set ``{feature, bug_fix, tech_debt, enhancement}``: with
    ``affected_files > 0`` that pre-filter KEEPS ``finalize-step-simplify``, and
    ``security_class_inactive`` independently keeps
    ``finalize-step-security-audit``, so a full-posture enhancement plan composes
    with both present — via the pre-filter keep branch, not a force-add.

    The zero-files case is where the two gates diverge, and that divergence is the
    out-of-scope-sibling proof: ``simplify_inactive`` still drops on
    ``affected_files_count == 0`` alone, while ``security_class_inactive`` needs an
    empty live footprint as well."""

    def test_full_posture_enhancement_plan_keeps_both_ceremony_steps(self, plan_context):
        plan_id = 'ceremony-enhancement-activation'
        _seed_marshal()  # all ceremony gates default to auto
        _stub_footprint(_FOOTPRINT)
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(_compose_ns(plan_id=plan_id, change_type='enhancement'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in bare
        assert 'finalize-step-security-audit' in bare
        # auto gates deferred — nothing was force-added; the pre-filters kept both.
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []

    def test_enhancement_with_zero_files_drops_simplify_but_keeps_security_audit(self, plan_context):
        # simplify_inactive's second leg is unchanged: affected_files_count == 0
        # drops finalize-step-simplify regardless of the code-touching change type.
        # security_class_inactive does NOT drop on that leg alone — the live
        # footprint is non-empty, so there is still a change surface to audit.
        _seed_marshal()
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-enhancement-zero-files',
                change_type='enhancement',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['simplify_omitted'] is True
        assert result['security_class_omitted'] == []
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' not in bare
        assert 'finalize-step-security-audit' in bare

    def test_enhancement_with_zero_files_and_empty_footprint_drops_both(self, plan_context):
        # Both legs of security_class_inactive fail → the security step drops too.
        # This is the only shape that removes it.
        _seed_marshal()
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-enhancement-zero-files-empty-footprint',
                change_type='enhancement',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['simplify_omitted'] is True
        assert [r['step'] for r in result['security_class_omitted']] == ['finalize-step-security-audit']
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' not in bare
        assert 'finalize-step-security-audit' not in bare
