# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _SCOPE_GATE_PHASE_6,
    _compose_ns,
    _mem,
    _write_drop_review_marshal,
    cmd_compose,
    read_manifest,
)


class TestScopeGatedFinalizePreFilter:
    """Scope-gated phase-6 subtraction pre-filter (scope_gated_finalize)."""

    def test_surgical_drops_three_non_guarded_steps_retains_automated_review(self, plan_context):
        """surgical scope drops plan-retrospective, pre-submission-self-review,
        and plugin-doctor — but RETAINS automatic-review by default."""
        # Use change_type=feature so the surgical row matrix does not pre-empt
        # the candidate list; the scope gate runs before the matrix regardless.
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-surgical',
                change_type='feature',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-surgical')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Three non-guarded steps dropped.
        assert 'plan-marshall:plan-retrospective' not in steps
        assert 'pre-submission-self-review' not in steps
        assert 'project:finalize-step-plugin-doctor' not in steps
        # automatic-review RETAINED by default (no override).
        assert 'automatic-review' in steps
        # Baseline steps survive.
        assert 'push' in steps
        assert 'lessons-capture' in steps

    def test_surgical_drops_generic_default_self_review_form(self, plan_context):
        """A consuming project listing the GENERIC default:pre-submission-self-review
        step (normalized to bare pre-submission-self-review at intake) must also be
        dropped on surgical scope — the surgical drop-set covers the normalized
        bare form, not only the meta-project project: wrapper. Regression for the
        drop-set that omitted the bare form after the canonical was generalized."""
        candidates = _SCOPE_GATE_PHASE_6
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-surgical-generic-selfreview',
                change_type='feature',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(candidates),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-surgical-generic-selfreview')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # The normalized bare form must be dropped by the surgical scope gate.
        assert 'pre-submission-self-review' not in steps
        assert 'default:pre-submission-self-review' not in steps
        # Baseline steps survive.
        assert 'push' in steps

    def test_scope_gated_automatic_review_survives_without_drop_hatch(self, plan_context):
        """automatic-review survives a scope-gated compose — the drop hatch is gone.

        ``drop_review_on_scope_gate`` was removed: declared-lane immunity, not an
        ad-hoc project-wide opt-in hatch, is what governs which scope-gated steps
        are retained. The legacy knob is written here deliberately to prove it is
        now INERT — no reader consumes it, so automatic-review is retained exactly
        as it is without the knob.
        """
        _write_drop_review_marshal(plan_context.fixture_dir, override=True)
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-surgical-override',
                change_type='feature',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-surgical-override')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # automatic-review RETAINED — the removed knob no longer drops it.
        assert 'automatic-review' in steps
        # Three non-guarded steps still dropped.
        assert 'plan-marshall:plan-retrospective' not in steps
        assert 'pre-submission-self-review' not in steps
        assert 'project:finalize-step-plugin-doctor' not in steps

    def test_drop_review_inert_on_non_scope_gated(self, plan_context):
        """drop_review_on_scope_gate=true is INERT on a non-scope-gated plan:
        automatic-review is retained on multi_module scope even with the
        override set, so flipping the project-wide knob cannot silently disable
        bot review on a large plan."""
        _write_drop_review_marshal(plan_context.fixture_dir, override=True)
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-multi-override',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=10,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-multi-override')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Override is inert at multi_module scope — automatic-review RETAINED.
        assert 'automatic-review' in steps
        # No scope subtraction at multi_module — the scope-gated steps survive.
        assert 'plan-marshall:plan-retrospective' in steps
        assert 'project:finalize-step-plugin-doctor' in steps
        # pre-submission-self-review SURVIVES: no footprint-gated pre-filter drops
        # it (the vacuous pre_submission_self_review_inactive predicate was removed
        # outright), and the inert multi_module scope gate makes no subtraction.
        assert 'pre-submission-self-review' in steps

    def test_single_module_drops_only_plan_retrospective(self, plan_context):
        """single_module SCOPE gate drops only plan-retrospective; plugin-doctor
        and automatic-review are retained by the scope gate.

        pre-submission-self-review SURVIVES: no footprint-gated pre-filter drops it
        (the vacuous pre_submission_self_review_inactive predicate was removed
        outright), and the single_module scope gate does not drop it."""
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-single-module',
                change_type='feature',
                scope_estimate='single_module',
                affected_files_count=4,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-single-module')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Only plan-retrospective is dropped by the single_module scope gate.
        assert 'plan-marshall:plan-retrospective' not in steps
        # pre-submission-self-review survives — the pre-filter no longer drops on an
        # empty compose-time footprint, and the single_module scope gate keeps it.
        assert 'pre-submission-self-review' in steps
        # plugin-doctor + automatic-review survive the single_module scope gate.
        assert 'project:finalize-step-plugin-doctor' in steps
        assert 'automatic-review' in steps

    def test_multi_module_retains_full_set(self, plan_context):
        """multi_module SCOPE gate makes no subtraction — the scope-gated steps
        and automatic-review are retained by the scope gate.

        pre-submission-self-review SURVIVES too: no footprint-gated pre-filter drops
        it (the vacuous pre-filter that once claimed to was removed outright), and
        the inert multi_module scope gate makes no subtraction."""
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-multi-module',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=10,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-multi-module')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # The scope gate makes no subtraction at multi_module scope — the
        # scope-gated steps and automatic-review are RETAINED by the scope gate.
        assert 'plan-marshall:plan-retrospective' in steps
        assert 'project:finalize-step-plugin-doctor' in steps
        assert 'automatic-review' in steps
        # pre-submission-self-review survives — no footprint-gated pre-filter drops
        # it, and the multi_module scope gate is inert.
        assert 'pre-submission-self-review' in steps

    def test_surgical_emits_one_decision_log_per_subtraction(self, plan_context):
        """surgical scope emits one decision-log line per SCOPE-GATE-dropped step.

        No footprint-gated pre-filter removes pre-submission-self-review, so it
        reaches the surgical scope gate and is subtracted there alongside the two
        other non-guarded candidates (plan-retrospective + plugin-doctor) — three
        scope-gate subtractions in total."""
        captured: list[tuple[str, str]] = []
        original = _mem._emit_decision_log

        def _capture(plan_id: str, message: str) -> None:
            captured.append((plan_id, message))

        _mem._emit_decision_log = _capture
        try:
            cmd_compose(
                _compose_ns(
                    plan_id='scope-surgical-log',
                    change_type='feature',
                    scope_estimate='surgical',
                    affected_files_count=2,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                    phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
                )
            )
        finally:
            _mem._emit_decision_log = original

        subtraction_entries = [(pid, msg) for pid, msg in captured if 'scope_gated_finalize subtraction' in msg]
        # All three non-guarded steps (plan-retrospective + plugin-doctor +
        # pre-submission-self-review) reach the surgical scope gate and are dropped
        # there → three decision-log lines. pre-submission-self-review now survives
        # the footprint pre-filter, so it too emits a scope_gated subtraction line.
        assert len(subtraction_entries) == 3
        for pid, msg in subtraction_entries:
            assert pid == 'scope-surgical-log'
            assert 'scope_estimate=surgical' in msg

    def test_result_carries_scope_gated_observability_fields(self, plan_context):
        """The compose result exposes scope_gated_finalize_dropped and
        scope_gated_finalize_immune for observability."""
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-observability',
                change_type='feature',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        # No candidate declares an explicit non-standard per-element lane override, so
        # nothing is immune to the surgical scope gate.
        assert result['scope_gated_finalize_immune'] == []
        dropped = result['scope_gated_finalize_dropped']
        assert 'plan-marshall:plan-retrospective' in dropped
        assert 'project:finalize-step-plugin-doctor' in dropped
        # pre-submission-self-review now survives the footprint pre-filter and
        # reaches the surgical scope gate, which drops it — so it IS reported in the
        # scope-gate's dropped set alongside the other two non-guarded steps.
        assert 'pre-submission-self-review' in dropped
        # automatic-review NOT in the dropped set without the override.
        assert 'automatic-review' not in dropped
