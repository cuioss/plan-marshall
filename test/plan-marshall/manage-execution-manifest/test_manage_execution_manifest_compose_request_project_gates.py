#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Request/project gate composition reads the authoritative phase object (review 84c048).

``marshal_phase_5_map`` is the ``verification_steps`` step-ID map produced by
``_read_marshal_phase_step_map`` — ``{step_id: params}`` — not the enclosing
``plan.phase-5-execute`` object, so ``.get('request_gates')`` on it always
misses and compose stamps no gates. The declarations live as siblings of
``verification_steps`` on the phase object and are read via
``_read_marshal_phase_5_gates``.
"""

from argparse import Namespace

from conftest import create_marshal_json, load_script_module

_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_request_project_gates',
)
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest

_mem._log_decision = lambda *a, **kw: None


def _compose_ns(plan_id: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=5,
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


def test_declared_gates_compose_into_verification_steps(plan_context):
    """Declared request/project gates land in the composed verification list."""
    plan_id = 'request-project-gates-compose'
    _seed_marshal(
        plan_context,
        {
            'verification_steps': {
                'default:verify:quality-gate': {},
                'default:verify:module-tests': {},
            },
            'request_gates': ['verify:coverage'],
            'project_gates': ['verify:quality-gate'],
        },
    )
    result = cmd_compose(_compose_ns(plan_id))
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    steps = manifest['phase_5']['verification_steps']
    assert 'verify:coverage' in steps
    assert 'verify:quality-gate' in steps
    assert 'verify:module-tests' in steps


def test_absent_gates_leave_list_unchanged(plan_context):
    """Absent declarations preserve the additive-only contract."""
    plan_id = 'request-project-gates-absent'
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
    manifest = read_manifest(plan_id)
    assert manifest is not None
    steps = manifest['phase_5']['verification_steps']
    assert 'verify:quality-gate' in steps
    assert 'verify:module-tests' in steps


def test_step_map_decoy_does_not_compose(plan_context):
    """The step map is not the gate source: no phase-level keys means no gates."""
    from conftest import load_script_module as _load

    _rules = _load(
        'plan-marshall',
        'manage-execution-manifest',
        '_manifest_rules.py',
        module_name='_rules_request_project_gates',
    )
    plan_id = 'request-project-gates-decoy'
    _seed_marshal(
        plan_context,
        {
            'verification_steps': {
                'default:verify:quality-gate': {},
                'default:verify:module-tests': {},
            },
        },
    )
    request_gates, project_gates = _rules._read_marshal_phase_5_gates()
    assert request_gates == []
    assert project_gates == []
    result = cmd_compose(_compose_ns(plan_id))
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    steps = manifest['phase_5']['verification_steps']
    assert 'verify:quality-gate' in steps
    assert 'request_gates' not in steps
