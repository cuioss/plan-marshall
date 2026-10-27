#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-93 D5 — a push must not slip past an armed auto-merge / merge queue.

An armed auto-merge (``gh pr merge --auto``) or a merge-queue entry is bound to the
HEAD it was armed for. PLAN-LB-50's auto-merge, armed for ``f4ca42ab``, merged a
force-pushed ``779b035ab`` 89 s later, and nothing in the push path refused the
push that moved the head. The push verbs now refuse while the arm holds, so the
armed entry can only ever see the HEAD it was armed for; the caller disarms,
pushes, and re-arms.

Only a POSITIVE observation refuses: ``in_queue`` / ``auto_merge_armed`` must be
literally ``True``. ``False`` means the read said no and ``indeterminate`` means it
could not answer — neither is evidence of an armed merge.
"""

from __future__ import annotations

import sys
from pathlib import Path

import _push_gate as push_gate
import pytest


@pytest.mark.parametrize(
    ('state', 'expected_condition'),
    [
        ({'pr_number': '7', 'in_queue': True, 'queue_position': 2}, 'in_queue'),
        ({'pr_number': '7', 'in_queue': False, 'auto_merge_armed': True}, 'auto_merge_armed'),
    ],
    ids=['in-merge-queue', 'auto-merge-armed'],
)
def test_an_armed_merge_is_a_positive_observation(state, expected_condition):
    """Both arming forms refuse, and the payload names which one held."""
    verdict = push_gate.evaluate_merge_arm_state(state)

    assert verdict is not None
    assert verdict[0] == expected_condition


@pytest.mark.parametrize(
    'state',
    [
        {'pr_number': '7', 'in_queue': False, 'auto_merge_armed': False},
        {'pr_number': '7', 'in_queue': 'indeterminate', 'auto_merge_armed': 'indeterminate'},
        {'pr_number': '7'},
        {},
    ],
    ids=['both-false', 'indeterminate', 'fields-absent', 'empty-read'],
)
def test_nothing_but_a_positive_observation_refuses(state):
    """⛔ MATCHED CONTROL — a negative or unreadable state never blocks a push."""
    assert push_gate.evaluate_merge_arm_state(state) is None


def test_the_refusal_carries_the_code_the_remedy_and_the_pr(monkeypatch):
    """The refusal names the PR, the condition, and how to proceed."""
    monkeypatch.setattr(
        push_gate,
        'read_merge_arm_state',
        lambda branch, project_dir=None: {'pr_number': '4711', 'in_queue': False, 'auto_merge_armed': True},
    )

    refusal = push_gate.armed_merge_refusal('feature/x')

    assert refusal is not None
    assert refusal['status'] == 'error'
    assert refusal['error'] == push_gate.ARMED_MERGE_REFUSAL
    assert refusal['condition'] == 'auto_merge_armed'
    assert refusal['pr_number'] == '4711'
    assert refusal['pushed'] is False
    assert 'Disable auto-merge' in refusal['message']


def test_the_reads_are_pinned_to_the_pushed_checkout(monkeypatch):
    """The gate hands the pushed worktree to the arm read, never the caller's cwd."""
    seen: list[str | None] = []

    def _reader(branch: str, project_dir: str | None = None) -> dict:
        seen.append(project_dir)
        return {}

    monkeypatch.setattr(push_gate, 'read_merge_arm_state', _reader)

    push_gate.armed_merge_refusal('feature/x', '/checkouts/worktree-a')

    assert seen == ['/checkouts/worktree-a']


def test_an_unreadable_arm_state_does_not_block(monkeypatch):
    """No PR, an unreadable PR, or a provider without the verbs is not an armed merge."""
    monkeypatch.setattr(push_gate, 'read_merge_arm_state', lambda branch, project_dir=None: {})

    assert push_gate.armed_merge_refusal('feature/x') is None


def test_the_push_verb_refuses_before_shipping_a_new_head(monkeypatch):
    """The wiring: ``git push`` is never reached while the arm holds.

    The stub is ``read_merge_arm_state`` (not the refusal itself), so the test
    exercises the real refusal AND proves ``cmd_push`` supplies the branch it read.
    The state is armed only for the branch the push would ship.
    """
    git_workflow = _load_git_workflow()
    ran: list[list[str]] = []

    def _fake_git(args, **kwargs):
        ran.append(list(args))
        if 'rev-parse' in args:
            return 0, 'c' * 40 + '\n', ''
        if 'symbolic-ref' in args:
            return 0, 'feature/x\n', ''
        return 0, '', ''

    def _armed_for_feature_x(branch: str, project_dir: str | None = None) -> dict:
        if branch == 'feature/x':
            return {'pr_number': '7', 'in_queue': False, 'auto_merge_armed': True}
        return {}

    monkeypatch.setattr(git_workflow, '_resolve_analyze_diff_path', lambda args: (Path('/repo'), None))
    monkeypatch.setattr(git_workflow, '_run_git_nul_verbatim', _fake_git)
    monkeypatch.setattr(push_gate, 'head_gate_refusal', lambda plan_id, head, **kwargs: None)
    monkeypatch.setattr(push_gate, 'read_merge_arm_state', _armed_for_feature_x)
    # `cmd_push` imports the gate lazily; pin the module registry to THIS copy so the
    # stub is the one the verb resolves, whatever the loader did to sys.path.
    monkeypatch.setitem(sys.modules, '_push_gate', push_gate)

    result = git_workflow.cmd_push(_push_args())

    assert result['status'] == 'error'
    assert result['error'] == push_gate.ARMED_MERGE_REFUSAL
    assert result['condition'] == 'auto_merge_armed'
    assert not any('push' in command for command in ran), f'git push ran while armed: {ran}'


def _load_git_workflow():
    from conftest import load_script_module

    return load_script_module('plan-marshall', 'workflow-integration-git', 'git-workflow.py', '_d5_git_workflow')


def _push_args():
    import argparse

    return argparse.Namespace(
        plan_id='p',
        worktree=None,
        project_dir=None,
        analyze_diff=None,
        message=None,
        message_file=None,
        push=False,
    )
