#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for _marshalld_journal (retention/GC, restart replay, ETA history).

Every test isolates the machine-global home via PLAN_MARSHALL_HOME -> tmp_path,
so no test touches the real ~/.plan-marshall/marshalld/journal/ tree.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _marshalld_journal as journal_mod  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


def test_record_spec_and_get(home):
    journal = journal_mod.Journal()
    journal.record_spec('job1', {'command': ['python3', 'x', 'a:b:c']})

    entry = journal.get('job1')

    assert entry is not None
    assert entry['job_id'] == 'job1'
    assert entry['status'] == 'queued'
    assert entry['result'] is None


def test_get_missing_returns_none(home):
    assert journal_mod.Journal().get('nope') is None


def test_record_status_transition(home):
    journal = journal_mod.Journal()
    journal.record_spec('job1', {'command': []})

    journal.record_status('job1', 'running')

    assert journal.get('job1')['status'] == 'running'


def test_record_result_sets_terminal_status(home):
    journal = journal_mod.Journal()
    journal.record_spec('job1', {'command': []})

    journal.record_result('job1', {'status': 'success', 'exit_code': 0})

    entry = journal.get('job1')
    assert entry['status'] == 'success'
    assert entry['result']['exit_code'] == 0


def test_gc_removes_expired_terminal_entries(home):
    journal = journal_mod.Journal(retention_seconds=3600)
    journal.record_spec('job1', {'command': []})
    journal.record_result('job1', {'status': 'success'})

    # GC as if far in the future -> the terminal entry is past retention.
    removed = journal.gc(now=time.time() + 10_000)

    assert 'job1' in removed
    assert journal.get('job1') is None


def test_gc_keeps_nonterminal_entries(home):
    journal = journal_mod.Journal(retention_seconds=0)
    journal.record_spec('job1', {'command': []}, status='running')

    removed = journal.gc(now=time.time() + 10_000)

    assert removed == []
    assert journal.get('job1') is not None


def test_replay_on_restart_marks_inflight_killed(home):
    journal = journal_mod.Journal()
    journal.record_spec('queued-job', {'command': []}, status='queued')
    journal.record_spec('running-job', {'command': []}, status='running')
    journal.record_spec('done-job', {'command': []})
    journal.record_result('done-job', {'status': 'success'})

    killed = journal.replay_on_restart()

    assert set(killed) == {'queued-job', 'running-job'}
    assert journal.get('queued-job')['status'] == 'killed'
    assert journal.get('running-job')['result']['status'] == 'killed'
    # Terminal results survive untouched.
    assert journal.get('done-job')['status'] == 'success'


def test_eta_history_mean(home):
    journal = journal_mod.Journal()
    journal.record_duration('maven:verify', 10.0)
    journal.record_duration('maven:verify', 20.0)
    journal.record_duration('maven:verify', 30.0)

    assert journal.estimate_eta('maven:verify') == 20.0


def test_eta_missing_key_returns_none(home):
    assert journal_mod.Journal().estimate_eta('unknown') is None


def test_eta_history_bounded_to_recent_samples(home):
    journal = journal_mod.Journal(eta_samples=3)
    for value in (100.0, 100.0, 1.0, 2.0, 3.0):
        journal.record_duration('k', value)

    # Only the last 3 samples (1, 2, 3) are retained.
    assert journal.estimate_eta('k') == 2.0


def test_journal_dir_is_0700(home):
    journal = journal_mod.Journal()
    directory = journal.ensure_dir()

    assert (directory.stat().st_mode & 0o777) == 0o700
