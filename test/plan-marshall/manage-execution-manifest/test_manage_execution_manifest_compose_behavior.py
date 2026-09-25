# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_tests_only_runs_module_tests_and_full_phase_6(plan_context):
    """Row 4 — verification change_type with affected files → role:module-tests + full Phase 6.

    Row 4 intersects ``phase_5_candidates`` by ``role: module-tests`` (see
    decision-rules.md § Role-Field Intersection). ``verify:quality-gate`` (role
    ``quality-gate``) and ``verify:coverage`` (role ``coverage``) are dropped;
    ``verify:module-tests`` (role ``module-tests``) is kept.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-tests',
            change_type='verification',
            scope_estimate='single_module',
            affected_files_count=4,
            phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage',
        )
    )
    assert result is not None and result['rule_fired'] == 'tests_only'
    manifest = read_manifest('matrix-tests')
    assert manifest is not None
    assert manifest['phase_5']['verification_steps'] == ['verify:module-tests']
    # Only finalize-step-simplify drops: simplify_inactive still gates on
    # change_type, and 'verification' is not in its code-bearing set.
    # finalize-step-security-audit is KEPT — security_class_inactive reads no
    # change_type at all, and this plan declares 4 affected files, so it has a
    # change surface to audit. This asymmetry is the whole point of the two gates
    # being separate.
    dropped = {'finalize-step-simplify'}
    expected_phase_6 = [s for s in DEFAULT_PHASE_6_STEPS if s not in dropped]
    assert manifest['phase_6']['steps'] == expected_phase_6
