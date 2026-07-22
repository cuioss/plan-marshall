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
import threading
from argparse import Namespace

import pytest

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

    def test_should_reject_combined_get_and_set(self, plan_context):
        cmd_orchestrator_create(_create_args('meta-both-epic'))

        result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-both-epic', set=True, get=True, field='owner', value='operator')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_reject_combined_get_and_set_without_resurrecting_archived(self, plan_context):
        # Simulate a prior `archive`: the epic lives ONLY in the archived tree
        # (phase closed); no active tree exists. A combined --get --set call must
        # be refused up front — before allow_archived resolution or any write —
        # so the STRICT active-path write branch never resurrects the active dir.
        slug = 'meta-archived-both-epic'
        active_dir = plan_context.fixture_dir / 'orchestrator' / slug
        archived_dir = plan_context.fixture_dir / 'archived-orchestrators' / slug
        archived_dir.mkdir(parents=True, exist_ok=True)
        (archived_dir / 'status.json').write_text(
            json.dumps(
                {
                    'kind': 'orchestrator',
                    'title': 'Archived Epic',
                    'phase': 'closed',
                    'workstreams': [],
                    'plans': [],
                    'resume_anchor': 'epic closed — see history.md',
                    'metadata': {},
                    'created': '2020-01-01T00:00:00Z',
                    'updated': '2020-01-01T00:00:00Z',
                },
                indent=2,
            ),
            encoding='utf-8',
        )

        result = cmd_orchestrator_metadata(
            Namespace(plan_id=slug, set=True, get=True, field='owner', value='operator')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'
        # The refused call performed no read/write: the active tree stays absent.
        assert not active_dir.exists()


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


# =============================================================================
# Concurrency: serialized read-modify-write (PR #915 finding 63cf41)
# =============================================================================


class TestOrchestratorConcurrentWrites:
    """The orchestrator-store status.json read-modify-write is serialized behind
    the shared ``_locks_core.rmw_json`` O_EXCL guard, so two concurrent sessions
    mutating the same document cannot lose a write (last-writer-wins over a stale
    read), and the guard is released on the error path.
    """

    @pytest.mark.xdist_group(name='manage_locks_contention')
    def test_should_not_lose_interleaved_metadata_writes(self, plan_context):
        cmd_orchestrator_create(_create_args('race-epic'))

        rounds = 20
        # Every wait in this test is explicitly bounded, so a lock regression
        # surfaces as a diagnosable timeout instead of hanging the suite: the
        # barrier times out if the sibling thread never arrives, and each join
        # times out if a thread never finishes.
        barrier_timeout_seconds = 30
        join_timeout_seconds = 60
        start = threading.Barrier(2, timeout=barrier_timeout_seconds)
        errors: list[Exception] = []

        def _setter(field: str) -> None:
            try:
                start.wait()
                for i in range(rounds):
                    cmd_orchestrator_metadata(
                        Namespace(
                            plan_id='race-epic', set=True, get=False, field=field, value=f'{field}-{i}'
                        )
                    )
            except Exception as exc:  # noqa: BLE001 - surfaced into the assertion below
                errors.append(exc)

        thread_a = threading.Thread(target=_setter, args=('alpha',))
        thread_b = threading.Thread(target=_setter, args=('beta',))
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=join_timeout_seconds)
        thread_b.join(timeout=join_timeout_seconds)

        assert not thread_a.is_alive(), (
            f'writer thread alpha still running after {join_timeout_seconds}s — '
            'the serialized read-modify-write guard is likely wedged'
        )
        assert not thread_b.is_alive(), (
            f'writer thread beta still running after {join_timeout_seconds}s — '
            'the serialized read-modify-write guard is likely wedged'
        )
        assert not errors
        content = json.loads(_orchestrator_status_file(plan_context, 'race-epic').read_text(encoding='utf-8'))
        # No lost update: BOTH concurrently-written fields survived. Each set
        # merged into the FRESH in-lock state rather than clobbering the whole
        # document from a stale snapshot.
        assert content['metadata']['alpha'] == f'alpha-{rounds - 1}'
        assert content['metadata']['beta'] == f'beta-{rounds - 1}'

    def test_should_release_lock_on_mutate_error(self, plan_context):
        cmd_orchestrator_create(_create_args('err-epic'))
        status_path = _orchestrator_status_file(plan_context, 'err-epic')
        guard_path = status_path.with_name(status_path.name + '.lock')

        def _boom(_state):
            raise RuntimeError('mutate failed')

        with pytest.raises(RuntimeError, match='mutate failed'):
            _core.rmw_json(status_path, _boom)

        # The O_EXCL guard is removed in rmw_json's finally even when the
        # mutation raises — a leaked guard would wedge every later writer.
        assert not guard_path.exists()

        # And the critical section is immediately re-acquirable afterwards.
        result = cmd_orchestrator_metadata(
            Namespace(plan_id='err-epic', set=True, get=False, field='owner', value='ok')
        )
        assert result['status'] == 'success'
        content = json.loads(status_path.read_text(encoding='utf-8'))
        assert content['metadata']['owner'] == 'ok'
