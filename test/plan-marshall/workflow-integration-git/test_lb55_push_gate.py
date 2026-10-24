#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-55 D1 — a push refuses a HEAD its pre-push gate never validated.

Both push verbs now consult the head the ``pre-push-quality-gate`` step recorded:
a fix commit after the gate, an amend, or a rebase produces a different HEAD, and
shipping it as "gated" is the ungated push the prose rule in
``pre-push-quality-gate.md`` never prevented.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import _push_gate as push_gate
import pytest

from conftest import load_script_module

force_push = load_script_module('plan-marshall', 'workflow-integration-git', '_cmd_force_push.py', '_lb55_force_push')

GATED = 'a' * 40
NEWER = 'b' * 40


def _status_with_gate(head: str | None) -> dict:
    record: dict = {'outcome': 'done'}
    if head:
        record['head_at_completion'] = head
    return {'metadata': {'phase_steps': {'6-finalize': {'pre-push-quality-gate': record}}}}


def test_a_fix_commit_after_the_gate_refuses_the_push():
    """The recorded head differs from the head being pushed → refusal, both SHAs named."""
    refusal = push_gate.head_gate_refusal('p', NEWER, status=_status_with_gate(GATED))

    assert refusal is not None
    assert refusal['status'] == 'error'
    assert refusal['error'] == push_gate.HEAD_NOT_GATED
    assert refusal['recorded_head'] == GATED
    assert refusal['head'] == NEWER
    assert refusal['step'] == push_gate.PRE_PUSH_GATE_STEP


def test_the_gated_head_passes():
    """⛔ MATCHED CONTROL — pushing exactly what the gate validated is not refused."""
    assert push_gate.head_gate_refusal('p', GATED, status=_status_with_gate(GATED)) is None


@pytest.mark.parametrize(
    'status',
    [None, {}, {'metadata': {}}, _status_with_gate(None)],
    ids=['no-status', 'empty', 'no-metadata', 'no-recorded-head'],
)
def test_no_recorded_head_carries_no_barrier(status):
    """Nothing validated means nothing to compare — an early-phase push still works."""
    assert push_gate.head_gate_refusal('p', NEWER, status=status) is None


def _git(root: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / 'repo'
    root.mkdir()
    _git(root, 'init', '-q', '-b', 'feature/x')
    _git(root, 'config', 'user.email', 't@t.test')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'a.txt').write_text('a\n', encoding='utf-8')
    _git(root, 'add', '.')
    _git(root, 'commit', '-q', '-m', 'A')
    return root


def test_force_push_with_lease_refuses_a_rebased_head(repo, monkeypatch):
    """The rebase path's push is this verb — a rebased head the gate never saw refuses."""
    head = _git(repo, 'rev-parse', 'HEAD')
    monkeypatch.setattr(push_gate, 'read_plan_status', lambda _pid: _status_with_gate(GATED))
    monkeypatch.setattr(force_push, '_resolve_branch_and_path', lambda _args: ('feature/x', repo, None))

    result = force_push.cmd_force_push(
        type('Args', (), {'plan_id': 'lb55-push-gate', 'project_dir': None, 'branch': None})()
    )

    assert result['status'] == 'error', f'the force-push must refuse an ungated head, got {result!r}'
    assert result.get('error_type') == push_gate.HEAD_NOT_GATED or result.get('error') == push_gate.HEAD_NOT_GATED
    assert result['head'] == head
    # Nothing reached the remote: the refusal precedes the push.
    assert 'remote_sha' not in result


def test_force_push_of_the_gated_head_proceeds_past_the_gate_check(repo, monkeypatch):
    """⛔ MATCHED CONTROL — the same tree, with the gate record matching, is not refused."""
    head = _git(repo, 'rev-parse', 'HEAD')
    monkeypatch.setattr(push_gate, 'read_plan_status', lambda _pid: _status_with_gate(head))
    monkeypatch.setattr(force_push, '_resolve_branch_and_path', lambda _args: ('feature/x', repo, None))
    calls: list[list[str]] = []

    def _fake_run_git(argv):
        calls.append(list(argv))
        if 'push' in argv:
            return 1, '', 'no remote configured'
        if argv[-1] == 'HEAD':
            return 0, f'{head}\n', ''
        return 0, 'feature/x\n', ''

    monkeypatch.setattr(force_push, 'run_git', _fake_run_git)

    result = force_push.cmd_force_push(
        type('Args', (), {'plan_id': 'lb55-push-gate-ok', 'project_dir': None, 'branch': None})()
    )

    assert result.get('error_type') != push_gate.HEAD_NOT_GATED
    assert any('push' in argv for argv in calls), 'the push must have been attempted'
