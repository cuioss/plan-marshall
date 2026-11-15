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

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _read_task, _write_task

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


def _gate_only_ns(plan_id: str) -> Namespace:
    """Compose namespace whose ONLY source of the quality gate is ``project_gates``.

    ``_compose_ns`` already lists the gate in its phase-5 CSV, which would make a
    project-gate seed decorative; this one leaves the CSV with module-tests alone,
    so the gate in the composed list can only have come from the project surface.
    """
    namespace = _compose_ns(plan_id)
    namespace.phase_5_steps = 'verify:module-tests'
    return namespace


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


# =============================================================================
# Per-task quality-gate stamping
# =============================================================================
#
# A gate stamped ``per_task`` executes inline with each task, so the task's own
# ``verification.commands`` must name the resolved executable — a phase-level
# step alone leaves the leaf nothing to run. An ``orchestrator``-tier gate is
# the opposite case: no leaf runs it inline, so it must NOT be pushed into a
# task. Both arms of that split, plus the phase-level step surviving either way,
# are asserted below.

_RESOLVED_QUALITY_GATE = (
    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"'
)


def _stub_architecture_resolve(monkeypatch, tier: str, executable: str | None = _RESOLVED_QUALITY_GATE) -> None:
    """Answer every ``architecture resolve`` with the gate executable at *tier*.

    The composer asks ``architecture resolve`` for both the tier stamp and the
    executable, so one stub answers both deterministically without a live
    architecture inventory. ``executable=None`` models a resolve that reported a
    tier but no executable — the transient lookup failure whose verdict must not
    withdraw a recorded command.
    """

    def _fake(_argv_extra, _plan_id, **_kwargs):
        resolved = {
            'status': 'success',
            'command': 'quality-gate',
            'resolution_level': 'module',
            'bash_timeout_seconds': 360,
            'exceeds_bash_ceiling': tier == 'orchestrator',
            'execution_tier': tier,
            'hint': 'stubbed',
        }
        if executable is not None:
            resolved['executable'] = executable
        return resolved

    monkeypatch.setattr(_mem, '_invoke_architecture_resolve', _fake)


def _stub_architecture_resolve_diverging(monkeypatch) -> None:
    """Stamp ``per_task`` but report ``orchestrator`` on the attributed lookup.

    The stamp is a snapshot; a probe that failed earlier stamps the permissive
    ``per_task`` default, so the attributed lookup can find the gate at
    orchestrator tier. That fresh verdict is the routing authority.
    """

    def _fake(_argv_extra, _plan_id, **kwargs):
        tier = 'orchestrator' if kwargs.get('top_level_plan_id') else 'per_task'
        return {
            'status': 'success',
            'command': 'quality-gate',
            'executable': _RESOLVED_QUALITY_GATE,
            'resolution_level': 'module',
            'bash_timeout_seconds': 900 if tier == 'orchestrator' else 360,
            'exceeds_bash_ceiling': tier == 'orchestrator',
            'execution_tier': tier,
            'hint': 'stubbed',
        }

    monkeypatch.setattr(_mem, '_invoke_architecture_resolve', _fake)


def _seed_gate_plan(plan_context, plan_id: str) -> None:
    """Seed a plan whose composed gates carry the project's quality gate.

    Task 1 carries no derived command and task 2 carries a non-build one, so the
    gate append is observable on both a bare and an already-populated
    verification block.
    """
    _seed_marshal(
        plan_context,
        {
            'verification_steps': {'default:verify:module-tests': {}},
            'project_gates': ['verify:quality-gate'],
        },
    )
    _write_task(plan_context.plans_dir, plan_id, 1, [])
    _write_task(plan_context.plans_dir, plan_id, 2, ['pytest test/plan-marshall/example_test.py'])


def test_per_task_gate_reaches_every_task_verification(plan_context, monkeypatch):
    """A project-declared quality gate stamped per_task reaches each task's commands."""
    plan_id = 'request-project-gates-per-task'
    _seed_gate_plan(plan_context, plan_id)
    _stub_architecture_resolve(monkeypatch, 'per_task')

    result = cmd_compose(_gate_only_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert 'verify:quality-gate' in manifest['phase_5']['verification_steps'], 'the gate came from project_gates'
    commands_by_task = {
        number: _read_task(plan_context.plans_dir, plan_id, number)['verification']['commands'] for number in (1, 2)
    }
    assert commands_by_task[1] == [_RESOLVED_QUALITY_GATE], 'a task with no derived command still gets the gate'
    assert commands_by_task[2] == ['pytest test/plan-marshall/example_test.py', _RESOLVED_QUALITY_GATE], (
        'the gate is appended after the command the task already carried'
    )


def test_gate_append_is_withdrawn_when_the_stamp_stops_covering_it(plan_context, monkeypatch):
    """A re-compose whose tier flipped to orchestrator takes the gate command back out.

    The stamp is an advisory snapshot, so the flip is ordinary; an append that
    could not be withdrawn would leave a gate command on the task forever and the
    task file would stop describing the manifest.
    """
    plan_id = 'request-project-gates-withdrawal'
    _seed_gate_plan(plan_context, plan_id)
    _stub_architecture_resolve(monkeypatch, 'per_task')
    assert cmd_compose(_gate_only_ns(plan_id))['status'] == 'success'
    appended = _read_task(plan_context.plans_dir, plan_id, 1)['verification']
    assert appended['commands'] == [_RESOLVED_QUALITY_GATE]
    assert appended['per_task_gate_commands'] == [_RESOLVED_QUALITY_GATE]

    # The routing pass must not be able to remove the command itself, or this
    # test would pass without the withdrawal doing anything.
    monkeypatch.setattr(_mem, '_resolve_command_tier', lambda *_args, **_kwargs: None)
    _stub_architecture_resolve(monkeypatch, 'orchestrator')
    assert cmd_compose(_gate_only_ns(plan_id))['status'] == 'success'

    verification = _read_task(plan_context.plans_dir, plan_id, 1)['verification']
    assert verification['commands'] == [], 'the appended gate is withdrawn with its stamp'
    assert 'per_task_gate_commands' not in verification


def test_the_attributed_lookup_tier_decides_the_append(plan_context, monkeypatch):
    """A stamp of `per_task` does not append a gate the fresh lookup places at orchestrator.

    The stamp is a snapshot taken when the tier probe may have failed and fallen
    back to the permissive default; the attributed lookup is fresher, so its tier
    is what decides whether a leaf runs the gate inline.
    """
    plan_id = 'request-project-gates-diverging-tier'
    _seed_gate_plan(plan_context, plan_id)
    _stub_architecture_resolve_diverging(monkeypatch)

    result = cmd_compose(_gate_only_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert 'verify:quality-gate' in manifest['phase_5']['verification_steps']
    assert _read_task(plan_context.plans_dir, plan_id, 1)['verification']['commands'] == []


def test_recorded_gate_command_survives_an_unresolved_lookup(plan_context, monkeypatch):
    """A resolve that reports the tier but no executable withdraws nothing.

    The stamp still covers the gate, so a transient lookup failure must leave the
    previously appended command on the task — otherwise a flaky resolve would
    silently drop the gate from every task it had reached.
    """
    plan_id = 'request-project-gates-unresolved'
    _seed_gate_plan(plan_context, plan_id)
    _stub_architecture_resolve(monkeypatch, 'per_task')
    assert cmd_compose(_gate_only_ns(plan_id))['status'] == 'success'

    monkeypatch.setattr(_mem, '_resolve_command_tier', lambda *_args, **_kwargs: None)
    _stub_architecture_resolve(monkeypatch, 'per_task', executable=None)
    assert cmd_compose(_gate_only_ns(plan_id))['status'] == 'success'

    verification = _read_task(plan_context.plans_dir, plan_id, 1)['verification']
    assert verification['commands'] == [_RESOLVED_QUALITY_GATE], 'the stamp still covers the gate'
    assert verification['per_task_gate_commands'] == [_RESOLVED_QUALITY_GATE]


def test_per_task_gate_leaves_the_phase_level_step_in_place(plan_context, monkeypatch):
    """The phase-level gate step survives the per-task stamp."""
    plan_id = 'request-project-gates-per-task-kept'
    _seed_gate_plan(plan_context, plan_id)
    _stub_architecture_resolve(monkeypatch, 'per_task')

    result = cmd_compose(_gate_only_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert 'verify:quality-gate' in manifest['phase_5']['verification_steps']


def test_orchestrator_tier_gate_is_not_pushed_into_a_task(plan_context, monkeypatch):
    """An orchestrator-tier gate runs at the phase level only, never inline per task."""
    plan_id = 'request-project-gates-orchestrator'
    _seed_gate_plan(plan_context, plan_id)
    _stub_architecture_resolve(monkeypatch, 'orchestrator')

    result = cmd_compose(_gate_only_ns(plan_id))

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert 'verify:quality-gate' in manifest['phase_5']['verification_steps']
    for number in (1, 2):
        commands = _read_task(plan_context.plans_dir, plan_id, number)['verification']['commands']
        assert _RESOLVED_QUALITY_GATE not in commands, 'no leaf runs an orchestrator-tier gate inline'
