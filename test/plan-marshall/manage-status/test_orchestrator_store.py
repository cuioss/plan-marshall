#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-status orchestrator store (kind=orchestrator, D5).

Covers:
- create/read/update-field/metadata round-trip under the orchestrator store
  (PLAN_BASE_DIR isolation via plan_context).
- kind=orchestrator schema fields validated on create.
- update-field validation: phase enum, list fields require JSON arrays,
  unknown fields rejected.
- CLI boundary: the new ``update-field`` verb and ``--store orchestrator``
  flags driven through the manage-status.py entry point.
- Default-store regression: plans-store calls remain byte-identical with and
  without the explicit ``--store plans`` flag.
"""

import json
from argparse import Namespace

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_status_core_orchestrator')

cmd_orchestrator_create = _core.cmd_orchestrator_create
cmd_orchestrator_read = _core.cmd_orchestrator_read
cmd_orchestrator_update_field = _core.cmd_orchestrator_update_field
cmd_orchestrator_metadata = _core.cmd_orchestrator_metadata


def _create_args(slug: str, title: str = 'Test Epic', force: bool = False) -> Namespace:
    return Namespace(plan_id=slug, title=title, force=force)


def _orchestrator_status_file(plan_context, slug: str):
    return plan_context.fixture_dir / 'orchestrator' / slug / 'status.json'


# =============================================================================
# Create
# =============================================================================


class TestOrchestratorCreate:
    def test_should_create_status_with_orchestrator_schema(self, plan_context):
        result = cmd_orchestrator_create(_create_args('test-epic'))

        assert result['status'] == 'success'
        assert result['store'] == 'orchestrator'
        content = json.loads(_orchestrator_status_file(plan_context, 'test-epic').read_text(encoding='utf-8'))
        assert content['kind'] == 'orchestrator'
        assert content['title'] == 'Test Epic'
        assert content['phase'] == 'init'
        assert content['workstreams'] == []
        assert content['plans'] == []
        assert content['resume_anchor'] == ''
        assert content['metadata'] == {}
        assert 'created' in content
        assert 'updated' in content

    def test_should_reject_duplicate_create_without_force(self, plan_context):
        cmd_orchestrator_create(_create_args('dup-epic'))

        result = cmd_orchestrator_create(_create_args('dup-epic', title='Second'))

        assert result['status'] == 'error'
        assert result['error'] == 'already_exists'

    def test_should_overwrite_with_force(self, plan_context):
        cmd_orchestrator_create(_create_args('force-epic', title='Original'))

        result = cmd_orchestrator_create(_create_args('force-epic', title='Replaced', force=True))

        assert result['status'] == 'success'
        content = json.loads(_orchestrator_status_file(plan_context, 'force-epic').read_text(encoding='utf-8'))
        assert content['title'] == 'Replaced'


# =============================================================================
# Read
# =============================================================================


class TestOrchestratorRead:
    def test_should_read_created_status(self, plan_context):
        cmd_orchestrator_create(_create_args('read-epic'))

        result = cmd_orchestrator_read(Namespace(plan_id='read-epic'))

        assert result['status'] == 'success'
        assert result['store'] == 'orchestrator'
        assert result['plan']['kind'] == 'orchestrator'
        assert result['plan']['phase'] == 'init'

    def test_should_return_none_for_missing_status(self, plan_context, capsys):
        result = cmd_orchestrator_read(Namespace(plan_id='absent-epic'))

        assert result is None
        assert 'file_not_found' in capsys.readouterr().out


# =============================================================================
# update-field
# =============================================================================


class TestOrchestratorUpdateField:
    def test_should_update_phase_through_lifecycle(self, plan_context):
        cmd_orchestrator_create(_create_args('phase-epic'))

        for phase in ('orchestrating', 'closed'):
            result = cmd_orchestrator_update_field(
                Namespace(plan_id='phase-epic', field='phase', value=phase)
            )
            assert result['status'] == 'success'

        content = json.loads(_orchestrator_status_file(plan_context, 'phase-epic').read_text(encoding='utf-8'))
        assert content['phase'] == 'closed'

    def test_should_reject_invalid_phase_value(self, plan_context):
        cmd_orchestrator_create(_create_args('bad-phase-epic'))

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='bad-phase-epic', field='phase', value='running')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_value'

    def test_should_reject_unknown_field(self, plan_context):
        cmd_orchestrator_create(_create_args('bad-field-epic'))

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='bad-field-epic', field='kind', value='plan')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'

    def test_should_update_resume_anchor_verbatim(self, plan_context):
        cmd_orchestrator_create(_create_args('anchor-epic'))

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='anchor-epic', field='resume_anchor', value='await PR #912 CI, then analyze landing')
        )

        assert result['status'] == 'success'
        content = json.loads(_orchestrator_status_file(plan_context, 'anchor-epic').read_text(encoding='utf-8'))
        assert content['resume_anchor'] == 'await PR #912 CI, then analyze landing'

    def test_should_update_plans_list_from_json_array(self, plan_context):
        cmd_orchestrator_create(_create_args('queue-epic'))
        plans = [
            {
                'id': 'PLAN-01',
                'slug': 'first-plan',
                'workstream': 'WS-01',
                'status': 'staged',
                'plan_marshall_plan_id': '',
                'pr': '',
                'landing': '',
            }
        ]

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='queue-epic', field='plans', value=json.dumps(plans))
        )

        assert result['status'] == 'success'
        content = json.loads(_orchestrator_status_file(plan_context, 'queue-epic').read_text(encoding='utf-8'))
        assert content['plans'] == plans

    def test_should_update_workstreams_list_from_json_array(self, plan_context):
        cmd_orchestrator_create(_create_args('ws-epic'))

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='ws-epic', field='workstreams', value='["WS-01", "WS-02"]')
        )

        assert result['status'] == 'success'
        content = json.loads(_orchestrator_status_file(plan_context, 'ws-epic').read_text(encoding='utf-8'))
        assert content['workstreams'] == ['WS-01', 'WS-02']

    def test_should_reject_non_json_array_for_list_field(self, plan_context):
        cmd_orchestrator_create(_create_args('bad-list-epic'))

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='bad-list-epic', field='plans', value='not-json')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_value'


# =============================================================================
# Metadata
# =============================================================================


class TestOrchestratorMetadata:
    def test_should_round_trip_metadata_field(self, plan_context):
        cmd_orchestrator_create(_create_args('meta-epic'))

        set_result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-epic', set=True, get=False, field='owner', value='operator')
        )
        get_result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-epic', set=False, get=True, field='owner', value=None)
        )

        assert set_result['status'] == 'success'
        assert get_result['status'] == 'success'
        assert get_result['value'] == 'operator'

    def test_should_report_not_found_for_missing_metadata_field(self, plan_context):
        cmd_orchestrator_create(_create_args('meta-missing-epic'))

        result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-missing-epic', set=False, get=True, field='absent', value=None)
        )

        assert result['status'] == 'not_found'

    def test_should_require_get_or_set(self, plan_context):
        cmd_orchestrator_create(_create_args('meta-noop-epic'))

        result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-noop-epic', set=False, get=False, field='x', value=None)
        )

        assert result['status'] == 'error'
        assert result['error'] == 'missing_operation'


# =============================================================================
# CLI boundary (new verb + --store flags through the entry point)
# =============================================================================


class TestOrchestratorCli:
    def test_should_create_and_update_field_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        create = run_script(
            SCRIPT_PATH,
            'create',
            '--store',
            'orchestrator',
            '--plan-id',
            'cli-epic',
            '--title',
            'CLI Epic',
            env_overrides=env,
        )
        update = run_script(
            SCRIPT_PATH,
            'update-field',
            '--plan-id',
            'cli-epic',
            '--field',
            'phase',
            '--value',
            'orchestrating',
            env_overrides=env,
        )
        read = run_script(
            SCRIPT_PATH,
            'read',
            '--store',
            'orchestrator',
            '--plan-id',
            'cli-epic',
            env_overrides=env,
        )

        assert create.returncode == 0
        assert 'status: success' in create.stdout
        assert update.returncode == 0
        assert 'status: success' in update.stdout
        assert read.returncode == 0
        assert 'kind: orchestrator' in read.stdout
        assert 'phase: orchestrating' in read.stdout

    def test_should_ignore_phases_for_orchestrator_create(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(
            SCRIPT_PATH,
            'create',
            '--store',
            'orchestrator',
            '--plan-id',
            'cli-phases-epic',
            '--title',
            'Epic',
            '--phases',
            '1-init,2-refine',
            env_overrides=env,
        )

        assert result.returncode == 0
        content = json.loads(
            _orchestrator_status_file(plan_context, 'cli-phases-epic').read_text(encoding='utf-8')
        )
        assert 'phases' not in content
        assert content['phase'] == 'init'

    def test_should_require_phases_for_plans_store_create(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'cli-plan',
            '--title',
            'Plan',
            env_overrides=env,
        )

        assert result.returncode == 2
        assert 'wrong_parameters' in result.stdout


# =============================================================================
# Default-store regression
# =============================================================================


class TestPlansStoreRegression:
    def test_should_read_plans_store_identically_with_and_without_store_flag(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        create = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'regression-plan',
            '--title',
            'Regression',
            '--phases',
            '1-init,2-refine',
            env_overrides=env,
        )
        assert create.returncode == 0

        implicit = run_script(SCRIPT_PATH, 'read', '--plan-id', 'regression-plan', env_overrides=env)
        explicit = run_script(
            SCRIPT_PATH, 'read', '--store', 'plans', '--plan-id', 'regression-plan', env_overrides=env
        )

        assert implicit.returncode == 0
        assert explicit.returncode == 0
        assert implicit.stdout == explicit.stdout

    def test_should_keep_orchestrator_store_out_of_plans_tree(self, plan_context):
        cmd_orchestrator_create(_create_args('separation-epic'))

        assert not (plan_context.plans_dir / 'separation-epic').joinpath('status.json').exists()
        assert _orchestrator_status_file(plan_context, 'separation-epic').exists()
