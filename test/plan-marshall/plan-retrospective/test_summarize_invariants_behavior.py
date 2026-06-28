# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``summarize-invariants.py``.

The sibling ``test_summarize_invariants.py`` drives ``cmd_run`` through the
``run_script`` subprocess harness and covers ``expected_invariants`` with
direct calls. This module adds IN-PROCESS coverage for the orchestration
``cmd_run`` (missing-invariant findings, drift findings, the no-handshakes
warning path) and the parsing/projection/drift helpers that the subprocess
path exercises but never counts for coverage — driving each against crafted
``handshakes.toon`` / ``status.json`` files under ``tmp_path`` and asserting
the structured verdict.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import write_handshakes  # noqa: E402

_si = load_script_module(
    'plan-marshall', 'plan-retrospective', 'summarize-invariants.py', 'si_behavior_mod'
)


def _full_row(phase: str, **overrides) -> dict:
    """Return a fully-populated handshake row for ``phase``.

    Every core invariant carries a value so the only gaps a test sees are the
    ones it deliberately blanks via ``overrides``.
    """
    row = {
        'phase': phase,
        'captured_at': '2026-04-17T10:00:00Z',
        'override': False,
        'override_reason': '',
        'main_sha': 'sha-main',
        'main_dirty': '0',
        'task_state_hash': 'tsh',
        'qgate_open_count': '0',
        'config_hash': 'cfg',
        'unfinished_tasks_count': '0',
        'phase_steps_complete': 'pstep',
    }
    row.update(overrides)
    return row


def _run_args(plan_dir: Path) -> Namespace:
    return Namespace(
        command='run',
        plan_id=None,
        archived_plan_path=str(plan_dir),
        mode='archived',
    )


class TestResolvePlanDir:
    def test_live_without_plan_id_raises(self):
        with pytest.raises(ValueError, match='--plan-id is required'):
            _si.resolve_plan_dir('live', None, None)

    def test_archived_without_path_raises(self):
        with pytest.raises(ValueError, match='--archived-plan-path is required'):
            _si.resolve_plan_dir('archived', None, None)

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match='Unknown mode'):
            _si.resolve_plan_dir('weird', 'p', None)


class TestPhaseAtOrAfterExecute:
    def test_none_phase_is_false(self):
        assert _si._phase_at_or_after_execute(None) is False

    def test_phase_below_execute_is_false(self):
        assert _si._phase_at_or_after_execute('3-outline') is False

    def test_phase_at_execute_is_true(self):
        assert _si._phase_at_or_after_execute('5-execute') is True

    def test_phase_after_execute_is_true(self):
        assert _si._phase_at_or_after_execute('6-finalize') is True

    def test_unparseable_prefix_is_false(self):
        assert _si._phase_at_or_after_execute('refine-now') is False


class TestPhaseStepsCompleteApplies:
    def test_nonexistent_phase_returns_false(self):
        assert _si._phase_steps_complete_applies('phase-does-not-exist-xyz') is False

    def test_finalize_phase_with_required_steps_returns_true(self):
        # phase-6-finalize ships a standards/required-steps.md, so the phase
        # opts in to phase_steps_complete tracking.
        assert _si._phase_steps_complete_applies('6-finalize') is True


class TestLoadStatusMetadata:
    def test_missing_status_returns_empty(self, tmp_path):
        assert _si.load_status_metadata(tmp_path) == {}

    def test_malformed_status_returns_empty(self, tmp_path):
        (tmp_path / 'status.json').write_text('{ broken', encoding='utf-8')
        assert _si.load_status_metadata(tmp_path) == {}

    def test_status_without_metadata_returns_empty(self, tmp_path):
        (tmp_path / 'status.json').write_text(json.dumps({'title': 'x'}), encoding='utf-8')
        assert _si.load_status_metadata(tmp_path) == {}

    def test_metadata_returned(self, tmp_path):
        (tmp_path / 'status.json').write_text(
            json.dumps({'metadata': {'worktree_path': '/wt'}}), encoding='utf-8'
        )
        assert _si.load_status_metadata(tmp_path) == {'worktree_path': '/wt'}


class TestLoadHandshakeRows:
    def test_absent_file_returns_none(self, tmp_path):
        assert _si.load_handshake_rows(tmp_path) is None

    def test_missing_handshakes_key_returns_empty_list(self, tmp_path):
        (tmp_path / 'handshakes.toon').write_text('plan_id: demo\n', encoding='utf-8')
        assert _si.load_handshake_rows(tmp_path) == []

    def test_scalar_handshakes_value_returns_empty_list(self, tmp_path):
        # A non-list ``handshakes`` value is defensively coerced to [].
        (tmp_path / 'handshakes.toon').write_text(
            'plan_id: demo\nhandshakes: notalist\n', encoding='utf-8'
        )
        assert _si.load_handshake_rows(tmp_path) == []

    def test_valid_rows_parsed(self, tmp_path):
        write_handshakes(tmp_path, 'demo', [_full_row('1-init')])
        rows = _si.load_handshake_rows(tmp_path)
        assert isinstance(rows, list)
        assert rows[0]['phase'] == '1-init'


class TestProjectRowsToPhaseMap:
    def test_strips_metadata_and_drops_empty(self):
        rows = [
            {
                'phase': '1-init',
                'captured_at': 'ts',
                'override': False,
                'override_reason': '',
                'main_sha': 'abc',
                'config_hash': '',
            }
        ]
        phase_map = _si.project_rows_to_phase_map(rows)
        assert phase_map == {'1-init': {'main_sha': 'abc'}}

    def test_rows_without_phase_skipped(self):
        rows = [{'phase': '', 'main_sha': 'abc'}, {'main_sha': 'def'}]
        assert _si.project_rows_to_phase_map(rows) == {}


class TestDetectDrift:
    def test_single_phase_yields_no_drift(self):
        phase_map = {'1-init': {'main_sha': 'abc'}}
        assert _si.detect_drift(phase_map) == []

    def test_main_sha_change_is_drift(self):
        phase_map = {
            '1-init': {'main_sha': 'abc', 'config_hash': 'cfg'},
            '6-finalize': {'main_sha': 'xyz', 'config_hash': 'cfg'},
        }
        drift = _si.detect_drift(phase_map)
        assert any(d['invariant'] == 'main_sha' for d in drift)
        # config_hash held steady → no drift entry for it.
        assert not any(d['invariant'] == 'config_hash' for d in drift)

    def test_excluded_invariants_never_drift(self):
        phase_map = {
            '1-init': {'main_dirty': '0', 'qgate_open_count': '0', 'unfinished_tasks_count': '5'},
            '6-finalize': {'main_dirty': '1', 'qgate_open_count': '3', 'unfinished_tasks_count': '0'},
        }
        assert _si.detect_drift(phase_map) == []


class TestCmdRunInProcess:
    def test_no_handshakes_emits_canonical_warning(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()

        result = _si.cmd_run(_run_args(plan_dir))

        assert result['status'] == 'success'
        assert result['phases'] == []
        assert any(f['message'] == 'No handshakes.toon found' for f in result['findings'])

    def test_missing_core_invariant_flagged_per_phase(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        rows = [
            _full_row('1-init'),
            _full_row('2-refine', config_hash=''),  # blank → reported as missing
        ]
        write_handshakes(plan_dir, 'plan', rows)

        result = _si.cmd_run(_run_args(plan_dir))

        refine = next(p for p in result['phases'] if p['phase'] == '2-refine')
        assert 'config_hash' in refine['invariants_missing']
        assert any(
            f['invariant'] == 'config_hash' and f['severity'] == 'error'
            for f in result['findings']
        )

    def test_drift_surfaced_as_warning_finding(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        rows = [
            _full_row('1-init', main_sha='sha-a'),
            _full_row('2-refine', main_sha='sha-b'),
        ]
        write_handshakes(plan_dir, 'plan', rows)

        result = _si.cmd_run(_run_args(plan_dir))

        assert any(d['invariant'] == 'main_sha' for d in result['drift'])
        assert any(
            f['severity'] == 'warning' and 'drift' in f['message']
            for f in result['findings']
        )

    def test_fully_populated_plan_has_no_missing_findings(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        rows = [_full_row('1-init'), _full_row('6-finalize')]
        write_handshakes(plan_dir, 'plan', rows)

        result = _si.cmd_run(_run_args(plan_dir))

        assert result['aspect'] == 'invariant_summary'
        assert not any(f['severity'] == 'error' for f in result['findings'])
