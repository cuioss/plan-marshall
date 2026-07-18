#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the marshall-orchestrator ``archive`` verb and the archived-epic
read-fallback across the store-resolver seam.

Covers the fourth deterministic ``orchestrator.py`` operation plus the
read-fallback flags threaded through ``file_ops.get_store_dir`` /
``manage-status``'s orchestrator handlers, all under ``PLAN_BASE_DIR``
isolation (via ``plan_context``):

- ``cmd_archive``: relocate a ``phase=closed`` epic (active → archived);
  refuse a non-closed epic (``not_closed``, no move); idempotent re-run of an
  already-archived slug (``already_archived``); refuse when no epic exists
  (``not_found``); refuse to clobber (``archive_conflict``); reject an invalid
  slug.
- Read-fallback: after archiving, ``orchestrator.py resume-summary`` and
  ``manage-status read --store orchestrator`` still resolve the epic from
  ``archived-orchestrators/``.
- Write-refusal: ``manage-status update-field --store orchestrator`` against an
  archived-only epic refuses with ``file_not_found`` (no resurrection at the
  active path).
- CLI boundary: ``archive`` driven through the ``orchestrator.py`` entry point
  with constructed argv at the subprocess boundary (``run_script``).
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

ORCH_SCRIPT_PATH = get_script_path('plan-marshall', 'marshall-orchestrator', 'orchestrator.py')
STATUS_SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

_orch = load_script_module(
    'plan-marshall', 'marshall-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

cmd_archive = _orch.cmd_archive
cmd_resume_summary = _orch.cmd_resume_summary
cmd_scaffold = _orch.cmd_scaffold

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'


def _active_epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _archived_epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'archived-orchestrators' / slug


def _write_epic_status(epic_dir: Path, phase: str = 'closed') -> Path:
    """Write a minimal kind=orchestrator status.json into ``epic_dir``."""
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Epic',
        'phase': phase,
        'workstreams': ['WS-01'],
        'plans': [],
        'resume_anchor': 'audit record',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    epic_dir.mkdir(parents=True, exist_ok=True)
    path = epic_dir / 'status.json'
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _seed_active_epic(plan_context, slug: str, phase: str = 'closed') -> Path:
    """Scaffold the active epic tree and write its status.json at ``phase``."""
    cmd_scaffold(Namespace(slug=slug))
    return _write_epic_status(_active_epic_dir(plan_context, slug), phase=phase)


# =============================================================================
# cmd_archive — relocation
# =============================================================================


class TestArchiveRelocation:
    def test_should_move_closed_epic_to_archived(self, plan_context):
        _seed_active_epic(plan_context, 'closed-epic', phase='closed')
        active = _active_epic_dir(plan_context, 'closed-epic')
        archived = _archived_epic_dir(plan_context, 'closed-epic')

        result = cmd_archive(Namespace(slug='closed-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'archive'
        assert result['already_archived'] is False
        assert result['archived_to'] == str(archived)
        assert not active.exists()
        assert (archived / 'status.json').is_file()

    def test_should_preserve_status_json_across_the_move(self, plan_context):
        _seed_active_epic(plan_context, 'preserve-epic', phase='closed')

        cmd_archive(Namespace(slug='preserve-epic'))

        moved = _archived_epic_dir(plan_context, 'preserve-epic') / 'status.json'
        doc = json.loads(moved.read_text(encoding='utf-8'))
        assert doc['phase'] == 'closed'
        assert doc['kind'] == 'orchestrator'


# =============================================================================
# cmd_archive — refusals
# =============================================================================


class TestArchiveRefusals:
    def test_should_refuse_non_closed_epic_with_no_move(self, plan_context):
        _seed_active_epic(plan_context, 'busy-epic', phase='orchestrating')
        active = _active_epic_dir(plan_context, 'busy-epic')

        result = cmd_archive(Namespace(slug='busy-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_closed'
        assert result['phase'] == 'orchestrating'
        assert 'run close first' in result['message']
        # No move performed: active tree intact, archived tree absent.
        assert (active / 'status.json').is_file()
        assert not _archived_epic_dir(plan_context, 'busy-epic').exists()

    def test_should_error_when_no_epic_exists(self, plan_context):
        result = cmd_archive(Namespace(slug='ghost-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_should_refuse_to_clobber_existing_archive(self, plan_context):
        _seed_active_epic(plan_context, 'dup-epic', phase='closed')
        # An archived tree already exists for the same slug.
        _write_epic_status(_archived_epic_dir(plan_context, 'dup-epic'), phase='closed')
        active = _active_epic_dir(plan_context, 'dup-epic')

        result = cmd_archive(Namespace(slug='dup-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'archive_conflict'
        # Neither tree is destroyed.
        assert (active / 'status.json').is_file()
        assert (_archived_epic_dir(plan_context, 'dup-epic') / 'status.json').is_file()

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_archive(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# cmd_archive — idempotency
# =============================================================================


class TestArchiveIdempotency:
    def test_should_report_already_archived_when_only_archived_exists(self, plan_context):
        # No active tree; only the archived tree is present.
        _write_epic_status(_archived_epic_dir(plan_context, 'done-epic'), phase='closed')
        archived = _archived_epic_dir(plan_context, 'done-epic')

        result = cmd_archive(Namespace(slug='done-epic'))

        assert result['status'] == 'success'
        assert result['already_archived'] is True
        assert result['archived_to'] == str(archived)
        assert (archived / 'status.json').is_file()

    def test_should_be_idempotent_on_repeated_archive(self, plan_context):
        _seed_active_epic(plan_context, 'twice-epic', phase='closed')

        first = cmd_archive(Namespace(slug='twice-epic'))
        second = cmd_archive(Namespace(slug='twice-epic'))

        assert first['status'] == 'success'
        assert first['already_archived'] is False
        assert second['status'] == 'success'
        assert second['already_archived'] is True
        assert second['archived_to'] == first['archived_to']


# =============================================================================
# Read-fallback — archived epics stay resolvable by the read verbs
# =============================================================================


class TestReadFallback:
    def test_resume_summary_resolves_archived_epic(self, plan_context):
        _seed_active_epic(plan_context, 'summary-epic', phase='closed')
        cmd_archive(Namespace(slug='summary-epic'))

        result = cmd_resume_summary(Namespace(slug='summary-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'resume-summary'
        assert '**Phase**: closed' in result['summary']

    def test_manage_status_read_resolves_archived_epic_via_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_active_epic(plan_context, 'read-epic', phase='closed')
        run_script(ORCH_SCRIPT_PATH, 'archive', '--slug', 'read-epic', env_overrides=env)

        read = run_script(
            STATUS_SCRIPT_PATH,
            'read',
            '--store',
            'orchestrator',
            '--plan-id',
            'read-epic',
            env_overrides=env,
        )

        assert read.returncode == 0
        assert 'status: success' in read.stdout
        assert 'closed' in read.stdout


# =============================================================================
# Write-refusal — writes never resurrect an archived-only epic
# =============================================================================


class TestWriteRefusal:
    def test_manage_status_update_field_refuses_archived_only_epic(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_active_epic(plan_context, 'frozen-epic', phase='closed')
        run_script(ORCH_SCRIPT_PATH, 'archive', '--slug', 'frozen-epic', env_overrides=env)

        update = run_script(
            STATUS_SCRIPT_PATH,
            'update-field',
            '--plan-id',
            'frozen-epic',
            '--field',
            'resume_anchor',
            '--value',
            'reopened',
            env_overrides=env,
        )

        assert 'file_not_found' in update.stdout
        # No active tree was recreated by the refused write.
        assert not _active_epic_dir(plan_context, 'frozen-epic').exists()


# =============================================================================
# CLI boundary (constructed argv at the subprocess boundary)
# =============================================================================


class TestCli:
    def test_should_archive_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_active_epic(plan_context, 'cli-epic', phase='closed')

        result = run_script(ORCH_SCRIPT_PATH, 'archive', '--slug', 'cli-epic', env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'already_archived: false' in result.stdout
        assert (_archived_epic_dir(plan_context, 'cli-epic') / 'status.json').is_file()
        assert not _active_epic_dir(plan_context, 'cli-epic').exists()

    def test_should_refuse_non_closed_epic_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_active_epic(plan_context, 'cli-busy-epic', phase='orchestrating')

        result = run_script(
            ORCH_SCRIPT_PATH, 'archive', '--slug', 'cli-busy-epic', env_overrides=env
        )

        assert result.returncode == 0
        assert 'error: not_closed' in result.stdout
        assert (_active_epic_dir(plan_context, 'cli-busy-epic') / 'status.json').is_file()
