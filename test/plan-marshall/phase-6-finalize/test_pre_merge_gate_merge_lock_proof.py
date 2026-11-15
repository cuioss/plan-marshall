#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the merge-mutex proof ``pre_merge_gate merge`` asks before it enqueues.

The merge dispatch is the ONE site that can advance a tree to the base branch, and
until this proof existed nothing on that path asked whether the caller actually held
the cross-plan merge mutex: the only reader of ``merge_lock``'s ``admission`` result
was prose in ``branch-cleanup.md``, so a run that chained the enqueue after an
``admission: blocked`` answer still merged.

What is pinned here is NEGATIVE first: with no lock file, with the lock held by
another plan, and with a lock file that cannot be read, the injected merge runner is
never invoked and the refusal names the holder it read. The positive control is that
a lock held by the plan asking to merge dispatches exactly as before, with the same
keys, and that the invocation refusal keeps its precedence over the new check.

Isolation: every case stages an isolated ``PLAN_BASE_DIR`` — the shared main-anchored
resolver's own test override — so the gate's production reader is the code under test
and no case can consult (or contend for) the repository's real ``.plan/local/merge.lock``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'pre_merge_gate.py', 'pre_merge_gate_merge_lock_proof')

_PLAN_ID = 'lb-145-gated-plan'
_OTHER_PLAN = 'lb-144-other-plan'
_PROJECT_DIR = '/abs/worktree'
_HEAD = 'abc1234def5678'

_CLEAN_VERDICT = {'status': 'success', 'plan_id': _PLAN_ID, 'phase': '6-finalize', 'blocking_count': 0}

_BLOCKING_VERDICT = {
    'status': 'error',
    'error': 'blocking_findings_present',
    'plan_id': _PLAN_ID,
    'phase': '6-finalize',
    'blocking_count': 1,
    'blocking_types': ['sonar-issue'],
    'per_type': {'sonar-issue': 1},
    'message': 'pending_findings_blocking_count failed',
}

#: A roster that was READ and proved every required bot a participant on this head.
_PARTICIPATION_COMPLETE = {
    'status': 'success',
    'participation_complete': True,
    'roster_read': True,
    'required_bots': ['coderabbit'],
    'optional_bots': [],
    'unproven_bots': [],
    'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
}

_NO_AUTHORIZATION = {
    'status': 'success',
    'any_authorized': False,
    'any_admissible': False,
    'authorized_kinds': [],
    'admissible_kinds': [],
    'inadmissible_kinds': [],
    'lapsed_kinds': [],
}


class _Runner:
    """Recording merge-runner seam: a canned verb payload plus every call's argv."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, ci_args):
        self.calls.append(list(ci_args))
        return {'status': 'success', 'merged': True}


@pytest.fixture
def lock_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stage an isolated main-anchored ``.plan/local`` and return its merge-lock path."""
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return base / 'merge.lock'


def _stage_lock(path: Path, holder: str) -> None:
    """Stage a held lock recording ``holder`` (mirrors the lock's own atomic create)."""
    path.write_text(holder + '\n', encoding='utf-8')


def _merge(runner: _Runner, *, findings=None, findings_recorder=None, **overrides):
    """Drive ``merge`` with the head, participation and store seams stubbed.

    The gate's LOCK reader is deliberately NOT stubbed: it is the code under test,
    and the ``lock_path`` fixture points it at an isolated base.
    """

    def findings_check(_plan_id):
        if findings_recorder is not None:
            findings_recorder.append(_plan_id)
        return dict(findings or _CLEAN_VERDICT)

    kwargs = {
        'route': 'safe-merge',
        'pr_number': 42,
        'project_dir': _PROJECT_DIR,
        'strategy': 'squash',
        'findings_check': findings_check,
        'merge_runner': runner,
        'status_reader': lambda _plan_id: None,
        'head_reader': lambda _project_dir: _HEAD,
        'participation_check': lambda _plan_id, _pr, _project_dir: dict(_PARTICIPATION_COMPLETE),
        'authorization_check': lambda _plan_id, _head: dict(_NO_AUTHORIZATION),
    }
    kwargs.update(overrides)
    return gate.merge(_PLAN_ID, **kwargs)


# --------------------------------------------------------------------------- #
# The refusal — three causes, one named code, and never a dispatch
# --------------------------------------------------------------------------- #


def test_the_refusal_code_is_the_declared_constant():
    """The code the payloads carry is the one the module declares."""
    assert gate.MERGE_LOCK_NOT_HELD == 'merge_lock_not_held'


def test_an_absent_lock_file_is_refused_and_nothing_dispatches(lock_path: Path):
    """No lock file at all: the gate refuses, names ``none``, and calls no merge verb."""
    runner = _Runner()

    result = _merge(runner)

    assert runner.calls == [], f'the merge runner was invoked on an unproven mutex: {runner.calls}'
    assert result['status'] == 'error'
    assert result['error'] == 'merge_lock_not_held'
    assert result['plan_id'] == _PLAN_ID
    assert result['holder'] == 'none'
    assert result['dispatched'] is False
    assert 'merge_lock acquire' in result['remedy']
    assert 'admission' in result['remedy']


def test_a_lock_held_by_another_plan_is_refused_naming_that_holder(lock_path: Path):
    """A foreign holder is named in the refusal, so the waiter knows who to wait for."""
    _stage_lock(lock_path, _OTHER_PLAN)
    runner = _Runner()

    result = _merge(runner)

    assert runner.calls == []
    assert result['error'] == 'merge_lock_not_held'
    assert result['holder'] == _OTHER_PLAN
    assert result['dispatched'] is False


def test_an_unreadable_lock_file_is_refused_rather_than_dispatched(lock_path: Path):
    """A lock path that cannot be read as a holder fails closed."""
    lock_path.mkdir()  # exists, but reading it as a holder raises
    runner = _Runner()

    result = _merge(runner)

    assert runner.calls == [], 'an unreadable lock file was read as permission to merge'
    assert result['error'] == 'merge_lock_not_held'
    assert result['holder'] == 'unreadable'
    assert result['dispatched'] is False


def test_a_lock_file_naming_no_holder_is_refused_as_unreadable(lock_path: Path):
    """A blank lock file proves no holder, so it is an unreadable proof, not a pass."""
    lock_path.write_text('', encoding='utf-8')
    runner = _Runner()

    result = _merge(runner)

    assert runner.calls == []
    assert result['error'] == 'merge_lock_not_held'
    assert result['holder'] == 'unreadable'


def test_the_check_runs_before_the_findings_store_is_read(lock_path: Path):
    """An unproven mutex is named without even the local store read."""
    runner = _Runner()
    consulted: list[str] = []

    result = _merge(runner, findings_recorder=consulted)

    assert result['error'] == 'merge_lock_not_held'
    assert consulted == [], f'the findings store was read before the mutex proof: {consulted}'


# --------------------------------------------------------------------------- #
# Order preserved — the invocation refusal still comes first
# --------------------------------------------------------------------------- #


def test_the_invocation_refusal_still_precedes_the_mutex_check(lock_path: Path):
    """A malformed call is refused as such even when the mutex is not held."""
    runner = _Runner()

    result = _merge(runner, strategy=None)

    assert runner.calls == []
    assert result['error'] == 'strategy_required'
    assert result.get('refusal_category') == 'invocation'


# --------------------------------------------------------------------------- #
# The pass — a lock held by this plan dispatches exactly as before
# --------------------------------------------------------------------------- #


def test_a_lock_held_by_this_plan_dispatches_exactly_as_before(lock_path: Path):
    """The positive control: the proof must not change the admitted payload."""
    _stage_lock(lock_path, _PLAN_ID)
    runner = _Runner()

    result = _merge(runner)

    assert runner.calls == [
        ['--project-dir', _PROJECT_DIR, 'pr', 'safe-merge', '--pr-number', '42', '--strategy', 'squash']
    ]
    assert result == {
        'status': 'success',
        'merged': True,
        'findings_gate': 'clean',
        'participation_gate': 'complete',
        'dispatched': True,
    }


def test_the_findings_gate_still_refuses_a_blocking_store_behind_a_held_mutex(lock_path: Path):
    """The store gate keeps its code once the mutex proof is satisfied."""
    _stage_lock(lock_path, _PLAN_ID)
    runner = _Runner()

    result = _merge(runner, findings=_BLOCKING_VERDICT)

    assert runner.calls == []
    assert result['error'] == 'blocking_findings_present'
    assert result['dispatched'] is False


def test_the_head_binding_still_refuses_behind_a_held_mutex(lock_path: Path):
    """The head gate keeps its code once the mutex proof is satisfied."""
    _stage_lock(lock_path, _PLAN_ID)
    runner = _Runner()

    result = _merge(
        runner,
        status_reader=_stamp_status_reader,
        head_dependence_reader=lambda _step: (True, None),
        classifier=lambda _step, _dir, _recorded: {'status': 'success', 'verdict': 'changed'},
    )

    assert runner.calls == []
    assert result['error'] == 'merge_candidate_not_gated'
    assert result['dispatched'] is False


def test_the_participation_gate_still_refuses_behind_a_held_mutex(lock_path: Path):
    """The participation gate keeps its code once the mutex proof is satisfied."""
    _stage_lock(lock_path, _PLAN_ID)
    runner = _Runner()
    unproven = dict(
        _PARTICIPATION_COMPLETE,
        participation_complete=False,
        unproven_bots=['coderabbit'],
        bot_states=[{'bot_kind': 'coderabbit', 'state': 'absent'}],
    )

    result = _merge(runner, participation_check=lambda _plan_id, _pr, _project_dir: dict(unproven))

    assert runner.calls == []
    assert result['error'] == 'merge_participation_unproven'
    assert result['dispatched'] is False


def _stamp_status_reader(_plan_id: str) -> dict:
    """A status record that stamps a DIFFERENT head, so the head binding must refuse."""
    return {
        'status': 'success',
        'plan_id': _PLAN_ID,
        'metadata': {
            'phase_steps': {
                '6-finalize': {
                    'pre-push-quality-gate': {
                        'outcome': 'done',
                        'head_at_completion': 'f' * 40,
                    }
                }
            }
        },
    }
