# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_compose_succeeds_when_every_step_resolves(plan_context):
    """The gate passes for a fully-resolvable step list.

    Covers all four resolution branches: built-in (`push`/`create-pr`/…), the
    promoted `plan-marshall:automatic-review` (boundary-normalized to the bare
    `automatic-review` built-in), a project-local `project:finalize-step-plugin-doctor`,
    and the opt-in `plan-marshall:plan-retrospective` bundle:skill finalize step,
    plus phase-5 canonical-verify steps. `multi_module` scope keeps
    `plan-marshall:plan-retrospective` (the scope gate only drops it on
    surgical/single_module), so it reaches — and passes — the gate.
    """
    resolvable = (
        'push',
        'create-pr',
        'plan-marshall:automatic-review',  # promoted → normalizes to bare automatic-review
        'project:finalize-step-plugin-doctor',  # project-local skill
        'lessons-capture',
        'plan-marshall:plan-retrospective',  # opt-in bundle:skill finalize step
        'branch-cleanup',
        'archive-plan',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-pass',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
            phase_5_steps='verify:quality-gate,verify:module-tests',
            phase_6_steps=','.join(resolvable),
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('resolve-gate-pass')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # The promoted bundle id normalized to bare; the opt-in bundle step and the
    # project step survived verbatim — all resolved by the gate.
    assert 'automatic-review' in steps
    assert 'project:finalize-step-plugin-doctor' in steps
    assert 'plan-marshall:plan-retrospective' in steps
    # Phase-5 canonical-verify steps resolved too.
    assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']
