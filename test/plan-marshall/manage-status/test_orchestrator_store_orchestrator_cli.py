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
from _orchestrator_store_fixtures import (
    SCRIPT_PATH,
    _core,
    _create_args,
    _orchestrator_status_file,
    cmd_orchestrator_create,
    cmd_orchestrator_metadata,
)

from conftest import run_script

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
# Concurrency: serialized read-modify-write
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
