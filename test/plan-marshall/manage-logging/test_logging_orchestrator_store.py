#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-logging orchestrator store (--store orchestrator, D6).

Covers:
- get_log_path resolution under the orchestrator store
  (``.plan/local/orchestrator/{slug}/logs/{work,decision}.log``).
- decision/work log round-trip under the orchestrator store, both in-process
  (plan_logging library) and through the manage-logging.py CLI entry point.
- CLI boundary: ``--store orchestrator`` requires ``--plan-id`` (the epic
  slug); the ``script`` verb carries no ``--store`` flag.
- Default-store regression: plans-store behavior is byte-identical with and
  without the explicit ``--store plans`` flag, and orchestrator writes never
  leak into the plans tree.
"""

import json

from plan_logging import get_log_path, log_entry, read_decision_log, read_work_log

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-logging', 'manage-logging.py')


def _orchestrator_logs_dir(plan_context, slug: str):
    return plan_context.fixture_dir / 'orchestrator' / slug / 'logs'


def _archived_orchestrator_logs_dir(plan_context, slug: str):
    return plan_context.fixture_dir / 'archived-orchestrators' / slug / 'logs'


def _init_plan(plan_context, plan_id: str) -> None:
    """Create an initialized plan dir (status.json sentinel) in the plans store."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(json.dumps({'plan_id': plan_id}), encoding='utf-8')


# =============================================================================
# Path resolution
# =============================================================================


class TestOrchestratorLogPath:
    def test_should_resolve_work_log_under_orchestrator_tree(self, plan_context):
        path = get_log_path('test-epic', 'work', store='orchestrator')

        assert path == _orchestrator_logs_dir(plan_context, 'test-epic') / 'work.log'

    def test_should_resolve_decision_log_under_orchestrator_tree(self, plan_context):
        path = get_log_path('test-epic', 'decision', store='orchestrator')

        assert path == _orchestrator_logs_dir(plan_context, 'test-epic') / 'decision.log'

    def test_should_keep_default_store_plan_scoped_for_initialized_plan(self, plan_context):
        _init_plan(plan_context, 'default-plan')

        implicit = get_log_path('default-plan', 'work')
        explicit = get_log_path('default-plan', 'work', store='plans')

        assert implicit == explicit
        assert implicit == plan_context.plans_dir / 'default-plan' / 'logs' / 'work.log'


# =============================================================================
# Library round-trip
# =============================================================================


class TestOrchestratorLibraryRoundTrip:
    def test_should_round_trip_work_entry_under_orchestrator_store(self, plan_context):
        log_entry('work', 'rt-epic', 'INFO', '[PLAN-STATUS] (plan-marshall:marshall-orchestrator) PLAN-01 queued -> running', store='orchestrator')

        result = read_work_log('rt-epic', store='orchestrator')

        assert result['status'] == 'success'
        assert result['total_entries'] == 1
        assert 'PLAN-01 queued -> running' in result['entries'][0]['message']

    def test_should_round_trip_decision_entry_under_orchestrator_store(self, plan_context):
        log_entry('decision', 'rt-epic', 'INFO', '(plan-marshall:marshall-orchestrator) Decomposed epic into 3 workstreams', store='orchestrator')

        result = read_decision_log('rt-epic', store='orchestrator')

        assert result['status'] == 'success'
        assert result['total_entries'] == 1
        assert 'Decomposed epic' in result['entries'][0]['message']

    def test_should_keep_orchestrator_entries_out_of_plans_store_read(self, plan_context):
        _init_plan(plan_context, 'rt-epic')

        log_entry('work', 'rt-epic', 'INFO', '[INTERACTION] orchestrator-only entry', store='orchestrator')

        plans_read = read_work_log('rt-epic', store='plans')
        assert plans_read['total_entries'] == 0


# =============================================================================
# Archived read-fallback (allow_archived transparency for log appends)
# =============================================================================


class TestOrchestratorArchivedFallback:
    """get_log_path resolves the orchestrator store with allow_archived=True, so a
    log append against an archived-only epic lands in the archived logs/ tree
    instead of scaffolding an empty active-path directory.
    """

    def test_should_resolve_archived_tree_when_only_archived_exists(self, plan_context):
        slug = 'archived-only-epic'
        (plan_context.fixture_dir / 'archived-orchestrators' / slug).mkdir(parents=True, exist_ok=True)

        path = get_log_path(slug, 'decision', store='orchestrator')

        assert path == _archived_orchestrator_logs_dir(plan_context, slug) / 'decision.log'

    def test_should_resolve_active_tree_when_both_active_and_archived_exist(self, plan_context):
        slug = 'both-exist-epic'
        (plan_context.fixture_dir / 'orchestrator' / slug).mkdir(parents=True, exist_ok=True)
        (plan_context.fixture_dir / 'archived-orchestrators' / slug).mkdir(parents=True, exist_ok=True)

        path = get_log_path(slug, 'work', store='orchestrator')

        # Active wins when both trees exist.
        assert path == _orchestrator_logs_dir(plan_context, slug) / 'work.log'

    def test_should_name_active_tree_when_neither_exists(self, plan_context):
        slug = 'brand-new-epic'

        path = get_log_path(slug, 'work', store='orchestrator')

        # Brand-new epic before scaffold: fall back to naming the active tree.
        assert path == _orchestrator_logs_dir(plan_context, slug) / 'work.log'

    def test_log_entry_appends_into_archived_tree_without_resurrecting_active(self, plan_context):
        slug = 'frozen-log-epic'
        (plan_context.fixture_dir / 'archived-orchestrators' / slug).mkdir(parents=True, exist_ok=True)
        active_dir = plan_context.fixture_dir / 'orchestrator' / slug

        log_entry(
            'decision',
            slug,
            'INFO',
            '(plan-marshall:marshall-orchestrator) archive decision on frozen epic',
            store='orchestrator',
        )

        # The append landed in the archived logs/ tree...
        result = read_decision_log(slug, store='orchestrator')
        assert result['status'] == 'success'
        assert result['total_entries'] == 1
        assert (_archived_orchestrator_logs_dir(plan_context, slug) / 'decision.log').is_file()
        # ...and did NOT resurrect an active-path directory.
        assert not active_dir.exists()


# =============================================================================
# CLI boundary
# =============================================================================


class TestOrchestratorCli:
    def test_should_write_and_read_work_log_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        write = run_script(
            SCRIPT_PATH,
            'work',
            '--plan-id',
            'cli-epic',
            '--level',
            'INFO',
            '--message',
            '[RECONCILIATION] (plan-marshall:marshall-orchestrator) Folded landing report PLAN-01',
            '--store',
            'orchestrator',
            env_overrides=env,
        )
        read = run_script(
            SCRIPT_PATH,
            'read',
            '--plan-id',
            'cli-epic',
            '--type',
            'work',
            '--store',
            'orchestrator',
            env_overrides=env,
        )

        assert write.returncode == 0
        assert read.returncode == 0
        assert 'Folded landing report PLAN-01' in read.stdout
        assert (_orchestrator_logs_dir(plan_context, 'cli-epic') / 'work.log').is_file()

    def test_should_write_and_read_decision_log_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        write = run_script(
            SCRIPT_PATH,
            'decision',
            '--plan-id',
            'cli-epic',
            '--level',
            'INFO',
            '--message',
            '(plan-marshall:marshall-orchestrator) Parked PLAN-03 until PLAN-01 lands',
            '--store',
            'orchestrator',
            env_overrides=env,
        )
        read = run_script(
            SCRIPT_PATH,
            'read',
            '--plan-id',
            'cli-epic',
            '--type',
            'decision',
            '--store',
            'orchestrator',
            env_overrides=env,
        )

        assert write.returncode == 0
        assert read.returncode == 0
        assert 'Parked PLAN-03' in read.stdout
        assert (_orchestrator_logs_dir(plan_context, 'cli-epic') / 'decision.log').is_file()

    def test_should_reject_orchestrator_store_without_plan_id(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(
            SCRIPT_PATH,
            'work',
            '--level',
            'INFO',
            '--message',
            'orphan entry',
            '--store',
            'orchestrator',
            env_overrides=env,
        )

        assert 'missing_plan_id' in result.stdout

    def test_should_not_offer_store_flag_on_script_verb(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(
            SCRIPT_PATH,
            'script',
            '--plan-id',
            'cli-epic',
            '--level',
            'INFO',
            '--message',
            'notation call (0.1s)',
            '--store',
            'orchestrator',
            env_overrides=env,
        )

        assert result.returncode == 2


# =============================================================================
# Default-store regression
# =============================================================================


class TestPlansStoreRegression:
    def test_should_write_plans_store_identically_with_and_without_store_flag(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _init_plan(plan_context, 'regression-plan')

        implicit = run_script(
            SCRIPT_PATH,
            'work',
            '--plan-id',
            'regression-plan',
            '--level',
            'INFO',
            '--message',
            '[STATUS] implicit-store entry',
            env_overrides=env,
        )
        explicit = run_script(
            SCRIPT_PATH,
            'work',
            '--plan-id',
            'regression-plan',
            '--level',
            'INFO',
            '--message',
            '[STATUS] explicit-store entry',
            '--store',
            'plans',
            env_overrides=env,
        )

        assert implicit.returncode == 0
        assert explicit.returncode == 0
        work_log = plan_context.plans_dir / 'regression-plan' / 'logs' / 'work.log'
        content = work_log.read_text(encoding='utf-8')
        assert 'implicit-store entry' in content
        assert 'explicit-store entry' in content

    def test_should_keep_orchestrator_store_out_of_plans_tree(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(
            SCRIPT_PATH,
            'work',
            '--plan-id',
            'separation-epic',
            '--level',
            'INFO',
            '--message',
            '[INTERACTION] orchestrator entry',
            '--store',
            'orchestrator',
            env_overrides=env,
        )

        assert result.returncode == 0
        assert not (plan_context.plans_dir / 'separation-epic').exists()
        assert (_orchestrator_logs_dir(plan_context, 'separation-epic') / 'work.log').is_file()
