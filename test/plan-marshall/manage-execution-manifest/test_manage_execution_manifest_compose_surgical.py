# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _PREFIXED_PHASE_6,
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_surgical_bug_fix_retains_review_gates(plan_context):
    """Row 5 — surgical+bug_fix: review gates RETAINED, legacy ci-wait dropped defensively.

    Review gates are NEVER silently suppressed — surgical bug_fix is
    exactly the case where the bots' job is to catch what humans miss
    on a one-line fix. Only the legacy 'ci-wait' step ID is defensively
    narrowed out.
    """
    candidates_with_legacy = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-bug',
            change_type='bug_fix',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_6_steps=','.join(candidates_with_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
    manifest = read_manifest('matrix-bug')
    assert manifest is not None
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in manifest['phase_6']['steps']
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in manifest['phase_6']['steps']
    assert 'lessons-capture' in manifest['phase_6']['steps']


def test_surgical_tech_debt_retains_review_gates(plan_context):
    """Row 5 — surgical+tech_debt: review gates RETAINED, legacy ci-wait dropped defensively.

    Mirror of surgical_bug_fix — same retention contract, distinct rule
    key. Review gates are never silently suppressed.
    """
    candidates_with_legacy = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-tech',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=2,
            # Need code-shaped candidate set (role: module-tests present) so
            # we don't fall into the docs_only row first. verify:module-tests
            # derives role: module-tests from its canonical segment.
            phase_5_steps='verify:quality-gate,verify:module-tests',
            phase_6_steps=','.join(candidates_with_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    manifest = read_manifest('matrix-tech')
    assert manifest is not None
    assert 'push' in manifest['phase_6']['steps']
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in manifest['phase_6']['steps']
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in manifest['phase_6']['steps']


def test_surgical_tech_debt_with_prefixed_candidates(plan_context):
    """Scope row — prefixed candidates: review gates RETAINED, legacy ci-wait dropped (bare output)."""
    prefixed_with_review_and_legacy = _PREFIXED_PHASE_6 + (
        'default:sonar-roundtrip',
        'default:ci-wait',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-3',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=3,
            # docs-shaped candidate set: only quality-gate, no module-tests/coverage.
            phase_5_steps='quality-gate',
            phase_6_steps=','.join(prefixed_with_review_and_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    manifest = read_manifest('prefix-rule-3')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    assert not any(s.startswith('default:') for s in steps)
    # Review gates RETAINED.
    for retained in ('sonar-roundtrip', 'automatic-review'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    # Non-review steps survive (bare).
    assert 'push' in steps
    assert 'lessons-capture' in steps


def test_surgical_enhancement_with_code_candidates_falls_to_default(plan_context):
    """The scope row only matches bug_fix/tech_debt; surgical+enhancement → default."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-surgical-enh',
            change_type='enhancement',
            scope_estimate='surgical',
            affected_files_count=2,
            phase_5_steps='verify:quality-gate,verify:module-tests',
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    manifest = read_manifest('matrix-surgical-enh')
    assert manifest is not None
    # Default keeps the full phase_6 candidate list — enhancement is a member of
    # the code-touching activation set {feature, bug_fix, tech_debt, enhancement}
    # that simplify_inactive gates on, and with affected_files_count > 0 the
    # security_class_inactive gate keeps its step too, so both survive.
    assert manifest['phase_6']['steps'] == list(DEFAULT_PHASE_6_STEPS)


def test_surgical_enhancement_with_docs_candidates_falls_to_default(plan_context):
    """surgical+enhancement with a docs-shaped candidate set now reaches the default row.

    This input used to be intercepted by the retired ``docs_only`` row purely
    because the candidate list lacked a module-tests / coverage role. The
    candidate list's shape says nothing about whether the change needs a build,
    so the row is gone and the ordinary matrix path applies: the scope row does
    not match ``enhancement``, so the default row fires and KEEPS the candidate.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-surgical-enh-docs',
            change_type='enhancement',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_5_steps='verify:quality-gate',
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    assert result['phase_5']['verification_steps_count'] == 1
