# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)

# =============================================================================
# Test: security_audit gate — symmetric peer of the other three finalize gates
# =============================================================================


class TestCeremonyFinalizeSecurityAudit:
    """The ``security_audit`` gate forces ``finalize-step-security-audit`` in/out,
    with ``auto`` deferring to the matrix-time ``security_class_inactive``
    pre-filter. The CEREMONY gate is still the symmetric peer of the other three
    (self_review / qgate / simplify); the PRE-FILTER it defers to is not — that one
    shares no helper with ``simplify_inactive`` and reads no ``change_type``.

    ``finalize-step-security-audit`` is a member of ``DEFAULT_PHASE_6_STEPS`` and of
    the security class (frontmatter ``persona: persona-security-expert``). The
    ``security_class_inactive`` pre-filter drops it ONLY when
    ``affected_files_count == 0`` AND the live footprint is empty. The default
    ``_compose_ns`` (``affected_files_count=5``) with the non-empty ``_FOOTPRINT``
    stub therefore keeps the step in the ``auto`` baseline for EVERY change type —
    ``analysis`` and ``verification`` are no longer 'gate fails' fixtures, because
    that is exactly the regression this gate closes. The canonical 'gate fails'
    fixture is now ``affected_files_count=0`` together with ``_stub_footprint([])``.
    """

    def test_auto_defers_to_prefilter_keep_branch(self, plan_context):
        # files>0 → security_class_inactive keeps the step (the gate has no
        # change_type leg); auto is a no-op, so it survives.
        _seed_marshal(finalize_gates={'security_audit': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-secaudit-auto-keep'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['security_audit'] == 'auto'
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))

    def test_auto_keeps_the_step_for_an_excluded_change_type(self, plan_context):
        # ⭐ The regression: change_type='analysis' used to drop the step. It must
        # not — the plan declares 5 affected files, so there is a change surface to
        # audit, and security_class_inactive reads no change_type at all.
        _seed_marshal(finalize_gates={'security_audit': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-secaudit-auto-excluded-type', change_type='analysis'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['security_audit'] == 'auto'
        assert result['security_class_omitted'] == []
        # Kept by the pre-filter, not force-added by the ceremony gate.
        assert result['ceremony_finalize_forced_in'] == []
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))

    def test_auto_defers_to_prefilter_drop_branch(self, plan_context):
        # The only drop condition: no declared affected files AND an empty live
        # footprint → security_class_inactive drops the step; auto does NOT re-add it.
        _seed_marshal(finalize_gates={'security_audit': 'auto'})
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-auto-drop',
                change_type='feature',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['security_audit'] == 'auto'
        assert [r['step'] for r in result['security_class_omitted']] == ['finalize-step-security-audit']
        # auto never force-includes — the pre-filter's drop stands.
        assert 'finalize-step-security-audit' not in result['ceremony_finalize_forced_in']
        assert 'finalize-step-security-audit' not in _bare(_manifest_phase_6_steps(result))

    def test_never_drops_security_audit_step(self, plan_context):
        # Baseline keeps the step (feature + files>0); never must drop it.
        _seed_marshal(finalize_gates={'security_audit': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-secaudit-never'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-security-audit' not in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-security-audit' in result['ceremony_finalize_forced_out']

    def test_never_is_no_op_when_already_dropped_by_prefilter(self, plan_context):
        # No change surface at all → security_class_inactive already dropped the
        # step; never security_audit is then a no-op (no double-drop, no
        # forced_out entry).
        _seed_marshal(finalize_gates={'security_audit': 'off'})
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-never-absent',
                change_type='feature',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-security-audit' not in result['ceremony_finalize_forced_out']
        assert 'finalize-step-security-audit' not in _bare(_manifest_phase_6_steps(result))

    def test_always_readds_security_audit_dropped_by_prefilter(self, plan_context):
        # No change surface at all → security_class_inactive drops the step; always
        # must re-add it regardless, overriding the pre-filter.
        _seed_marshal(finalize_gates={'security_audit': 'minimal'})
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-always-readd',
                change_type='feature',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-security-audit' in result['ceremony_finalize_forced_in']

    def test_always_is_no_op_when_step_already_present(self, plan_context):
        # feature + files>0 → the step survives the matrix; always is a no-op.
        _seed_marshal(finalize_gates={'security_audit': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-secaudit-always-present'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))

    def test_always_inserts_before_plan_mutating_tail(self, plan_context):
        # No change surface drops the step; always re-adds it before the
        # plan-mutating tail.
        _seed_marshal(finalize_gates={'security_audit': 'minimal'})
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-always-order',
                change_type='feature',
                affected_files_count=0,
            )
        )

        assert result is not None
        steps = _manifest_phase_6_steps(result)
        bare_seq = [next(iter(_bare([s]))) for s in steps]
        assert 'finalize-step-security-audit' in bare_seq
        assert 'archive-plan' in bare_seq
        assert bare_seq.index('finalize-step-security-audit') < bare_seq.index('archive-plan')
