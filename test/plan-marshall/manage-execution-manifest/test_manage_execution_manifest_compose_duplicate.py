# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _make_tier_stub,
    _mem,
    _write_task,
    cmd_compose,
    read_manifest,
)


def test_duplicate_orchestrator_routings_are_deduped(plan_context, monkeypatch):
    """Case (e): two tasks routing the same verb to ``orchestrator`` produce
    a single bare ``verify:module-tests`` entry in ``phase_5.verification_steps``."""
    plan_id = 'tier-dedupe'
    same_cmd = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
        '--command-args "verify plan-marshall"'
    )
    _write_task(plan_context.plans_dir, plan_id, 1, [same_cmd])
    _write_task(plan_context.plans_dir, plan_id, 2, [same_cmd])
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_tier_stub(orchestrator_verbs={'verify'}))

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=4))

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    steps = manifest['phase_5']['verification_steps']
    # The bare verify:module-tests appears exactly once (deduped); no prefixed stray.
    assert steps.count('verify:module-tests') == 1
    assert 'default:verify:module-tests' not in steps
