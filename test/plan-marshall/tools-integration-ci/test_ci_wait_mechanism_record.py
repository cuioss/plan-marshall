#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Contract tests for the ``[WAIT]`` mechanism-selection record on the CI-wait arm.

The record is the evidence that answers "which wait mechanism did this wait
actually run on?" from the log alone. The load-bearing case is the **silent
degrade**: a wait that falls through to the ``poll_until`` fallback instead of
the ``gh run watch`` terminal-state tail must be distinguishable from the tail
by the record alone — that is the regression these tests exist for.

Emissions are captured by monkeypatching the module-level ``plan_logging.log_entry``
seam that :func:`ci_base.record_wait_mechanism` writes through; the handler-driving
helpers (``_ok_auth``, ``_make_incrementing_clock``) come from the shared
``_ci_wait_contract`` module.
"""

import argparse

import _github_ci
import ci_base
import github_ops
import gitlab_ops
import plan_logging
import pytest
from _ci_wait_contract import _make_incrementing_clock, _ok_auth

_PLAN_ID = 'wait-record-plan'
_PR_NUMBER = 123

_RUN_LINK = 'https://github.com/o/r/actions/runs/999/job/42'


# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture
def wait_records(monkeypatch):
    """Capture every ``[WAIT]`` record written through the plan_logging seam."""
    captured: list[tuple[str, str, str]] = []

    def fake_log_entry(log_type, plan_id, level, message):
        if message.startswith('[WAIT] '):
            captured.append((plan_id, level, message))

    monkeypatch.setattr(plan_logging, 'log_entry', fake_log_entry)
    return captured


def _parse_wait_record(message: str) -> dict[str, str]:
    """Parse a ``[WAIT] k=v k=v ...`` message into its field map."""
    assert message.startswith('[WAIT] '), message
    fields: dict[str, str] = {}
    for token in message[len('[WAIT] '):].split(' '):
        key, _sep, value = token.partition('=')
        fields[key] = value
    return fields


def _ci_wait_args(*, plan_id: str | None = _PLAN_ID, dispatch: str | None = None, timeout: int = 300):
    """Build a ``checks wait`` Namespace.

    ``dispatch=None`` omits the attribute entirely, exercising the handler's
    ``getattr(..., 'undeclared')`` default for a caller that never declared it.
    """
    namespace = argparse.Namespace(
        pr_number=_PR_NUMBER,
        timeout=timeout,
        interval=0,
        error_style='generic',
        router_plan_id=plan_id,
    )
    if dispatch is not None:
        namespace.dispatch = dispatch
    return namespace


def _check_row(state: str, *, link: str = _RUN_LINK) -> dict:
    return {'name': 'verify', 'state': state, 'bucket': '', 'link': link, 'workflow': 'ci'}


def _stub_github(monkeypatch, *, fetch_results):
    """Neutralise every network / clock / persistence seam of the GitHub handler.

    ``fetch_results`` is the sequence of check-row lists successive
    ``_fetch_pr_checks`` calls return; the last entry is reused once exhausted.
    """
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (1, '', 'no network in tests'))
    monkeypatch.setattr(_github_ci, '_read_ci_wait_p50_seed', lambda: None)
    monkeypatch.setattr(_github_ci, '_record_ci_wait_duration', lambda _duration: None)
    monkeypatch.setattr(_github_ci, '_fetch_pr_head_sha', lambda _pr: 'deadbeef')
    monkeypatch.setattr(_github_ci, '_enrich_failing_checks', lambda entries, **_kw: entries)
    monkeypatch.setattr(_github_ci, '_monotonic', _make_incrementing_clock())

    watch_calls: list[str] = []

    def fake_watch(run_id, _timeout):
        watch_calls.append(str(run_id))
        return 0, '', ''

    monkeypatch.setattr(_github_ci, '_watch_run', fake_watch)

    remaining = list(fetch_results)

    def fake_fetch(_pr_number):
        rows = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return True, {'checks': rows}

    monkeypatch.setattr(_github_ci, '_fetch_pr_checks', fake_fetch)
    return watch_calls


# =============================================================================
# (a) Happy path — the watch tail stamps mechanism=watch_tail / outcome=success
# =============================================================================


def test_watch_tail_records_mechanism_and_success_outcome(monkeypatch, wait_records):
    watch_calls = _stub_github(
        monkeypatch,
        fetch_results=[[_check_row('IN_PROGRESS')], [_check_row('SUCCESS')]],
    )

    result = _github_ci.cmd_ci_wait(_ci_wait_args(dispatch='detached'))

    assert result['status'] == 'success', result
    assert result['final_status'] == 'success'
    assert result['mechanism'] == 'watch_tail', 'the returned dict must carry the mechanism, not only the [WAIT] log'
    assert watch_calls == ['999']

    assert len(wait_records) == 1, wait_records
    plan_id, level, message = wait_records[0]
    assert plan_id == _PLAN_ID
    assert level == 'INFO'
    assert _parse_wait_record(message) == {
        'consumer': 'ci-wait',
        'mechanism': 'watch_tail',
        'dispatch': 'detached',
        'target': f'pr#{_PR_NUMBER}',
        'outcome': 'success',
    }


# =============================================================================
# (a2) seed_only — the post-seed snapshot is already terminal, so neither the
#      watch tail nor the poll fallback runs.
# =============================================================================


def test_seed_only_records_mechanism_and_success_outcome(monkeypatch, wait_records):
    """First post-seed snapshot is already terminal/successful → mechanism=seed_only.

    The third supported CI-wait mechanism: the seed sleep alone resolves the wait
    because the very first checks snapshot after it is terminal. No run is ever in
    a wait state, so the ``gh run watch`` tail never fires and the ``poll_until``
    fallback is never entered — the wait is stamped ``seed_only`` at ``INFO``.
    """
    watch_calls = _stub_github(
        monkeypatch,
        fetch_results=[[_check_row('SUCCESS')]],
    )

    result = _github_ci.cmd_ci_wait(_ci_wait_args(dispatch='detached'))

    assert result['status'] == 'success', result
    assert result['final_status'] == 'success'
    assert result['mechanism'] == 'seed_only', 'a wait resolved by the seed alone must stamp seed_only'
    assert watch_calls == [], 'neither the watch tail nor the poll fallback runs when the seed snapshot is terminal'

    assert len(wait_records) == 1, wait_records
    _plan_id, level, message = wait_records[0]
    assert level == 'INFO', 'a clean seed_only resolution is not a degrade'
    fields = _parse_wait_record(message)
    assert fields['mechanism'] == 'seed_only'
    assert fields['outcome'] == 'success'


# =============================================================================
# (b) The regression this plan exists for — a silent degrade to poll_fallback
# =============================================================================


def test_poll_fallback_degrade_is_recorded_at_warning(monkeypatch, wait_records):
    """No watchable run → the poll_until branch runs → mechanism=poll_fallback.

    Without the record this degrade is invisible: the returned TOON is byte-identical
    to a watch-tail resolution, so only the emitted mechanism distinguishes them.
    """
    watch_calls = _stub_github(
        monkeypatch,
        fetch_results=[[], [_check_row('SUCCESS')]],
    )

    result = _github_ci.cmd_ci_wait(_ci_wait_args(dispatch='inline'))

    assert result['status'] == 'success', result
    assert result['mechanism'] == 'poll_fallback', 'the returned dict must carry the mechanism, not only the [WAIT] log'
    assert watch_calls == [], 'the watch tail must not run when no run is watchable'

    assert len(wait_records) == 1, wait_records
    _plan_id, level, message = wait_records[0]
    assert level == 'WARNING', 'a degrade must be recorded at a level distinct from a clean resolution'
    fields = _parse_wait_record(message)
    assert fields['mechanism'] == 'poll_fallback'
    assert fields['dispatch'] == 'inline'
    assert fields['outcome'] == 'success'


# =============================================================================
# (c) The deadline_exceeded envelope still emits a record
# =============================================================================


def test_deadline_exceeded_envelope_still_records(monkeypatch, wait_records):
    _stub_github(
        monkeypatch,
        fetch_results=[[_check_row('IN_PROGRESS')], [_check_row('IN_PROGRESS')]],
    )

    result = _github_ci.cmd_ci_wait(_ci_wait_args(dispatch='detached'))

    assert result['wait_outcome'] == 'deadline_exceeded', result
    assert result['mechanism'] == 'watch_tail', 'the deadline_exceeded envelope must also carry the mechanism'

    assert len(wait_records) == 1, wait_records
    _plan_id, level, message = wait_records[0]
    assert level == 'WARNING'
    fields = _parse_wait_record(message)
    assert fields['mechanism'] == 'watch_tail'
    assert fields['outcome'] == 'deadline_exceeded'


# =============================================================================
# (d) Best-effort — a raising write never aborts the wait
# =============================================================================


def test_write_failure_does_not_abort_the_wait(monkeypatch):
    _stub_github(
        monkeypatch,
        fetch_results=[[_check_row('IN_PROGRESS')], [_check_row('SUCCESS')]],
    )

    def exploding_log_entry(*_a, **_kw):
        raise OSError('work log unwritable')

    monkeypatch.setattr(plan_logging, 'log_entry', exploding_log_entry)

    result = _github_ci.cmd_ci_wait(_ci_wait_args(dispatch='detached'))

    assert result['status'] == 'success', result
    assert result['final_status'] == 'success'
    assert result['wait_outcome'] == 'completed'


# =============================================================================
# (e) A falsy plan_id emits nothing — a plan-less CI call has no work log
# =============================================================================


def test_falsy_plan_id_emits_no_record(monkeypatch, wait_records):
    _stub_github(
        monkeypatch,
        fetch_results=[[_check_row('IN_PROGRESS')], [_check_row('SUCCESS')]],
    )

    result = _github_ci.cmd_ci_wait(_ci_wait_args(plan_id=None, dispatch='detached'))

    assert result['status'] == 'success', result
    assert wait_records == []


# =============================================================================
# (f) An undeclared --dispatch records `undeclared`, never a plausible default
# =============================================================================


def test_undeclared_dispatch_is_recorded_as_undeclared(monkeypatch, wait_records):
    _stub_github(
        monkeypatch,
        fetch_results=[[_check_row('IN_PROGRESS')], [_check_row('SUCCESS')]],
    )

    result = _github_ci.cmd_ci_wait(_ci_wait_args(dispatch=None))

    assert result['status'] == 'success', result
    assert len(wait_records) == 1, wait_records
    assert _parse_wait_record(wait_records[0][2])['dispatch'] == 'undeclared'


def test_checks_wait_parser_defaults_dispatch_to_undeclared():
    """The argparse default is `undeclared` — the flag itself only accepts the two declared modes."""
    parser, _pr_sub, _checks_sub, _issue_sub, _branch_sub = ci_base.build_parser('test')

    args = parser.parse_args(['checks', 'wait', '--pr-number', str(_PR_NUMBER)])
    assert args.dispatch == 'undeclared'

    declared = parser.parse_args(['checks', 'wait', '--pr-number', str(_PR_NUMBER), '--dispatch', 'detached'])
    assert declared.dispatch == 'detached'


# =============================================================================
# Cross-provider: the GitLab arm maps onto the same shared vocabulary
# =============================================================================


def test_gitlab_wait_records_the_shared_vocabulary(monkeypatch, wait_records):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, '_read_ci_wait_p50_seed', lambda: None)
    monkeypatch.setattr(gitlab_ops, '_record_ci_wait_duration', lambda _duration: None)
    monkeypatch.setattr(gitlab_ops, '_fetch_mr_head_sha', lambda _pr: 'deadbeef')
    monkeypatch.setattr(gitlab_ops, '_enrich_failing_checks', lambda entries, **_kw: entries)
    monkeypatch.setattr(gitlab_ops, '_monotonic', _make_incrementing_clock())
    monkeypatch.setattr(gitlab_ops, '_watch_pipeline', lambda *_a, **_kw: (0, '', ''))

    snapshots = [
        {'jobs': [{'name': 'build', 'status': 'running'}], 'pipeline_id': 77, 'pipeline_status': 'running'},
        {'jobs': [{'name': 'build', 'status': 'success'}], 'pipeline_id': 77, 'pipeline_status': 'success'},
    ]

    def fake_fetch(_pr_number):
        return True, snapshots.pop(0) if len(snapshots) > 1 else snapshots[0]

    monkeypatch.setattr(gitlab_ops, '_fetch_mr_jobs', fake_fetch)

    result = gitlab_ops.cmd_ci_wait(_ci_wait_args(dispatch='detached'))

    assert result['status'] == 'success', result
    assert result['mechanism'] == 'watch_tail', 'the GitLab returned dict must carry the mechanism too'
    assert len(wait_records) == 1, wait_records
    fields = _parse_wait_record(wait_records[0][2])
    assert fields['consumer'] == 'ci-wait'
    assert fields['mechanism'] == 'watch_tail'
    assert fields['mechanism'] in ci_base.WAIT_MECHANISMS
    assert fields['dispatch'] in ci_base.WAIT_DISPATCH_MODES
    assert fields['outcome'] == 'success'
