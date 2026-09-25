# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    pytest,
    read_manifest,
)

# =============================================================================
# Input validation tests
# =============================================================================


@pytest.mark.parametrize(
    'field,value,error_code',
    [
        ('change_type', 'unknown_type', 'invalid_change_type'),
        ('scope_estimate', 'massive', 'invalid_scope_estimate'),
        ('track', 'twisty', 'invalid_track'),
    ],
)



# =============================================================================
# Compose-time step-resolution gate
#
# `compose` resolves every FINAL emitted phase-5/6 step id and fails loud
# (`status: error`, `error: unresolvable_step`) on the first that resolves to no
# built-in doc, project-local skill, or bundle discovery-registry entry — closing
# the hole `validate-loadable` left by short-circuiting every external step to
# `loadable: true`. These fixtures cover the three fail-loud shapes (never-existed
# bundle:skill, never-existed built-in, never-existed project:) and the all-resolve
# success path (built-in + project: + promoted `plan-marshall:automatic-review` +
# opt-in `plan-marshall:plan-retrospective`). The CSV-fallback compose path carries
# no marshal.json keyed map, so the reported `marshal_key` degrades to the emitted
# step id (which still names the offending key verbatim).
# =============================================================================
def test_compose_rejects_invalid_enum_values(plan_context, field, value, error_code):
    kwargs = {field: value}
    result = cmd_compose(_compose_ns(plan_id='val-enum', **kwargs))
    assert result is not None and result['status'] == 'error'
    assert result['error'] == error_code



def test_compose_rejects_unresolvable_bundle_skill_step(plan_context):
    """A never-existed bundle:skill finalize step fails compose loud, naming the key.

    `plan-marshall:ghost-review` is preserved verbatim through boundary
    normalization (external prefixes are never stripped) and survives the Row 7
    default rule, so it reaches the resolution gate. The finalize-step discovery
    registry has no such implementor, so `compose` returns `unresolvable_step`.
    """
    candidates = (
        'push',
        'create-pr',
        'automatic-review',
        'plan-marshall:ghost-review',  # never-existed bundle:skill finalize step
        'archive-plan',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-ghost-bundle',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=6,
            phase_6_steps=','.join(candidates),
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_6'
    assert result['step_id'] == 'plan-marshall:ghost-review'
    assert result['marshal_key'] == 'plan-marshall:ghost-review'
    assert 'plan-marshall:ghost-review' in result['message']
    # No manifest is written on the fail-loud path.
    assert read_manifest('resolve-gate-ghost-bundle') is None



def test_compose_rejects_unresolvable_builtin_step(plan_context):
    """A never-existed bare built-in step fails compose loud (no standards/workflow doc)."""
    candidates = ('push', 'create-pr', 'ghost-builtin-step', 'archive-plan')
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-ghost-builtin',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=6,
            phase_6_steps=','.join(candidates),
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_6'
    assert result['step_id'] == 'ghost-builtin-step'
    assert 'ghost-builtin-step' in result['message']



def test_compose_rejects_unresolvable_project_step(plan_context):
    """A never-existed project: finalize step fails compose loud (no project-local SKILL.md)."""
    candidates = ('push', 'create-pr', 'project:finalize-step-ghost', 'archive-plan')
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-ghost-project',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=6,
            phase_6_steps=','.join(candidates),
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_6'
    assert result['step_id'] == 'project:finalize-step-ghost'
    assert 'project:finalize-step-ghost' in result['message']



def test_compose_rejects_unresolvable_phase_5_canonical(plan_context):
    """A never-existed phase-5 canonical (`verify:{bogus}`) fails compose loud.

    The verify-canonicals universe (the composer `_CANONICAL_TO_ROLE` keys unioned
    with every `ext-point-build-verify-step` implementor's `canonicals`) does not
    contain `bogus-canonical`, so the phase-5 gate rejects it before phase-6 is
    even reached.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-ghost-canonical',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=6,
            phase_5_steps='verify:quality-gate,verify:bogus-canonical',
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_5'
    assert result['step_id'] == 'verify:bogus-canonical'
    assert 'bogus-canonical' in result['message']
