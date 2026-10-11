#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pre-merge findings gate that owns the branch-cleanup merge dispatch.

The merge verb used to be reachable without the blocking-findings check having
run: the check was an instruction the step body could skip or misread. The
entry point closes that by being the only route to the merge verb. The load-
bearing property under test is therefore NEGATIVE — on a pending actionable
finding, and on an unevaluable count, the injected merge runner is NEVER invoked —
with the positive control that a clean store reaches it exactly once, with the
routed verb's arguments unchanged, on both routes.
"""

from argparse import Namespace

import pytest

from conftest import load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'pre_merge_gate.py', 'pre_merge_gate')

# Both route-parametrized refusal tests bind gate.ROUTES; an empty route set would
# turn every case into a silent skip, so pin it non-empty at collection time.
assert len(gate.ROUTES) >= 1, 'pre_merge_gate.ROUTES is empty; the route-parametrized refusal tests would vanish'

_PLAN_ID = 'pre-merge-gate-plan'
_PROJECT_DIR = '/abs/worktree'

_BLOCKING_VERDICT = {
    'status': 'error',
    'error': 'blocking_findings_present',
    'plan_id': _PLAN_ID,
    'phase': '6-finalize',
    'blocking_count': 2,
    'blocking_types': ['build-error', 'sonar-issue'],
    'per_type': {'sonar-issue': 2},
    'message': 'pending_findings_blocking_count failed',
}

_QUERY_FAILED_VERDICT = {
    'status': 'error',
    'error': 'query_failed',
    'plan_id': _PLAN_ID,
    'phase': '6-finalize',
    'message': 'pending_findings_blocking_count could not be evaluated',
}

_CLEAN_VERDICT = {'status': 'success', 'plan_id': _PLAN_ID, 'phase': '6-finalize', 'blocking_count': 0}


class _Runner:
    """Recording merge-runner seam: returns a canned verb payload and logs every call."""

    def __init__(self, payload=None):
        self.calls: list[list[str]] = []
        self.payload = payload or {'status': 'success', 'merged': True}

    def __call__(self, ci_args):
        self.calls.append(list(ci_args))
        return dict(self.payload)


def _merge(verdict, runner, *, route='safe-merge', **flags):
    if route == 'safe-merge':
        flags.setdefault('strategy', 'squash')
    return gate.merge(
        _PLAN_ID,
        route=route,
        pr_number=42,
        project_dir=_PROJECT_DIR,
        findings_check=lambda _plan_id: dict(verdict),
        merge_runner=runner,
        **flags,
    )


# --------------------------------------------------------------------------- #
# The gate refuses — the merge runner is never reached
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize('route', gate.ROUTES)
def test_pending_actionable_finding_blocks_the_merge(route):
    """A pending actionable finding returns the refusal verbatim and merges nothing."""
    runner = _Runner()

    result = _merge(_BLOCKING_VERDICT, runner, route=route)

    assert runner.calls == [], f'the merge runner was invoked on a blocked store: {runner.calls}'
    assert result['dispatched'] is False
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    for key in ('blocking_count', 'blocking_types', 'per_type', 'message'):
        assert result[key] == _BLOCKING_VERDICT[key]
    assert 'findings_gate' not in result


@pytest.mark.parametrize('route', gate.ROUTES)
def test_unevaluable_count_fails_closed(route):
    """An unevaluable pending count is ``query_failed`` and merges nothing."""
    runner = _Runner()

    result = _merge(_QUERY_FAILED_VERDICT, runner, route=route)

    assert runner.calls == [], f'the merge runner was invoked on an unevaluable store: {runner.calls}'
    assert result['dispatched'] is False
    assert result['error'] == 'query_failed'
    assert result['message'] == _QUERY_FAILED_VERDICT['message']


def test_success_without_a_measured_zero_is_not_a_clean_store():
    """A success envelope missing ``blocking_count: 0`` fails closed, never reads as clean."""
    runner = _Runner()

    result = _merge({'status': 'success', 'plan_id': _PLAN_ID, 'phase': '6-finalize'}, runner)

    assert runner.calls == []
    assert result['dispatched'] is False
    assert result['error'] == 'findings_verdict_unrecognised'


# --------------------------------------------------------------------------- #
# The gate passes — exactly one routed dispatch, arguments unchanged
# --------------------------------------------------------------------------- #


def test_clean_store_dispatches_safe_merge_once_with_its_arguments():
    """A clean store reaches ``ci pr safe-merge`` exactly once, flags forwarded verbatim."""
    runner = _Runner({'status': 'success', 'merged': True, 'strategy': 'squash'})

    result = _merge(
        _CLEAN_VERDICT,
        runner,
        route='safe-merge',
        strategy='squash',
        delete_branch=True,
        admin_merge_on_stuck_state=True,
    )

    assert runner.calls == [
        [
            '--project-dir',
            _PROJECT_DIR,
            'pr',
            'safe-merge',
            '--pr-number',
            '42',
            '--strategy',
            'squash',
            '--delete-branch',
            '--admin-merge-on-stuck-state',
        ]
    ]
    assert result == {
        'status': 'success',
        'merged': True,
        'strategy': 'squash',
        'findings_gate': 'clean',
        'dispatched': True,
    }


def test_clean_store_dispatches_merge_queue_once_with_the_pr_number_alone():
    """A clean store reaches ``ci pr merge-queue`` exactly once, PR number only."""
    runner = _Runner({'status': 'success', 'enqueued': True})

    result = _merge(_CLEAN_VERDICT, runner, route='merge-queue')

    assert runner.calls == [['--project-dir', _PROJECT_DIR, 'pr', 'merge-queue', '--pr-number', '42']]
    assert result['enqueued'] is True
    assert result['findings_gate'] == 'clean'
    assert result['dispatched'] is True


def test_plan_id_is_never_forwarded_to_the_ci_router():
    """The merge verbs stay plan-agnostic: ``--plan-id`` scopes the findings check only."""
    runner = _Runner()

    _merge(_CLEAN_VERDICT, runner, route='safe-merge')

    assert len(runner.calls) == 1
    assert '--plan-id' not in runner.calls[0]
    assert _PLAN_ID not in runner.calls[0]


# --------------------------------------------------------------------------- #
# Verdict source and invocation shape
# --------------------------------------------------------------------------- #


def test_default_findings_check_is_the_findings_check_handler_at_6_finalize(monkeypatch):
    """The default verdict source is the ``findings-check`` handler, called for ``6-finalize``."""
    seen: list[Namespace] = []

    def fake_handler(args):
        seen.append(args)
        return dict(_BLOCKING_VERDICT)

    monkeypatch.setattr(gate, 'cmd_findings_check', fake_handler)
    runner = _Runner()

    result = gate.merge(
        _PLAN_ID,
        route='merge-queue',
        pr_number=7,
        project_dir=_PROJECT_DIR,
        merge_runner=runner,
    )

    assert [(a.plan_id, a.phase) for a in seen] == [(_PLAN_ID, '6-finalize')]
    assert runner.calls == []
    assert result['error'] == 'blocking_findings_present'


def test_safe_merge_route_requires_a_strategy_before_anything_runs():
    """A safe-merge call without ``--strategy`` is refused before the check or the merge."""
    checks: list[str] = []
    runner = _Runner()

    result = gate.merge(
        _PLAN_ID,
        route='safe-merge',
        pr_number=42,
        project_dir=_PROJECT_DIR,
        findings_check=lambda plan_id: checks.append(plan_id) or dict(_CLEAN_VERDICT),
        merge_runner=runner,
    )

    assert checks == []
    assert runner.calls == []
    assert result['error'] == 'strategy_required'
    assert result['dispatched'] is False


@pytest.mark.parametrize(
    'flags',
    [{'strategy': 'squash'}, {'delete_branch': True}, {'admin_merge_on_stuck_state': True}],
    ids=['strategy', 'delete-branch', 'admin-merge-on-stuck-state'],
)
def test_safe_merge_only_flags_are_refused_on_the_merge_queue_route(flags):
    """The enqueue takes the PR number alone; a safe-merge flag there is refused, not dropped."""
    runner = _Runner()

    result = _merge(_CLEAN_VERDICT, runner, route='merge-queue', **flags)

    assert runner.calls == []
    assert result['error'] == 'flag_not_applicable_to_route'
    assert result['dispatched'] is False


def test_route_choices_are_exactly_the_closed_dispatch_set():
    """``--route`` admits exactly the two merge verbs branch-cleanup may reach."""
    parser = gate.build_parser()
    merge_parser = parser._subparsers._group_actions[0].choices['merge']
    route_action = next(action for action in merge_parser._actions if action.dest == 'route')

    assert set(route_action.choices) == {'safe-merge', 'merge-queue'}


@pytest.mark.parametrize('forbidden', ['merge', 'auto-merge'])
def test_cli_rejects_a_forbidden_merge_verb_as_route(forbidden, monkeypatch):
    """``ci pr merge`` / ``ci pr auto-merge`` are unreachable: argparse rejects the route."""
    monkeypatch.setattr(
        'sys.argv',
        [
            'pre_merge_gate.py',
            'merge',
            '--plan-id',
            _PLAN_ID,
            '--pr-number',
            '42',
            '--route',
            forbidden,
            '--project-dir',
            _PROJECT_DIR,
        ],
    )

    with pytest.raises(SystemExit) as exc:
        gate.main()

    assert exc.value.code == 2
