# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _PREFIXED_PHASE_6,
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_rule_1_early_terminate_analysis_with_prefixed_candidates(plan_context):
    """Rule 1 (early_terminate_analysis) — prefixed candidates: include only lessons/archive (bare)."""
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-1',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
            phase_6_steps=','.join(_PREFIXED_PHASE_6),
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
    manifest = read_manifest('prefix-rule-1')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # Boundary normalization strips `default:` at intake — output is bare.
    assert set(steps) == {'lessons-capture', 'archive-plan'}
    # No `default:`-prefixed entries survive anywhere in the manifest.
    assert not any(s.startswith('default:') for s in steps)
    # Heavy steps that would have leaked through pre-fix are absent.
    for excluded in ('push', 'create-pr', 'automatic-review', 'pre-push-quality-gate', 'branch-cleanup'):
        assert excluded not in steps



def test_rule_2_recipe_with_prefixed_candidates(plan_context):
    """Rule 2 (recipe) — prefixed candidates: review gates RETAINED, legacy ci-wait dropped (bare output)."""
    prefixed_with_review_and_legacy = _PREFIXED_PHASE_6 + (
        'default:sonar-roundtrip',
        'default:ci-wait',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-2',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            phase_6_steps=','.join(prefixed_with_review_and_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'
    manifest = read_manifest('prefix-rule-2')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # No `default:` prefix in output — boundary-normalized at intake.
    assert not any(s.startswith('default:') for s in steps)
    # Review gates RETAINED — never silently suppressed.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    # Non-heavy steps survive (bare).
    assert 'push' in steps
    assert 'create-pr' in steps
    assert 'lessons-capture' in steps



def test_rule_5_surgical_bug_fix_with_prefixed_candidates(plan_context):
    """Rule 5 (surgical_bug_fix) — prefixed candidates: review gates RETAINED, legacy ci-wait dropped (bare output)."""
    prefixed_with_review_and_legacy = _PREFIXED_PHASE_6 + (
        'default:sonar-roundtrip',
        'default:ci-wait',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-5-bug',
            change_type='bug_fix',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_6_steps=','.join(prefixed_with_review_and_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
    manifest = read_manifest('prefix-rule-5-bug')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    assert not any(s.startswith('default:') for s in steps)
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    assert 'lessons-capture' in steps
    assert 'push' in steps



def test_rule_5_surgical_tech_debt_with_prefixed_candidates(plan_context):
    """Rule 5 (surgical_tech_debt) — prefixed candidates: same retention as bug_fix (bare output)."""
    prefixed_with_review_and_legacy = _PREFIXED_PHASE_6 + (
        'default:sonar-roundtrip',
        'default:ci-wait',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-5-tech',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=2,
            # Code-shaped candidate set (role: module-tests present) so we
            # don't fall into docs_only first.
            phase_5_steps='verify:quality-gate,verify:module-tests',
            phase_6_steps=','.join(prefixed_with_review_and_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    manifest = read_manifest('prefix-rule-5-tech')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    assert not any(s.startswith('default:') for s in steps)
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    assert 'push' in steps



def test_rule_6_verification_no_files_with_prefixed_candidates(plan_context):
    """Rule 6 (verification_no_files) — prefixed candidates: include only lessons/archive (bare output)."""
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-6',
            change_type='verification',
            scope_estimate='none',
            affected_files_count=0,
            phase_6_steps=','.join(_PREFIXED_PHASE_6),
        )
    )
    assert result is not None and result['rule_fired'] == 'verification_no_files'
    manifest = read_manifest('prefix-rule-6')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # Boundary normalization strips `default:` at intake — output is bare.
    assert set(steps) == {'lessons-capture', 'archive-plan'}
    assert not any(s.startswith('default:') for s in steps)
    for excluded in ('push', 'create-pr', 'automatic-review', 'pre-push-quality-gate', 'branch-cleanup'):
        assert excluded not in steps
