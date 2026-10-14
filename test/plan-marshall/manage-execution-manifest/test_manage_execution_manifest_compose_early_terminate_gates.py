#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Early-terminated phase 5 never persists unrunnable required gates (review bdbecd).

When the compose matrix selects early_terminate True it deliberately emits an
empty phase 5 verification list, but the later additive request/project gate
pass could repopulate that list while phase 5 still short-circuits execution,
so a required gate would appear in the manifest without running. Composed
required gates lift the short-circuit so phase 5 enforces the stamped gates
verbatim.
"""

from argparse import Namespace

from conftest import create_marshal_json, load_script_module

_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_early_terminate_gates',
)
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest

_mem._log_decision = lambda *a, **kw: None


def _compose_ns(plan_id: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='analysis',
        track='complex',
        scope_estimate='none',
        recipe_key=None,
        affected_files_count=0,
        phase_5_steps='verify:quality-gate,verify:module-tests',
        phase_6_steps=None,
        commit_and_push=None,
    )


def _seed_marshal(plan_context, phase_5: dict) -> None:
    create_marshal_json(
        plan_context.fixture_dir,
        config={
            'skill_domains': {'system': {}},
            'system': {'retention': {}},
            'plan': {
                'phase-5-execute': dict(phase_5),
                'phase-6-finalize': {
                    'steps': {
                        'default:push': {},
                        'default:archive-plan': {},
                    },
                },
            },
        },
        nest_in_plan_dir=False,
    )


def test_early_terminate_lifted_for_required_gates(plan_context):
    """Composed required gates lift the early-termination short-circuit."""
    plan_id = 'early-terminate-required-gates-lifted'
    _seed_marshal(
        plan_context,
        {
            'verification_steps': {
                'default:verify:quality-gate': {},
                'default:verify:module-tests': {},
            },
            'request_gates': ['verify:coverage'],
            'project_gates': [],
        },
    )
    result = cmd_compose(_compose_ns(plan_id))
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'early_terminate_analysis'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert manifest['phase_5']['early_terminate'] is False
    assert 'verify:coverage' in manifest['phase_5']['verification_steps']


def test_early_terminate_stays_when_no_gates(plan_context):
    """Without composed gates the early-termination short-circuit stands."""
    plan_id = 'early-terminate-no-gates-stays'
    _seed_marshal(
        plan_context,
        {
            'verification_steps': {
                'default:verify:quality-gate': {},
                'default:verify:module-tests': {},
            },
        },
    )
    result = cmd_compose(_compose_ns(plan_id))
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'early_terminate_analysis'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert manifest['phase_5']['early_terminate'] is True
    assert manifest['phase_5']['verification_steps'] == []
