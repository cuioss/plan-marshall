# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_decision_rules_fixtures import (
    _SECURITY_CLASS,
    _apply_security_class_inactive,
    _restore_footprint_resolver,
    pytest,
)


class TestSecurityClassInactivePreFilter:
    """Direct unit coverage of the ``security_class_inactive`` pre-filter helper."""

    @pytest.mark.parametrize(
        'affected_files_count,live_footprint_count,expect_present,expect_dropped_count',
        [
            # Either change-surface signal being non-empty keeps the step.
            (5, 3, True, 0),
            (5, 0, True, 0),
            (0, 3, True, 0),
            (1, 0, True, 0),
            (0, 1, True, 0),
            # Only the genuine no-change-surface case drops it.
            (0, 0, False, 1),
        ],
    )
    def test_gate_truth_table(
        self,
        affected_files_count,
        live_footprint_count,
        expect_present,
        expect_dropped_count,
    ):
        candidates = ['finalize-step-security-audit', 'push', 'archive-plan']
        kept, dropped = _apply_security_class_inactive(
            candidates, _SECURITY_CLASS, affected_files_count, live_footprint_count
        )
        assert len(dropped) == expect_dropped_count
        assert ('finalize-step-security-audit' in kept) is expect_present
        # Non-target candidates are never disturbed.
        assert 'push' in kept
        assert 'archive-plan' in kept

    @pytest.mark.parametrize('change_type', ['analysis', 'verification', 'feature', 'bug_fix'])
    def test_change_type_is_not_an_input_at_all(self, change_type):
        # The helper's signature carries no change_type parameter — the regression
        # this gate exists to prevent is a security sweep dropped on a semantic
        # outline-time label. Passing a change-shape-bearing candidate set with a
        # non-zero surface must keep the step whatever the plan's change_type is,
        # which the absent parameter makes structurally true.
        assert 'change_type' not in _apply_security_class_inactive.__code__.co_varnames
        kept, dropped = _apply_security_class_inactive(['finalize-step-security-audit'], _SECURITY_CLASS, 4, 0)
        assert kept == ['finalize-step-security-audit']
        assert dropped == []

    def test_drop_record_names_step_and_reason(self):
        kept, dropped = _apply_security_class_inactive(['finalize-step-security-audit', 'push'], _SECURITY_CLASS, 0, 0)
        assert kept == ['push']
        assert dropped == [
            {
                'step': 'finalize-step-security-audit',
                'reason': 'no declared affected files and empty live footprint',
            }
        ]

    def test_population_is_caller_derived_not_a_step_id_literal(self):
        # A second security-class member is dropped by the same call, and a
        # non-member sharing no persona is not — proving the helper reads the
        # supplied population rather than a hardcoded id.
        population = frozenset({'finalize-step-security-audit', 'finalize-step-other-security'})
        candidates = [
            'finalize-step-security-audit',
            'finalize-step-other-security',
            'finalize-step-simplify',
        ]
        kept, dropped = _apply_security_class_inactive(candidates, population, 0, 0)
        assert kept == ['finalize-step-simplify']
        assert {record['step'] for record in dropped} == population

    def test_no_op_when_no_security_class_step_in_candidates(self):
        # No population member is present → nothing to drop even in the
        # zero-change-surface case.
        candidates = ['push', 'archive-plan']
        kept, dropped = _apply_security_class_inactive(candidates, _SECURITY_CLASS, 0, 0)
        assert dropped == []
        assert kept == candidates

    def test_returns_new_list_on_drop_not_mutating_input(self):
        # The drop branch must not mutate the caller's candidate list in place.
        candidates = ['finalize-step-security-audit', 'push']
        kept, dropped = _apply_security_class_inactive(candidates, _SECURITY_CLASS, 0, 0)
        assert len(dropped) == 1
        assert 'finalize-step-security-audit' not in kept
        # Input list is untouched.
        assert candidates == ['finalize-step-security-audit', 'push']
