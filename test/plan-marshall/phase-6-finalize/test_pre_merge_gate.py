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

import re
import subprocess
import sys
from argparse import Namespace

import pytest
from _dispatch_roster import parse_roster_rows

from conftest import MARKETPLACE_ROOT, load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'pre_merge_gate.py', 'pre_merge_gate')

# Both route-parametrized refusal tests bind gate.ROUTES; an empty route set would
# turn every case into a silent skip, so pin it non-empty at collection time.
assert len(gate.ROUTES) >= 1, 'pre_merge_gate.ROUTES is empty; the route-parametrized refusal tests would vanish'

_PLAN_ID = 'pre-merge-gate-plan'
_PROJECT_DIR = '/abs/worktree'
_HEAD = 'abc1234def5678'

_CLEAN_VERDICT = {'status': 'success', 'plan_id': _PLAN_ID, 'phase': '6-finalize', 'blocking_count': 0}

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

#: A roster that was READ and proved every required bot a participant on this head.
_PARTICIPATION_COMPLETE = {
    'status': 'success',
    'participation_complete': True,
    'roster_read': True,
    'required_bots': ['coderabbit'],
    'optional_bots': ['sourcery'],
    'unproven_bots': [],
    'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
}

#: The operator's standing ruling: a quota-LIMITED required bot whose qualifying
#: review of this head is on record. ``review_completeness`` classifies current-head
#: participation above an observed refusal, so this resolves ``participated`` and
#: needs no grant of its own.
_PARTICIPATION_QUOTA_LIMITED_BUT_REVIEWED = {
    'status': 'success',
    'participation_complete': True,
    'roster_read': True,
    'required_bots': ['coderabbit'],
    'optional_bots': [],
    'unproven_bots': [],
    'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
}

#: A required bot that never reviewed any head.
_PARTICIPATION_ABSENT = {
    'status': 'success',
    'participation_complete': False,
    'roster_read': True,
    'required_bots': ['coderabbit'],
    'optional_bots': [],
    'unproven_bots': ['coderabbit'],
    'bot_states': [{'bot_kind': 'coderabbit', 'state': 'absent'}],
}

#: A required bot whose review predates the merge candidate.
_PARTICIPATION_STALE = {
    'status': 'success',
    'participation_complete': False,
    'roster_read': True,
    'required_bots': ['coderabbit'],
    'optional_bots': [],
    'unproven_bots': ['coderabbit'],
    'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated_stale'}],
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

_GRANTED_AUTHORIZATION = {
    'status': 'success',
    'any_authorized': True,
    'any_admissible': True,
    'authorized_kinds': ['barrier-ask-override'],
    'admissible_kinds': ['barrier-ask-override'],
    'inadmissible_kinds': [],
    'lapsed_kinds': [],
}

#: A ruling that exists at this head over some OTHER gap: reported, never admissible.
_WRONG_GAP_AUTHORIZATION = {
    'status': 'success',
    'any_authorized': True,
    'any_admissible': False,
    'authorized_kinds': ['pre-merge-consent'],
    'admissible_kinds': [],
    'inadmissible_kinds': ['pre-merge-consent'],
    'lapsed_kinds': [],
}


class _Seam:
    """Recording seam: returns a canned payload and logs every call's arguments."""

    def __init__(self, payload):
        self.calls: list[tuple] = []
        self.payload = payload

    def __call__(self, *args):
        self.calls.append(args)
        return dict(self.payload)


class _Runner:
    """Recording merge-runner seam: returns a canned verb payload and logs every call."""

    def __init__(self, payload=None):
        self.calls: list[list[str]] = []
        self.payload = payload or {'status': 'success', 'merged': True}

    def __call__(self, ci_args):
        self.calls.append(list(ci_args))
        return dict(self.payload)


def _merge(verdict, runner, *, route='safe-merge', participation=None, authorization=None, **flags):
    """Drive ``merge`` with the participation and head seams defaulted to a pass.

    The default head reader answers a fixed SHA and the default status reader answers
    ``None``, so a case about the FINDINGS or ROUTING logic spawns no git or status
    subprocess. A case about participation overrides ``participation`` /
    ``authorization``; a case about the head overrides ``head_reader`` itself.
    """
    if route == 'safe-merge':
        flags.setdefault('strategy', 'squash')
    flags.setdefault('head_reader', lambda _project_dir: _HEAD)
    flags.setdefault('status_reader', lambda _plan_id: None)
    flags.setdefault(
        'participation_check',
        lambda _plan_id, _pr, _project_dir: dict(participation or _PARTICIPATION_COMPLETE),
    )
    flags.setdefault('authorization_check', lambda _plan_id, _head: dict(authorization or _NO_AUTHORIZATION))
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
        'participation_gate': 'complete',
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


# --------------------------------------------------------------------------- #
# The production merge runner — the argv reaching subprocess.run
# --------------------------------------------------------------------------- #


def _patch_subprocess(monkeypatch, tmp_path, *, stdout, stderr='', returncode=0):
    """Pin the executor path and replace ``subprocess.run``; return ``(executor, calls)``."""
    executor = tmp_path / 'execute-script.py'
    calls: list[tuple[list[str], dict]] = []

    def fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(gate, 'get_executor_path', lambda: executor)
    monkeypatch.setattr(gate.subprocess, 'run', fake_run)
    return executor, calls


@pytest.mark.parametrize(
    ('route', 'flags', 'verb_args'),
    [
        ('safe-merge', {'strategy': 'rebase'}, ['--pr-number', '42', '--strategy', 'rebase']),
        ('merge-queue', {}, ['--pr-number', '42']),
    ],
    ids=['safe-merge', 'merge-queue'],
)
def test_production_runner_invokes_the_ci_router_through_the_executor(monkeypatch, tmp_path, route, flags, verb_args):
    """On a clean store the default runner runs ``ci`` through the executor with the
    router-level ``--project-dir`` ahead of the ``pr`` verb, and parses its TOON."""
    executor, calls = _patch_subprocess(monkeypatch, tmp_path, stdout='status: success\nmerged: true\n')

    result = gate.merge(
        _PLAN_ID,
        route=route,
        pr_number=42,
        project_dir=_PROJECT_DIR,
        findings_check=lambda _plan_id: dict(_CLEAN_VERDICT),
        # The head-binding AND participation seams are stubbed away: this case asserts
        # the argv the CI ROUTER receives, and each production reader spawns its own
        # subprocess (the head-binding and participation behaviour have their own cases).
        status_reader=lambda _plan_id: None,
        head_reader=lambda _dir: None,
        participation_check=lambda _plan_id, _pr, _project_dir: dict(_PARTICIPATION_COMPLETE),
        **flags,
    )

    assert calls == [
        (
            [
                sys.executable,
                str(executor),
                'plan-marshall:tools-integration-ci:ci',
                '--project-dir',
                _PROJECT_DIR,
                'pr',
                route,
                *verb_args,
            ],
            {'capture_output': True, 'text': True, 'check': False},
        )
    ]
    assert result['status'] == 'success'
    assert result['findings_gate'] == 'clean'
    assert result['dispatched'] is True


@pytest.mark.parametrize('stdout', ['', '  \n'], ids=['empty', 'whitespace-only'])
def test_production_runner_reports_a_silent_verb_as_merge_verb_no_output(monkeypatch, tmp_path, stdout):
    """A verb that printed nothing is an error payload naming its exit code and
    stderr — never parsed as a merge outcome."""
    _patch_subprocess(monkeypatch, tmp_path, stdout=stdout, stderr='router crashed\n', returncode=1)

    result = gate.merge(
        _PLAN_ID,
        route='merge-queue',
        pr_number=42,
        project_dir=_PROJECT_DIR,
        findings_check=lambda _plan_id: dict(_CLEAN_VERDICT),
        status_reader=lambda _plan_id: None,
        head_reader=lambda _dir: None,
        participation_check=lambda _plan_id, _pr, _project_dir: dict(_PARTICIPATION_COMPLETE),
    )

    assert result['status'] == 'error'
    assert result['error'] == 'merge_verb_no_output'
    assert 'exit_code=1' in result['message']
    assert 'router crashed' in result['message']
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


# --------------------------------------------------------------------------- #
# D1 — required-bot participation is proven at the merge dispatch
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize('route', gate.ROUTES)
def test_unreviewed_required_bot_is_refused_without_a_covering_grant(route):
    """A required bot that never reviewed the candidate blocks BOTH merge routes.

    The refusal is the new named code, and it carries the bots and their states so an
    operator can see WHICH reviewer is unproven rather than only that something is.
    """
    runner = _Runner()

    result = _merge(_CLEAN_VERDICT, runner, route=route, participation=_PARTICIPATION_ABSENT)

    assert runner.calls == [], f'the merge runner was invoked on an unproven participation state: {runner.calls}'
    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_PARTICIPATION_UNPROVEN
    assert result['reason'] == 'participation_unproven'
    assert result['roster_read'] is True
    assert result['unproven_bots'] == ['coderabbit']
    assert result['bot_states'] == [{'bot_kind': 'coderabbit', 'state': 'absent'}]
    assert result['dispatched'] is False
    assert result['authorization']['any_admissible'] is False


def test_unreviewed_required_bot_merges_under_a_covering_grant():
    """A HEAD-bound authorization over the barrier gap admits the merge, and says so."""
    runner = _Runner()

    result = _merge(
        _CLEAN_VERDICT,
        runner,
        participation=_PARTICIPATION_ABSENT,
        authorization=_GRANTED_AUTHORIZATION,
    )

    assert len(runner.calls) == 1
    assert result['dispatched'] is True
    assert result['participation_gate'] == 'authorized'
    assert result['merge_authorization_kind'] == 'barrier-ask-override'
    assert result['merge_authorization_gap'] == gate.REVIEW_BARRIER_GAP_CLASS
    assert result['unproven_bots'] == ['coderabbit']


def test_a_ruling_over_another_gap_does_not_admit_the_merge():
    """``any_authorized: true`` beside ``any_admissible: false`` is still a refusal.

    Several kinds are granted at earlier sites at the SAME head over a DIFFERENT gap,
    so routing on head-validity alone would admit an unproven reviewer on the strength
    of a routine consent.
    """
    runner = _Runner()

    result = _merge(
        _CLEAN_VERDICT,
        runner,
        participation=_PARTICIPATION_ABSENT,
        authorization=_WRONG_GAP_AUTHORIZATION,
    )

    assert runner.calls == []
    assert result['error'] == gate.MERGE_PARTICIPATION_UNPROVEN
    assert result['authorization']['any_authorized'] is True
    assert result['authorization']['any_admissible'] is False
    assert result['authorization']['inadmissible_kinds'] == ['pre-merge-consent']


def test_quota_limited_required_bot_with_a_qualifying_review_is_admitted():
    """The operator's standing ruling needs no grant: the predicate proves participation.

    ``review_completeness`` ranks a current-head review above the bot's later quota
    refusal, so this resolves ``participated`` — which is why the authorization seam is
    never even consulted here.
    """
    runner = _Runner()
    authorization = _Seam(_GRANTED_AUTHORIZATION)

    result = _merge(
        _CLEAN_VERDICT,
        runner,
        participation=_PARTICIPATION_QUOTA_LIMITED_BUT_REVIEWED,
        authorization_check=authorization,
    )

    assert authorization.calls == [], 'a proven participant must not need an authorization lookup'
    assert len(runner.calls) == 1
    assert result['participation_gate'] == 'complete'
    assert 'merge_authorization_kind' not in result


def test_a_review_that_predates_the_candidate_is_refused():
    """Stale participation is unproven: the tree being merged was never reviewed."""
    runner = _Runner()

    result = _merge(_CLEAN_VERDICT, runner, participation=_PARTICIPATION_STALE)

    assert runner.calls == []
    assert result['error'] == gate.MERGE_PARTICIPATION_UNPROVEN
    assert result['bot_states'] == [{'bot_kind': 'coderabbit', 'state': 'participated_stale'}]


def test_empty_roster_is_refused_and_states_that_the_roster_was_read():
    """An EMPTY roster is a decision nobody made, never a vacuously-satisfied quorum."""
    runner = _Runner()
    empty_roster = {
        'status': 'error',
        'error': 'roster_empty',
        'roster_read': True,
        'required_bots': [],
        'optional_bots': [],
        'reason': 'the roster was read and configures no REQUIRED reviewer',
    }

    result = _merge(_CLEAN_VERDICT, runner, participation=empty_roster)

    assert runner.calls == []
    assert result['error'] == gate.MERGE_PARTICIPATION_UNPROVEN
    assert result['reason'] == 'roster_empty'
    assert result['roster_read'] is True
    assert result['required_bots'] == []


def test_unreadable_roster_is_refused_and_states_that_it_was_not_read():
    """A roster nobody could read is not an empty roster and is not a pass."""
    runner = _Runner()
    unreadable = {
        'status': 'error',
        'error': 'roster_unreadable',
        'roster_read': False,
        'reason': 'the configured review-bot roster could not be read',
    }

    result = _merge(_CLEAN_VERDICT, runner, participation=unreadable)

    assert runner.calls == []
    assert result['reason'] == 'roster_unreadable'
    assert result['roster_read'] is False


def test_an_unresolvable_head_reports_that_no_authorization_was_checked():
    """With no HEAD there is no tree to bind a ruling to, and the payload says so."""
    runner = _Runner()

    result = _merge(
        _CLEAN_VERDICT,
        runner,
        participation=_PARTICIPATION_ABSENT,
        head_reader=lambda _project_dir: None,
    )

    assert runner.calls == []
    assert result['error'] == gate.MERGE_PARTICIPATION_UNPROVEN
    assert result['authorization']['checked'] is False


# --------------------------------------------------------------------------- #
# D1 — the production participation chain
# --------------------------------------------------------------------------- #


_ROSTER_PAYLOAD = {
    'status': 'success',
    'phase': '6-finalize',
    'step_id': 'plan-marshall:automatic-review',
    'params': {'required_bots': 'coderabbit', 'optional_bots': 'sourcery'},
}

_FETCH_PAYLOAD = {
    'status': 'success',
    'merge_candidate_sha_resolved': True,
    'participated_bots': [{'bot_kind': 'coderabbit', 'evidence_kind': 'review_body'}],
    'stale_participation_bots': [{'bot_kind': 'sourcery', 'evidence_kind': 'comment'}],
    'refused_bots': [],
    'unrecognised_refusal': [{'bot_kind': 'other-bot', 'layer': 'enumerative'}],
    'refused_causes': [{'bot_kind': 'other-bot', 'cause': 'size'}],
    'refused_size_caps': [{'bot_kind': 'other-bot', 'cap': '400 lines'}],
}

_PREDICATE_PAYLOAD = {
    'status': 'success',
    'participation_complete': True,
    'proves': 'participation_only',
    'unproven_bots': [],
    'bot_states': [
        {'bot_kind': 'coderabbit', 'state': 'participated'},
        {'bot_kind': 'sourcery', 'state': 'participated_stale'},
    ],
}

_PRODUCER_NOTATION = 'plan-marshall:workflow-integration-github:github_pr'


def _participation_chain(monkeypatch, responses):
    """Drive ``_check_participation`` with the verb seam replaced by ``responses``."""
    calls: list[tuple[str, list[str]]] = []

    def fake_run_verb(notation, argv, **_kwargs):
        calls.append((notation, list(argv)))
        return dict(responses[notation])

    monkeypatch.setattr(gate, '_run_verb', fake_run_verb)
    monkeypatch.setattr(gate, '_provider_pr_notation', lambda _project_dir=None: _PRODUCER_NOTATION)
    return gate._check_participation(_PLAN_ID, 42, _PROJECT_DIR), calls


def _full_chain_responses(**overrides):
    responses = {
        gate._MANIFEST_NOTATION: _ROSTER_PAYLOAD,
        _PRODUCER_NOTATION: _FETCH_PAYLOAD,
        gate._COMPLETENESS_NOTATION: _PREDICATE_PAYLOAD,
    }
    responses.update(overrides)
    return responses


def test_the_production_chain_reads_the_roster_the_producer_and_the_predicate(monkeypatch):
    """The chain is the BARRIER's, in this order, with the producer's records translated."""
    verdict, calls = _participation_chain(monkeypatch, _full_chain_responses())

    assert [notation for notation, _argv in calls] == [
        gate._MANIFEST_NOTATION,
        _PRODUCER_NOTATION,
        gate._COMPLETENESS_NOTATION,
    ]
    assert verdict['participation_complete'] is True
    assert verdict['roster_read'] is True

    roster_argv = calls[0][1]
    assert roster_argv[:2] == ['step-params', 'get']
    assert roster_argv[-2:] == ['--step-id', 'plan-marshall:automatic-review']

    producer_argv = calls[1][1]
    # The routing flags precede the verb, so the producer reads the plan's worktree; the
    # post-verb copy is the producer's own argument. Both must be present.
    assert producer_argv[:4] == ['--plan-id', _PLAN_ID, 'fetch_findings', '--pr-number']
    assert producer_argv.count('--plan-id') == 2
    assert '--required-bots' in producer_argv
    assert 'coderabbit' in producer_argv

    predicate_argv = calls[2][1]
    assert predicate_argv[0] == 'check'
    assert predicate_argv[-1] == '--triage-ran', 'the merge runs after triage, so a pending finding must block'
    # The producer emits RECORDS; the predicate consumes PAIRS. One conversion site.
    assert 'coderabbit:review_body' in predicate_argv
    assert 'sourcery:comment' in predicate_argv
    assert 'other-bot' in predicate_argv
    assert 'other-bot:size' in predicate_argv
    assert 'other-bot:400 lines' in predicate_argv


def test_the_chain_does_not_reach_the_producer_when_the_roster_is_empty(monkeypatch):
    """An empty roster is decided before any provider call: nothing to prove, nothing to read."""
    empty = dict(_ROSTER_PAYLOAD, params={'required_bots': '', 'optional_bots': ''})

    verdict, calls = _participation_chain(monkeypatch, _full_chain_responses(**{gate._MANIFEST_NOTATION: empty}))

    assert [notation for notation, _argv in calls] == [gate._MANIFEST_NOTATION]
    assert verdict['error'] == 'roster_empty'
    assert verdict['roster_read'] is True


def test_the_chain_refuses_a_producer_that_could_not_resolve_the_candidate(monkeypatch):
    """``merge_candidate_sha_resolved: false`` means the observations are about no tree."""
    unresolvable = dict(_FETCH_PAYLOAD, merge_candidate_sha_resolved=False)

    verdict, calls = _participation_chain(monkeypatch, _full_chain_responses(**{_PRODUCER_NOTATION: unresolvable}))

    assert [notation for notation, _argv in calls] == [gate._MANIFEST_NOTATION, _PRODUCER_NOTATION]
    assert verdict['error'] == 'participation_unreadable'


def test_the_chain_refuses_a_producer_without_a_participation_arm(monkeypatch):
    """A provider that classifies nothing answers no participation question."""
    armless = {'status': 'success', 'merge_candidate_sha_resolved': True}

    verdict, _calls = _participation_chain(monkeypatch, _full_chain_responses(**{_PRODUCER_NOTATION: armless}))

    assert verdict['error'] == 'participation_arm_unavailable'


def test_the_chain_refuses_when_the_predicate_does_not_answer(monkeypatch):
    """An unknown predicate verdict is never read as complete."""
    failed = {'status': 'error', 'error': 'findings_store_unresolved'}

    verdict, _calls = _participation_chain(monkeypatch, _full_chain_responses(**{gate._COMPLETENESS_NOTATION: failed}))

    assert verdict['error'] == 'predicate_unreadable'


def test_the_chain_reads_the_provider_from_the_configured_providers_list(monkeypatch, tmp_path):
    """The producer notation is DERIVED from ``providers[]``, never a hard-coded provider."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text(
        '{"providers": [{"category": "ci", "skill_name": "plan-marshall:workflow-integration-gitlab"}]}',
        encoding='utf-8',
    )
    monkeypatch.setattr(gate, '_find_marshal_path', lambda _start=None: plan_dir / 'marshal.json')

    assert gate._provider_pr_notation() == 'plan-marshall:workflow-integration-gitlab:gitlab_pr'


def test_the_provider_resolution_is_anchored_at_the_projects_own_tree(tmp_path):
    """The walk starts at the ``--project-dir`` the merge binds to, not at the cwd.

    A dispatch whose shell sits in another checkout must resolve THAT tree's provider —
    resolving the cwd's would silently read a different project's configuration, and
    resolving nothing would refuse every merge in a correctly configured one.
    """
    project = tmp_path / 'project'
    (project / '.plan').mkdir(parents=True)
    (project / '.plan' / 'marshal.json').write_text(
        '{"providers": [{"category": "ci", "skill_name": "plan-marshall:workflow-integration-gitlab"}]}',
        encoding='utf-8',
    )

    assert gate._provider_pr_notation(str(project)) == 'plan-marshall:workflow-integration-gitlab:gitlab_pr'


def test_an_unresolvable_provider_makes_the_notation_empty(monkeypatch, tmp_path):
    """No configured provider is an empty answer, never a default provider."""
    monkeypatch.setattr(gate, '_find_marshal_path', lambda _start=None: tmp_path / 'absent.json')

    assert gate._provider_pr_notation() is None


def test_an_unknown_participation_state_is_never_authorizable():
    """A state nobody could read is NOT a review gap, so no grant admits it.

    This is the spec's standing constraint and the doc's own UNKNOWN disposition: a
    ruling covers a gap somebody can NAME. Reading an unreadable roster or a silent
    predicate like an unproven bot would let one grant recorded earlier admit a merge
    with zero participation proof — the exact fail-open the gate removes.
    """
    runner = _Runner()
    unreadable = {
        'status': 'error',
        'error': 'roster_unreadable',
        'roster_read': False,
        'reason': 'the configured review-bot roster could not be read',
    }
    authorization = _Seam(_GRANTED_AUTHORIZATION)

    result = _merge(
        _CLEAN_VERDICT,
        runner,
        participation=unreadable,
        authorization_check=authorization,
    )

    assert authorization.calls == [], 'an UNKNOWN participation state must not even consult an authorization'
    assert runner.calls == []
    assert result['error'] == gate.MERGE_PARTICIPATION_UNPROVEN
    assert result['authorizable'] is False
    assert 'No merge authorization covers this' in result['message']


def test_the_whole_participation_chain_is_unknown_authorizable_or_refused():
    """The refusal says WHICH side of the authorizable line it is on, per input."""
    refused_unknown = _merge(
        _CLEAN_VERDICT,
        _Runner(),
        participation={
            'status': 'error',
            'error': 'participation_arm_unavailable',
            'roster_read': True,
            'reason': 'the provider producer returned no participation arm',
        },
        authorization=_GRANTED_AUTHORIZATION,
    )
    refused_gap = _merge(
        _CLEAN_VERDICT,
        _Runner(),
        participation=_PARTICIPATION_ABSENT,
        authorization=_NO_AUTHORIZATION,
    )

    assert refused_unknown['authorizable'] is False
    assert refused_gap['authorizable'] is True


def test_a_comment_filed_by_the_participation_read_blocks_the_merge(monkeypatch):
    """The producer files findings, so the store gate must be re-read after it runs.

    The participation chain calls the provider producer, and that producer writes a
    ``pr-comment`` finding for every comment it has not seen. A comment that landed
    between the first store gate and that read is therefore in the store and was never
    gated — so the second read is what keeps the dispatch the latest point a pending
    finding can stop the merge.
    """
    runner = _Runner()
    verdicts = [_CLEAN_VERDICT, _BLOCKING_VERDICT]
    checks: list[str] = []

    def findings_check(plan_id):
        checks.append(plan_id)
        return dict(verdicts[min(len(checks) - 1, len(verdicts) - 1)])

    result = gate.merge(
        _PLAN_ID,
        route='safe-merge',
        pr_number=42,
        project_dir=_PROJECT_DIR,
        strategy='squash',
        findings_check=findings_check,
        merge_runner=runner,
        status_reader=lambda _plan_id: None,
        head_reader=lambda _project_dir: _HEAD,
        participation_check=lambda _plan_id, _pr, _project_dir: dict(_PARTICIPATION_COMPLETE),
    )

    assert len(checks) == 2, 'the store must be read again after the participation chain ran the producer'
    assert runner.calls == []
    assert result['error'] == 'blocking_findings_present'
    assert result['dispatched'] is False


def test_the_produce_then_re_read_order_does_not_block_a_genuinely_clean_store():
    """Positive control for the second read: two clean reads still dispatch once."""
    runner = _Runner()
    checks: list[str] = []

    def findings_check(plan_id):
        checks.append(plan_id)
        return dict(_CLEAN_VERDICT)

    result = gate.merge(
        _PLAN_ID,
        route='merge-queue',
        pr_number=42,
        project_dir=_PROJECT_DIR,
        findings_check=findings_check,
        merge_runner=runner,
        status_reader=lambda _plan_id: None,
        head_reader=lambda _project_dir: _HEAD,
        participation_check=lambda _plan_id, _pr, _project_dir: dict(_PARTICIPATION_COMPLETE),
    )

    assert len(checks) == 2
    assert len(runner.calls) == 1
    assert result['dispatched'] is True


def test_the_participation_mapping_is_the_predicates_own():
    """The quota-limited-but-reviewed case is on the predicate's ADMITTED side, by its code.

    D1's verify-first clause asks how the check tells a quota-limited required bot with a
    qualifying review apart from an unreviewed one, and which ``review_completeness``
    state members it maps to each side. Asserting that against THIS module's canned
    payload would only restate the fixture, so the mapping is read from the predicate
    itself: a current-head participation credit outranks an observed refusal, while a
    bot with no participation and a refusal resolves to an unproven member.
    """
    predicate = load_script_module(
        'plan-marshall', 'automatic-review', 'review_completeness.py', 'review_completeness_for_gate'
    )

    quota_limited_but_reviewed = predicate.classify_bot(
        'coderabbit',
        {'coderabbit': 'review_body'},
        True,
        set(),
        {'coderabbit'},
    )
    unreviewed_and_refused = predicate.classify_bot(
        'coderabbit',
        {},
        False,
        set(),
        {'coderabbit'},
    )
    never_reviewed = predicate.classify_bot('coderabbit', {}, False, set(), set())

    assert quota_limited_but_reviewed in {'participated', 'participated_but_empty'}
    assert quota_limited_but_reviewed not in predicate._UNPROVEN_STATES
    assert unreviewed_and_refused in predicate._UNPROVEN_STATES
    assert never_reviewed in predicate._UNPROVEN_STATES


# --------------------------------------------------------------------------- #
# D2 — the merge record says what was relied on
# --------------------------------------------------------------------------- #


_SKILL_STANDARDS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards'
_BRANCH_CLEANUP = _SKILL_STANDARDS / 'branch-cleanup.md'
_BRANCH_CLEANUP_REREVIEW = _SKILL_STANDARDS / 'branch-cleanup-rereview.md'
_BRANCH_CLEANUP_TEXT = _BRANCH_CLEANUP.read_text(encoding='utf-8')
_DOCS = {
    _BRANCH_CLEANUP: _BRANCH_CLEANUP_TEXT,
    _BRANCH_CLEANUP_REREVIEW: _BRANCH_CLEANUP_REREVIEW.read_text(encoding='utf-8'),
}

_ROSTER_HEADING = '## Merge-Authorization Roster'
_ROSTER_ROWS: list[tuple[str, str]] = parse_roster_rows(_BRANCH_CLEANUP_TEXT, _ROSTER_HEADING)

#: Vacuity guard — every sweep below is parametrized over a population parsed out of a
#: document, so a heading that moved would collect zero cases and report green.
assert _ROSTER_ROWS, f'no merge-authorization roster rows parsed from {_BRANCH_CLEANUP}'

_GRANT_KINDS: list[str] = [kind for kind, row in _ROSTER_ROWS if 'bound_via: grant' in row]
assert _GRANT_KINDS, 'the roster declares no grant-backed authorization kind'


_MERGE_FACTS_CLEAN = [
    'action=rebased',
    'upstream_commit_count=3',
    'merge_mechanism=pr_safe_merge',
    'merge_state=merged',
    'cleanup_owed=false',
    'work_performed=true',
]


def test_a_granted_merge_step_record_carries_the_gap():
    """The wording Branch E specifies is what the script writes."""
    written: list[list[str]] = []

    result = gate.record_merge(
        _PLAN_ID,
        facts=list(_MERGE_FACTS_CLEAN),
        grant_kind='barrier-ask-override',
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['display_detail'] == 'merged under barrier-ask-override, gap recorded'
    assert written, 'the step record was never written'
    argv = written[0]
    assert argv[:2] == ['mark-step-done', '--plan-id']
    assert argv[argv.index('--display-detail') + 1] == 'merged under barrier-ask-override, gap recorded'
    # Every fact the caller supplied reaches the writer verbatim.
    for fact in _MERGE_FACTS_CLEAN:
        assert fact in argv


def test_a_clean_merge_step_record_never_carries_the_gap():
    """The clean form is the clause composition, and it asserts no gap."""
    written: list[list[str]] = []

    result = gate.record_merge(
        _PLAN_ID,
        facts=list(_MERGE_FACTS_CLEAN),
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['display_detail'] == 'rebased onto base, merged directly, cleanup complete'
    assert 'gap recorded' not in result['display_detail']
    assert 'action=rebased' in written[0]
    assert 'upstream_commit_count=3' in written[0]


@pytest.mark.parametrize(
    ('action', 'merge_mechanism', 'expected'),
    [
        ('noop', 'pr_safe_merge', 'already current with base, merged directly, cleanup complete'),
        (None, 'merge_queue', 'rebase deferred to queue, queue-merged, corroborated, cleanup complete'),
    ],
    ids=['noop', 'queue'],
)
def test_the_clean_form_renders_both_axes_as_clauses(action, merge_mechanism, expected):
    """Neither axis is interpolated raw: the queue path never claims a rebase this step did."""
    assert gate.clean_merge_step_detail(action, merge_mechanism) == expected


def test_the_longest_admissible_grant_kind_still_fits_the_bound():
    """Every roster ``grant`` kind renders inside the declared ceiling.

    The population is DERIVED from the roster, so a kind added there is sized here
    without editing this test — and the bound is the script's own constant, which the
    doc's § "Length discipline" states.
    """
    longest = max(_GRANT_KINDS, key=len)

    rendered = gate.merge_step_detail(longest)

    assert len(rendered) <= gate.MERGE_DISPLAY_DETAIL_MAX_CHARS, (
        f'the longest admissible grant kind {longest!r} renders {len(rendered)} characters: {rendered!r}'
    )


def test_the_documented_branch_e_length_matches_the_rendered_length():
    """The doc's published worst case is the value the script actually renders."""
    match = re.search(r'`merged under barrier-ask-override, gap recorded`, \*\*(\d+) chars\*\*', _BRANCH_CLEANUP_TEXT)

    assert match is not None, 'branch-cleanup.md no longer publishes the Branch E worst-case length'
    assert len(gate.merge_step_detail('barrier-ask-override')) == int(match.group(1))


def test_the_documented_branch_e_wording_is_the_scripts_template():
    """Branch E stays the SPECIFICATION: the literal it states is the script's template."""
    assert gate.GAP_RECORDED_TEMPLATE in _BRANCH_CLEANUP_TEXT, (
        'branch-cleanup.md no longer states the gap-bearing wording, so the script would be '
        'specifying a record shape no document owns'
    )
    assert 'record-merge' in _BRANCH_CLEANUP_TEXT, (
        'branch-cleanup.md does not route Branch A/E through the verb that renders the wording'
    )


@pytest.mark.parametrize(
    ('facts', 'expected_error'),
    [
        (
            [
                'action=rebased',
                'merge_mechanism=merge_queue',
                'merge_state=merged',
                'cleanup_owed=false',
                'work_performed=true',
            ],
            'action_on_queue_route',
        ),
        (
            ['merge_mechanism=squash', 'merge_state=merged', 'cleanup_owed=false', 'work_performed=true'],
            'display_detail_invalid',
        ),
        (
            [
                'merge_mechanism=pr_safe_merge',
                'action=skipped',
                'upstream_commit_count=1',
                'merge_state=merged',
                'cleanup_owed=false',
                'work_performed=true',
            ],
            'display_detail_invalid',
        ),
        (['merge_mechanism=pr_safe_merge', 'merge_state=merged'], 'facts_incomplete'),
        (
            ['merge_mechanism=pr_safe_merge', 'merge_state=n/a', 'cleanup_owed=false', 'work_performed=true'],
            'merge_state_not_landed',
        ),
        (['merge_mechanism=pr_safe_merge', 'not-a-pair'], 'facts_malformed'),
        (
            ['merge_mechanism=pr_safe_merge', 'merge_state=merged', 'cleanup_owed=false', 'work_performed=true'],
            'action_required_on_direct_route',
        ),
        (
            [
                'merge_mechanism=pr_safe_merge',
                'action=rebased',
                'merge_state=merged',
                'cleanup_owed=false',
                'work_performed=true',
            ],
            'upstream_count_required_with_action',
        ),
    ],
    ids=[
        'action-on-queue',
        'unknown-mechanism',
        'unknown-action',
        'missing-facts',
        'not-landed',
        'malformed-fact',
        'no-action-on-direct-route',
        'action-without-upstream-count',
    ],
)
def test_record_merge_refuses_an_incoherent_record_and_writes_nothing(facts, expected_error):
    """A record asserting something the path cannot have produced is refused, not written."""
    written: list[list[str]] = []

    result = gate.record_merge(
        _PLAN_ID,
        facts=list(facts),
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert written == [], f'a refused record was still written: {written}'
    assert result['error'] == expected_error
    assert result[gate.REFUSAL_CATEGORY_FIELD] == gate.INVOCATION_REFUSAL


@pytest.mark.parametrize(
    ('facts', 'expected_error'),
    [
        (
            [
                'action=rebased',
                'upstream_commit_count=1',
                'merge_mechanism=merge_queue',
                'merge_state=merged',
                'cleanup_owed=false',
                'work_performed=true',
            ],
            'action_on_queue_route',
        ),
        (
            ['merge_mechanism=pr_safe_merge', 'merge_state=merged', 'cleanup_owed=false', 'work_performed=true'],
            'action_required_on_direct_route',
        ),
        (
            [
                'action=rebased',
                'upstream_commit_count=1',
                'merge_mechanism=squash',
                'merge_state=merged',
                'cleanup_owed=false',
                'work_performed=true',
            ],
            'display_detail_invalid',
        ),
    ],
    ids=['granted-action-on-queue', 'granted-no-action-on-direct-route', 'granted-unknown-mechanism'],
)
def test_the_route_action_rules_also_bind_the_authorized_rendering(facts, expected_error):
    """Branch E is not exempt from the coherence rules: the FACTS must be able to be true."""
    written: list[list[str]] = []

    result = gate.record_merge(
        _PLAN_ID,
        facts=list(facts),
        grant_kind='barrier-ask-override',
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert written == []
    assert result['error'] == expected_error


def test_a_granted_queue_record_is_accepted():
    """Positive control for the granted path: a coherent queue record still renders Branch E."""
    written: list[list[str]] = []

    result = gate.record_merge(
        _PLAN_ID,
        facts=[
            'merge_mechanism=merge_queue',
            'merge_state=merged',
            'cleanup_owed=false',
            'work_performed=true',
        ],
        grant_kind='barrier-ask-override',
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['display_detail'] == 'merged under barrier-ask-override, gap recorded'
    assert len(written) == 1


def test_a_rerouted_direct_merge_records_its_rebase():
    """The ``queue_wait: forbidden`` reroute merges directly WHILE the queue knob is true.

    Its record therefore carries a rebase action on a ``pr_safe_merge`` mechanism — the
    combination a naive "rebase iff use_merge_queue == false" rule would refuse.
    """
    written: list[list[str]] = []

    result = gate.record_merge(
        _PLAN_ID,
        facts=[
            'action=rebased',
            'upstream_commit_count=2',
            'merge_mechanism=pr_safe_merge',
            'merge_state=merged',
            'cleanup_owed=false',
            'work_performed=true',
        ],
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['display_detail'] == 'rebased onto base, merged directly, cleanup complete'
    assert len(written) == 1


def test_record_merge_refuses_a_grant_kind_carrying_a_control_character():
    """A multi-line kind would render a multi-line step detail inside the length bound."""
    written: list[list[str]] = []

    result = gate.record_merge(
        _PLAN_ID,
        facts=list(_MERGE_FACTS_CLEAN),
        grant_kind='barrier\nask-override',
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert written == []
    assert result['error'] == 'display_detail_invalid'


def test_record_merge_refuses_a_rendering_over_the_declared_ceiling():
    """The bound is measured on the RENDERED string, and refused at the write site."""
    written: list[list[str]] = []

    result = gate.record_merge(
        _PLAN_ID,
        facts=list(_MERGE_FACTS_CLEAN),
        grant_kind='k' * gate.MERGE_DISPLAY_DETAIL_MAX_CHARS,
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert written == []
    assert result['error'] == 'display_detail_invalid'
    assert str(gate.MERGE_DISPLAY_DETAIL_MAX_CHARS) in result['message']


# --------------------------------------------------------------------------- #
# D3 — every pre-enqueue merge question says whether a second one follows
# --------------------------------------------------------------------------- #

_MERGE_OPTION_LABELS = (
    'Merge anyway (record reason)',
    'Accept the coverage gap (record reason)',
    'Merge anyway — override red CI',
    'Merge anyway — proceed unreviewed',
)

#: The placeholder every such site must carry instead of a hand-written sentence.
_MERGE_CONSEQUENCE_PLACEHOLDER = '{merge_consequence}'


def _fenced_blocks(text):
    """Every fenced code block in ``text`` — the population a prompt block lives in."""
    return text.split('```')[1::2]


def _declaring_blocks(text, label):
    """Every fenced block that DECLARES ``label`` as an option (``label: "<label>"``).

    Declaration is what separates a render site from a mention: several bash blocks name
    these labels in decision-log message text and in ``--operator-answer`` arguments, and
    neither renders an option. Every declared block is a site, never only the first.
    """
    declaration = f'label: "{label}"'
    return [block for block in _fenced_blocks(text) if declaration in block]


def _prose_site(text, label):
    """The paragraph documenting ``label`` as a sentence rather than a composed prompt."""
    for paragraph in text.split('\n\n'):
        if label in paragraph and _MERGE_CONSEQUENCE_PLACEHOLDER in paragraph:
            return paragraph
    return None


def _sites_for(label):
    """Return ``[(path, block_or_paragraph), …]`` for every site that renders ``label``.

    The whole population, not the best match: a label rendered at two places is two
    sites, and asserting only the first would leave the second free to hand-write a
    sentence the other knob value contradicts.
    """
    sites = []
    for path, text in _DOCS.items():
        sites.extend((path, block) for block in _declaring_blocks(text, label))
    if sites:
        return sites
    for path, text in _DOCS.items():
        paragraph = _prose_site(text, label)
        if paragraph is not None:
            return [(path, paragraph)]
    return []


def test_the_corpus_never_states_either_consequence_sentence():
    """No site may hand-write either value's sentence, which is what makes the pair safe."""
    for path, text in _DOCS.items():
        assert gate.MERGE_CONSEQUENCE_WITHOUT_ASKING not in text, f'{path.name} hard-codes the without-asking sentence'
        assert gate.MERGE_CONSEQUENCE_WITH_ASKING not in text, f'{path.name} hard-codes the asking sentence'


@pytest.mark.parametrize('label', _MERGE_OPTION_LABELS)
def test_every_pre_enqueue_merge_option_renders_the_generated_sentence(label):
    """EVERY site that renders ``label`` carries the placeholder and says which outcome follows."""
    sites = _sites_for(label)

    assert sites, f'no block or paragraph in the finalize standards renders {label!r}'

    for path, context in sites:
        assert _MERGE_CONSEQUENCE_PLACEHOLDER in context, (
            f'{label!r} in {path.name} does not carry {_MERGE_CONSEQUENCE_PLACEHOLDER}, so its option '
            'text cannot be generated from the final_merge_without_asking value'
        )

        without_asking = context.replace(_MERGE_CONSEQUENCE_PLACEHOLDER, gate.merge_consequence_text(True))
        with_asking = context.replace(_MERGE_CONSEQUENCE_PLACEHOLDER, gate.merge_consequence_text(False))

        assert gate.merge_consequence_text(True) in without_asking
        assert gate.merge_consequence_text(False) in with_asking
        # Falsifiable in the direction that matters: the rendered site must NOT carry
        # the OTHER value's sentence, which is what a contradictory site looks like.
        assert gate.merge_consequence_text(False) not in without_asking
        assert gate.merge_consequence_text(True) not in with_asking


def test_the_site_census_covers_every_merge_option_label():
    """The four declared merge-option labels all resolve to at least one real site.

    A label whose site was reworded away would otherwise vanish silently: the
    per-label test above would still be parametrized over it but find nothing.
    """
    resolved = {label: len(_sites_for(label)) for label in _MERGE_OPTION_LABELS}

    assert all(count > 0 for count in resolved.values()), f'a merge-option label resolves to no site: {resolved}'


def test_the_site_detector_fires_on_a_hand_written_sentence():
    """Mutation control: a site that hard-codes the other value's text IS reported.

    Without this the corpus assertion above could pass over a document that simply
    stopped carrying the sentences for an unrelated reason.
    """
    contradictory = (
        '```text\nAskUserQuestion:\n  options:\n'
        '    - label: "Merge anyway (record reason)"\n'
        f'      description: "{gate.MERGE_CONSEQUENCE_WITH_ASKING}"\n'
        '```\n'
    )

    blocks = _declaring_blocks(contradictory, 'Merge anyway (record reason)')

    assert len(blocks) == 1, 'the declaration detector missed a real option declaration'
    assert _MERGE_CONSEQUENCE_PLACEHOLDER not in blocks[0], (
        'the fixture must omit the placeholder, or it does not model a hand-written site'
    )
    assert gate.MERGE_CONSEQUENCE_WITH_ASKING in blocks[0]


def test_the_prose_site_detector_fires_on_a_paragraph_without_the_placeholder():
    """Mutation control: the prose fallback only accepts a paragraph that HAS the placeholder."""
    with_placeholder = 'The option carries `{merge_consequence}` so the operator knows what follows.'
    without = 'The red-CI override option is offered, and then the merge proceeds.'

    assert _prose_site(with_placeholder + '\n\n' + without, 'nonexistent-label') is None
    assert _prose_site(with_placeholder, '{merge_consequence}') == with_placeholder
    assert _prose_site(without, 'red-CI override') is None, (
        'a paragraph that names a site but carries no placeholder must not be accepted as its render site'
    )


def test_the_two_consequence_sentences_state_opposite_outcomes():
    """Each sentence says what actually follows its option, and the two cannot be swapped."""
    without_asking = gate.merge_consequence_text(True)
    with_asking = gate.merge_consequence_text(False)

    assert without_asking != with_asking
    assert 'no second question' in without_asking.lower()
    assert 'confirmation' in with_asking.lower()


@pytest.mark.parametrize('value', ['true', 'false'])
def test_the_consequence_text_cli_renders_the_resolved_knob_value(value, capsys):
    """The verb answers from the value it was given, and says which one it used."""
    parser = gate.build_parser()
    args = parser.parse_args(['consequence-text', '--final-merge-without-asking', value])

    assert gate.cmd_consequence_text(args) == 0
    emitted = capsys.readouterr().out

    assert f'final_merge_without_asking: {value}' in emitted
    assert gate.merge_consequence_text(value == 'true') in emitted


def test_the_consequence_knob_flag_admits_only_the_two_declared_values():
    """A third value names no outcome, so argparse refuses it before any text is rendered."""
    parser = gate.build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(['consequence-text', '--final-merge-without-asking', 'maybe'])

    assert exc.value.code == 2
