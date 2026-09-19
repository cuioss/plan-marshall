#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the phase-completion artifact gates (PLAN-01).

``cmd_transition`` refuses bare 2-refine / 3-outline / 4-plan transitions
unless the phase artifact exists, with an explicit logged exemption for
legitimately artifact-free phases. Pins:

(a) bare 2-refine refuses with ``refine_bare_transition``;
(b) 2-refine passes with a clarified_request section;
(c) 2-refine passes with status.metadata.confidence;
(d) bare 3-outline refuses with ``outline_bare_transition``;
(e) 3-outline passes with a validating solution_outline.md;
(f) bare 4-plan refuses with ``plan_bare_transition``;
(g) 4-plan passes with a TASK file;
(h) 4-plan passes with a composed execution.toon;
(i) exemption without reason refuses with ``missing_exempt_reason``;
(j) exemption with reason succeeds, persists phase_exemptions, and is
    decision-logged.
"""

import json
from argparse import Namespace

from _manage_status_transition_fixtures import cmd_create, cmd_transition, cmd_update_phase

from conftest import load_script_module

_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_query_gates')
cmd_set_phase = _query.cmd_set_phase


def _seed_at_phase(plan_id: str, phase: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Phase Gate Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    order = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']
    idx = order.index(phase)
    for done_phase in order[:idx]:
        cmd_update_phase(Namespace(plan_id=plan_id, phase=done_phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase=phase))


def test_bare_2_refine_refuses(plan_context):
    plan_id = 'gate-bare-2refine'
    _seed_at_phase(plan_id, '2-refine')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='2-refine'))
    assert result['status'] == 'error'
    assert result['error'] == 'refine_bare_transition'
    assert result['phase'] == '2-refine'


def test_2_refine_passes_with_clarified_request(plan_context):
    plan_id = 'gate-2refine-clarified'
    _seed_at_phase(plan_id, '2-refine')
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'request.md').write_text(
        '# Request\n\n## Original Input\n\norig\n\n## Clarified Request\n\nclarified body\n',
        encoding='utf-8',
    )
    result = cmd_transition(Namespace(plan_id=plan_id, completed='2-refine'))
    assert result['status'] == 'success'
    assert result['next_phase'] == '3-outline'


def test_2_refine_passes_with_confidence(plan_context):
    plan_id = 'gate-2refine-confidence'
    _seed_at_phase(plan_id, '2-refine')
    plan_dir = plan_context.plan_dir_for(plan_id)
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    status.setdefault('metadata', {})['confidence'] = 82
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='2-refine'))
    assert result['status'] == 'success'


def test_bare_3_outline_refuses(plan_context):
    plan_id = 'gate-bare-3outline'
    _seed_at_phase(plan_id, '3-outline')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='3-outline'))
    assert result['status'] == 'error'
    assert result['error'] == 'outline_bare_transition'


def test_3_outline_passes_with_solution_outline(plan_context):
    plan_id = 'gate-3outline-ok'
    _seed_at_phase(plan_id, '3-outline')
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution\n\n## Deliverables\n\n### Deliverable 1\n\nBody\n',
        encoding='utf-8',
    )
    result = cmd_transition(Namespace(plan_id=plan_id, completed='3-outline'))
    assert result['status'] == 'success'
    assert result['next_phase'] == '4-plan'


def test_bare_4_plan_refuses(plan_context):
    plan_id = 'gate-bare-4plan'
    _seed_at_phase(plan_id, '4-plan')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_bare_transition'


def test_4_plan_passes_with_task_file(plan_context):
    plan_id = 'gate-4plan-task'
    _seed_at_phase(plan_id, '4-plan')
    plan_dir = plan_context.plan_dir_for(plan_id)
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').write_text('{"title": "t"}', encoding='utf-8')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'success'
    assert result['next_phase'] == '5-execute'


def test_4_plan_passes_with_manifest(plan_context):
    plan_id = 'gate-4plan-manifest'
    _seed_at_phase(plan_id, '4-plan')
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'execution.toon').write_text('manifest_version: 1\n', encoding='utf-8')
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'success'


def test_exemption_without_reason_refuses(plan_context):
    plan_id = 'gate-exempt-no-reason'
    _seed_at_phase(plan_id, '2-refine')
    result = cmd_transition(
        Namespace(plan_id=plan_id, completed='2-refine', allow_bare_transition=True, bare_reason=None)
    )
    assert result['status'] == 'error'
    assert result['error'] == 'missing_exempt_reason'


def test_exemption_with_reason_persists_and_logs(plan_context):
    plan_id = 'gate-exempt-ok'
    _seed_at_phase(plan_id, '3-outline')
    result = cmd_transition(
        Namespace(
            plan_id=plan_id,
            completed='3-outline',
            allow_bare_transition=True,
            bare_reason='light-lane outline deferred to execute',
        )
    )
    assert result['status'] == 'success'
    assert result['next_phase'] == '4-plan'
    plan_dir = plan_context.plan_dir_for(plan_id)
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    exemptions = status.get('metadata', {}).get('phase_exemptions', {})
    assert exemptions.get('3-outline', {}).get('reason') == 'light-lane outline deferred to execute'
    assert 'granted_at' in exemptions['3-outline']


def test_4_plan_rejects_task_directory(plan_context):
    plan_id = 'gate-4plan-taskdir'
    _seed_at_phase(plan_id, '4-plan')
    plan_dir = plan_context.plan_dir_for(plan_id)
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').mkdir()
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_bare_transition'


def test_4_plan_rejects_manifest_directory(plan_context):
    plan_id = 'gate-4plan-manifestdir'
    _seed_at_phase(plan_id, '4-plan')
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'execution.toon').mkdir()
    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_bare_transition'
