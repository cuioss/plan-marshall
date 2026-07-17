#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the marshall-orchestrator scaffolding script (D7).

Covers the three-verb surface of ``orchestrator.py`` under ``PLAN_BASE_DIR``
isolation (via ``plan_context``):

- ``scaffold``: directory-tree creation and idempotency.
- ``queue``: read and transition round-trip against a fixture status.json,
  plus the error envelopes (missing status, unknown plan, unpaired flags).
- ``resume-summary``: START-HERE block generation derived purely from
  status.json (resume anchor, phase, running/parked plans, ordered queue).
- CLI boundary: all three verbs driven through the ``orchestrator.py`` entry
  point with constructed argv at the subprocess boundary (``run_script``).
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'marshall-orchestrator', 'orchestrator.py')

_orch = load_script_module(
    'plan-marshall', 'marshall-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

cmd_scaffold = _orch.cmd_scaffold
cmd_queue = _orch.cmd_queue
cmd_resume_summary = _orch.cmd_resume_summary
EPIC_SUBDIRS = _orch.EPIC_SUBDIRS

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'


def _epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _make_plan(
    plan_id: str,
    status: str = 'staged',
    workstream: str = 'WS-01',
    plan_marshall_plan_id: str = '',
    pr: str = '',
    landing: str = '',
) -> dict:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': workstream,
        'status': status,
        'plan_marshall_plan_id': plan_marshall_plan_id,
        'pr': pr,
        'landing': landing,
    }


def _write_status(
    plan_context,
    slug: str,
    plans: list | None = None,
    phase: str = 'orchestrating',
    resume_anchor: str = 'await PR #912 CI, then analyze landing',
) -> Path:
    """Write a kind=orchestrator fixture status.json into the isolated store."""
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Epic',
        'phase': phase,
        'workstreams': ['WS-01'],
        'plans': plans if plans is not None else [],
        'resume_anchor': resume_anchor,
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context, slug) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _read_status_file(path: Path) -> dict:
    return dict(json.loads(path.read_text(encoding='utf-8')))


# =============================================================================
# scaffold
# =============================================================================


class TestScaffold:
    def test_should_create_epic_directory_tree(self, plan_context):
        result = cmd_scaffold(Namespace(slug='fresh-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'scaffold'
        assert result['already_existed'] is False
        root = _epic_dir(plan_context, 'fresh-epic')
        assert result['root'] == str(root)
        assert root.is_dir()
        for sub in ('workstreams', 'plans', 'landings', 'logs'):
            assert (root / sub).is_dir()

    def test_should_report_all_layout_subdirs(self, plan_context):
        result = cmd_scaffold(Namespace(slug='layout-epic'))

        assert sorted(result['directories']) == sorted(EPIC_SUBDIRS)
        assert set(EPIC_SUBDIRS) == {'workstreams', 'plans', 'landings', 'logs'}

    def test_should_be_idempotent_on_rerun(self, plan_context):
        cmd_scaffold(Namespace(slug='rerun-epic'))
        marker = _epic_dir(plan_context, 'rerun-epic') / 'plans' / 'PLAN-01-keep.md'
        marker.write_text('kept', encoding='utf-8')

        result = cmd_scaffold(Namespace(slug='rerun-epic'))

        assert result['status'] == 'success'
        assert result['already_existed'] is True
        assert marker.read_text(encoding='utf-8') == 'kept'

    def test_should_not_create_status_json(self, plan_context):
        cmd_scaffold(Namespace(slug='no-status-epic'))

        assert not (_epic_dir(plan_context, 'no-status-epic') / 'status.json').exists()

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_scaffold(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'
        assert not (plan_context.fixture_dir / 'evil').exists()

    def test_should_reject_empty_slug(self, plan_context):
        result = cmd_scaffold(Namespace(slug=''))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# queue — read
# =============================================================================


class TestQueueRead:
    def test_should_return_phase_anchor_and_plans(self, plan_context):
        plans = [_make_plan('PLAN-01'), _make_plan('PLAN-02', status='running')]
        _write_status(plan_context, 'read-epic', plans=plans)

        result = cmd_queue(Namespace(slug='read-epic', transition=None, status=None))

        assert result['status'] == 'success'
        assert result['operation'] == 'queue'
        assert result['phase'] == 'orchestrating'
        assert result['resume_anchor'] == 'await PR #912 CI, then analyze landing'
        assert result['plans'] == plans

    def test_should_error_when_status_json_missing(self, plan_context):
        cmd_scaffold(Namespace(slug='bare-epic'))

        result = cmd_queue(Namespace(slug='bare-epic', transition=None, status=None))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_queue(Namespace(slug='../evil', transition=None, status=None))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# queue — transition
# =============================================================================


class TestQueueTransition:
    def test_should_round_trip_status_transition(self, plan_context):
        status_path = _write_status(
            plan_context, 'flow-epic', plans=[_make_plan('PLAN-01'), _make_plan('PLAN-02')]
        )

        result = cmd_queue(
            Namespace(slug='flow-epic', transition='PLAN-01', status='running')
        )

        assert result['status'] == 'success'
        assert result['operation'] == 'queue-transition'
        assert result['plan'] == 'PLAN-01'
        assert result['previous_status'] == 'staged'
        assert result['new_status'] == 'running'
        on_disk = _read_status_file(status_path)
        assert on_disk['plans'][0]['status'] == 'running'
        assert on_disk['plans'][1]['status'] == 'staged'

    def test_should_stamp_updated_on_transition(self, plan_context):
        status_path = _write_status(plan_context, 'stamp-epic', plans=[_make_plan('PLAN-01')])

        cmd_queue(Namespace(slug='stamp-epic', transition='PLAN-01', status='parked'))

        assert _read_status_file(status_path)['updated'] != FIXED_TIMESTAMP

    def test_should_read_back_transitioned_state(self, plan_context):
        _write_status(plan_context, 'roundtrip-epic', plans=[_make_plan('PLAN-01')])
        cmd_queue(Namespace(slug='roundtrip-epic', transition='PLAN-01', status='landed'))

        result = cmd_queue(Namespace(slug='roundtrip-epic', transition=None, status=None))

        assert result['plans'][0]['status'] == 'landed'

    def test_should_error_for_unknown_plan_id(self, plan_context):
        _write_status(plan_context, 'miss-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(Namespace(slug='miss-epic', transition='PLAN-99', status='running'))

        assert result['status'] == 'error'
        assert result['error'] == 'plan_not_found'
        assert result['available_plans'] == ['PLAN-01']

    def test_should_require_status_with_transition(self, plan_context):
        _write_status(plan_context, 'pair-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(Namespace(slug='pair-epic', transition='PLAN-01', status=None))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_require_transition_with_status(self, plan_context):
        _write_status(plan_context, 'pair2-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(Namespace(slug='pair2-epic', transition=None, status='running'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_error_when_status_json_missing(self, plan_context):
        result = cmd_queue(
            Namespace(slug='absent-epic', transition='PLAN-01', status='running')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


# =============================================================================
# resume-summary
# =============================================================================


class TestResumeSummary:
    def test_should_render_anchor_phase_and_groups_from_status_json(self, plan_context):
        plans = [
            _make_plan('PLAN-01', status='landed', pr='#901', landing='PLAN-01.md'),
            _make_plan('PLAN-02', status='running', plan_marshall_plan_id='epic-plan-2'),
            _make_plan('PLAN-03', status='parked'),
            _make_plan('PLAN-04', workstream='WS-02'),
            _make_plan('PLAN-05'),
        ]
        _write_status(plan_context, 'summary-epic', plans=plans)

        result = cmd_resume_summary(Namespace(slug='summary-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'resume-summary'
        summary = result['summary']
        assert '**Resume anchor**: await PR #912 CI, then analyze landing' in summary
        assert '**Phase**: orchestrating' in summary
        assert '**Running**:' in summary
        assert 'PLAN-02 (WS-01) — plan=epic-plan-2' in summary
        assert '**Parked**:' in summary
        assert 'PLAN-03 (WS-01)' in summary
        assert '1. PLAN-04 (WS-02)' in summary
        assert '2. PLAN-05 (WS-01)' in summary
        assert 'PLAN-01 (WS-01)' in summary
        assert 'status: landed' in summary
        assert 'PR #901' in summary

    def test_should_render_empty_queue_marker(self, plan_context):
        _write_status(plan_context, 'empty-epic', plans=[])

        result = cmd_resume_summary(Namespace(slug='empty-epic'))

        assert '**Queue** (staged, in order):' in result['summary']
        assert '- (empty)' in result['summary']

    def test_should_render_placeholder_for_unset_anchor(self, plan_context):
        _write_status(plan_context, 'anchorless-epic', resume_anchor='')

        result = cmd_resume_summary(Namespace(slug='anchorless-epic'))

        assert '**Resume anchor**: (not set)' in result['summary']

    def test_should_error_when_status_json_missing(self, plan_context):
        result = cmd_resume_summary(Namespace(slug='absent-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_resume_summary(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# CLI boundary (constructed argv at the subprocess boundary)
# =============================================================================


class TestCli:
    def test_should_scaffold_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(SCRIPT_PATH, 'scaffold', '--slug', 'cli-epic', env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'already_existed: false' in result.stdout
        for sub in ('workstreams', 'plans', 'landings', 'logs'):
            assert (_epic_dir(plan_context, 'cli-epic') / sub).is_dir()

    def test_should_transition_and_read_queue_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, 'cli-queue-epic', plans=[_make_plan('PLAN-01')])

        transition = run_script(
            SCRIPT_PATH,
            'queue',
            '--slug',
            'cli-queue-epic',
            '--transition',
            'PLAN-01',
            '--status',
            'running',
            env_overrides=env,
        )
        read = run_script(SCRIPT_PATH, 'queue', '--slug', 'cli-queue-epic', env_overrides=env)

        assert transition.returncode == 0
        assert 'previous_status: staged' in transition.stdout
        assert 'new_status: running' in transition.stdout
        assert read.returncode == 0
        assert 'running' in read.stdout

    def test_should_generate_resume_summary_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, 'cli-summary-epic', plans=[_make_plan('PLAN-01')])

        result = run_script(SCRIPT_PATH, 'resume-summary', '--slug', 'cli-summary-epic', env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'summary:' in result.stdout
        assert 'PLAN-01' in result.stdout

    def test_should_reject_unknown_subcommand(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(SCRIPT_PATH, 'launch', '--slug', 'cli-epic', env_overrides=env)

        assert result.returncode == 2
