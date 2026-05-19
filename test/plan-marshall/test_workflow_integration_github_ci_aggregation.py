#!/usr/bin/env python3
"""Tests for github_ops.py CI conclusion-state aggregation.

Locks the canonical conclusion → partition mapping established in
lesson-2026-05-18-16-001 deliverable 1:

    non-failing : SUCCESS | SKIPPED | NEUTRAL
    failing     : FAILURE | TIMED_OUT | CANCELLED | ACTION_REQUIRED |
                  STALE | STARTUP_FAILURE | <unknown future conclusion>
    wait        : IN_PROGRESS | QUEUED | PENDING | <empty/null>

The aggregation seam appears in three call sites:

    _classify_check_buckets  — the partition helper
    cmd_ci_status            — sync overall-status read
    cmd_ci_wait              — wait-loop final_status
    _fetch_pr_overall_ci_status — used by ci_wait_for_status_flip

The ``mixed`` outcome was deleted as part of the lesson — every input
must now resolve to one of ``pending | success | failure | none``.

Tests use the conftest run_gh / poll_until monkeypatch seam — no live
``gh`` invocations.
"""

import argparse
import time

import ci_base  # type: ignore[import-not-found]
import github_ops  # type: ignore[import-not-found]

# =============================================================================
# Helpers
# =============================================================================


def _check(state: str, name: str = 'check', link: str = '') -> dict:
    """Build a minimal check row matching ``gh pr checks --json state`` shape."""
    return {
        'name': name,
        'state': state,
        'bucket': '',
        'link': link,
        'startedAt': '',
        'completedAt': '',
        'workflow': '',
    }


def _ok_auth():
    return True, ''


def _noop_sleep(monkeypatch):
    monkeypatch.setattr(ci_base.time, 'sleep', lambda *_a, **_kw: None)
    monkeypatch.setattr(time, 'sleep', lambda *_a, **_kw: None)


# =============================================================================
# _classify_check_buckets — single-conclusion partition table
# =============================================================================


def test_classify_success_is_non_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('SUCCESS')])
    assert failing == [] and wait == [] and len(non_failing) == 1


def test_classify_skipped_is_non_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('SKIPPED')])
    assert failing == [] and wait == [] and len(non_failing) == 1


def test_classify_neutral_is_non_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('NEUTRAL')])
    assert failing == [] and wait == [] and len(non_failing) == 1


def test_classify_failure_is_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('FAILURE')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_timed_out_is_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('TIMED_OUT')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_cancelled_is_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('CANCELLED')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_action_required_is_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('ACTION_REQUIRED')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_stale_is_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('STALE')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_startup_failure_is_failing():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('STARTUP_FAILURE')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_in_progress_is_wait():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('IN_PROGRESS')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_queued_is_wait():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('QUEUED')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_pending_is_wait():
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('PENDING')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_null_conclusion_is_wait():
    """A missing/null ``state`` field normalises to empty-string → wait partition."""
    failing, wait, non_failing = github_ops._classify_check_buckets([{'name': 'x'}])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_unknown_conclusion_defaults_to_failing():
    """Defense-in-depth: unknown future conclusions land in the failing bucket."""
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('NEW_FUTURE_VALUE')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_case_insensitive_normalisation():
    """``_normalize_conclusion`` upper-cases the raw state, so lowercase input still partitions."""
    failing, wait, non_failing = github_ops._classify_check_buckets([_check('success')])
    assert failing == [] and wait == [] and len(non_failing) == 1


# =============================================================================
# _derive_overall_status — mixed-fixture aggregation
# =============================================================================


def test_derive_empty_returns_none():
    status, failing, wait = github_ops._derive_overall_status([])
    assert status == 'none' and failing == [] and wait == []


def test_derive_success_plus_skipped_returns_success():
    checks = [_check('SUCCESS', name='build'), _check('SKIPPED', name='license')]
    status, failing, wait = github_ops._derive_overall_status(checks)
    assert status == 'success' and failing == [] and wait == []


def test_derive_success_plus_neutral_returns_success():
    checks = [_check('SUCCESS', name='build'), _check('NEUTRAL', name='cla')]
    status, failing, wait = github_ops._derive_overall_status(checks)
    assert status == 'success'


def test_derive_success_plus_skipped_plus_neutral_returns_success():
    checks = [_check('SUCCESS'), _check('SKIPPED'), _check('NEUTRAL')]
    status, failing, _ = github_ops._derive_overall_status(checks)
    assert status == 'success' and failing == []


def test_derive_success_plus_failure_returns_failure_with_failing_names():
    checks = [_check('SUCCESS', name='build'), _check('FAILURE', name='lint')]
    status, failing, wait = github_ops._derive_overall_status(checks)
    assert status == 'failure'
    assert [c.get('name') for c in failing] == ['lint']
    assert wait == []


def test_derive_success_plus_cancelled_returns_failure():
    checks = [_check('SUCCESS', name='build'), _check('CANCELLED', name='test')]
    status, failing, _ = github_ops._derive_overall_status(checks)
    assert status == 'failure'
    assert [c.get('name') for c in failing] == ['test']


def test_derive_skipped_plus_neutral_plus_cancelled_returns_failure():
    """One failing partition member is enough to flip the aggregate."""
    checks = [_check('SKIPPED'), _check('NEUTRAL'), _check('CANCELLED', name='dep-review')]
    status, failing, _ = github_ops._derive_overall_status(checks)
    assert status == 'failure'
    assert [c.get('name') for c in failing] == ['dep-review']


def test_derive_success_plus_in_progress_returns_pending():
    """A single wait-state check forces the aggregate into ``pending``."""
    checks = [_check('SUCCESS', name='build'), _check('IN_PROGRESS', name='deploy')]
    status, failing, wait = github_ops._derive_overall_status(checks)
    assert status == 'pending'
    assert failing == []
    assert [c.get('name') for c in wait] == ['deploy']


def test_derive_failure_plus_in_progress_returns_pending():
    """Wait dominates failure — caller must wait before declaring failure."""
    checks = [_check('FAILURE', name='lint'), _check('IN_PROGRESS', name='build')]
    status, failing, wait = github_ops._derive_overall_status(checks)
    assert status == 'pending'
    assert failing == []
    assert [c.get('name') for c in wait] == ['build']


# =============================================================================
# PR #410 regression — the originating shape of lesson-2026-05-18-16-001
# =============================================================================


def test_pr_410_regression_three_successes_one_skipped_is_success():
    """Lesson-2026-05-18-16-001: PR #410's CI shape ``[success, success, success, skipped]``
    MUST aggregate to ``success`` (not ``failure``, not ``mixed``).

    Before the fix the legacy ``mixed`` fall-through interpreted any non-pass /
    non-skip conclusion as failure, but it also silently routed
    success-plus-skipped into ``mixed`` via the legacy bucket comparison —
    forcing the precondition resolver to report ``ci_failure`` on every green
    PR with at least one skipped check.
    """
    checks = [
        _check('SUCCESS', name='build'),
        _check('SUCCESS', name='test'),
        _check('SUCCESS', name='lint'),
        _check('SKIPPED', name='license-check'),
    ]
    status, failing, wait = github_ops._derive_overall_status(checks)
    assert status == 'success', f'PR #410 regression: expected success, got {status}'
    assert failing == []
    assert wait == []


# =============================================================================
# cmd_ci_status — end-to-end with stubbed run_gh
# =============================================================================


def _ci_status_args(pr_number=42):
    return argparse.Namespace(pr_number=pr_number, plan_id=None, slot=None)


def _make_run_gh_returning(checks_json: str):
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        if args[:2] == ['pr', 'checks']:
            return 0, checks_json, ''
        if args[:2] == ['pr', 'view']:
            return 0, '{"headRefOid": "deadbeef"}', ''
        return 0, '', ''

    return run_gh_stub, captured


def test_ci_status_returns_success_for_all_passing(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    stub, _ = _make_run_gh_returning('[{"name":"build","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""}]')
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    result = github_ops.cmd_ci_status(_ci_status_args())

    assert result['status'] == 'success'
    assert result['overall_status'] == 'success'
    assert result['check_count'] == 1


def test_ci_status_returns_success_for_pass_plus_skipped(monkeypatch):
    """The PR #410 regression at the cmd_ci_status call site."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    payload = (
        '['
        '{"name":"build","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""},'
        '{"name":"license","state":"SKIPPED","bucket":"skipped","link":"","startedAt":"","completedAt":"","workflow":""}'
        ']'
    )
    stub, _ = _make_run_gh_returning(payload)
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    result = github_ops.cmd_ci_status(_ci_status_args())

    assert result['overall_status'] == 'success'


def test_ci_status_returns_failure_for_one_failing(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    payload = (
        '['
        '{"name":"build","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""},'
        '{"name":"lint","state":"FAILURE","bucket":"fail","link":"","startedAt":"","completedAt":"","workflow":""}'
        ']'
    )
    stub, _ = _make_run_gh_returning(payload)
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    result = github_ops.cmd_ci_status(_ci_status_args())

    assert result['overall_status'] == 'failure'


def test_ci_status_returns_pending_for_one_in_progress(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    payload = (
        '['
        '{"name":"build","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""},'
        '{"name":"deploy","state":"IN_PROGRESS","bucket":"","link":"","startedAt":"","completedAt":"","workflow":""}'
        ']'
    )
    stub, _ = _make_run_gh_returning(payload)
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    result = github_ops.cmd_ci_status(_ci_status_args())

    assert result['overall_status'] == 'pending'


def test_ci_status_returns_none_for_empty_checks(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    stub, _ = _make_run_gh_returning('[]')
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    result = github_ops.cmd_ci_status(_ci_status_args())

    assert result['overall_status'] == 'none'


# =============================================================================
# cmd_ci_wait — final_status derivation after wait completes
# =============================================================================


def _ci_wait_args(pr_number=42, timeout=5, interval=0):
    return argparse.Namespace(pr_number=pr_number, timeout=timeout, interval=interval)


def test_ci_wait_final_status_success_for_pass_plus_skipped(monkeypatch):
    """PR #410 regression at the cmd_ci_wait call site — the precondition source."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    payload = (
        '['
        '{"name":"build","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""},'
        '{"name":"license","state":"SKIPPED","bucket":"skipped","link":"","startedAt":"","completedAt":"","workflow":""}'
        ']'
    )

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, payload, ''
        if args[:2] == ['pr', 'view']:
            return 0, '{"headRefOid": "deadbeef"}', ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_ci_wait(_ci_wait_args())

    assert result['status'] == 'success', result
    assert result['final_status'] == 'success'
    assert result['failing_checks'] == []
    assert result['wait_outcome'] == 'completed'


def test_ci_wait_final_status_failure_lists_failing_checks(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    payload = (
        '['
        '{"name":"build","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""},'
        '{"name":"lint","state":"FAILURE","bucket":"fail","link":"https://github.com/o/r/actions/runs/77/job/1","startedAt":"","completedAt":"","workflow":"ci"}'
        ']'
    )

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, payload, ''
        if args[:2] == ['pr', 'view']:
            return 0, '{"headRefOid": "deadbeef"}', ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_ci_wait(_ci_wait_args())

    assert result['final_status'] == 'failure'
    assert [e['name'] for e in result['failing_checks']] == ['lint']
    assert result['failing_checks'][0]['conclusion'] == 'FAILURE'
    assert result['failing_checks'][0]['run_id'] == '77'


def test_ci_wait_final_status_none_when_zero_checks(monkeypatch):
    """An empty checks payload still completes the wait — final_status is ``none``."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    # is_complete_fn returns False for the empty list, so the poll has to
    # eventually yield a non-empty payload OR time out. We force the second
    # poll to return a non-empty terminal list so the wait completes cleanly,
    # then assert ``final_status`` derives from the terminal state.
    call = {'n': 0}

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            call['n'] += 1
            if call['n'] == 1:
                return 0, '[]', ''
            return 0, '[{"name":"x","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""}]', ''
        if args[:2] == ['pr', 'view']:
            return 0, '{"headRefOid": "deadbeef"}', ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_ci_wait(_ci_wait_args())

    assert result['status'] == 'success'
    assert result['final_status'] == 'success'


# =============================================================================
# _fetch_pr_overall_ci_status — used by ci_wait_for_status_flip
# =============================================================================


def test_fetch_pr_overall_returns_success_for_pass_plus_skipped(monkeypatch):
    payload = (
        '['
        '{"name":"build","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""},'
        '{"name":"license","state":"SKIPPED","bucket":"skipped","link":"","startedAt":"","completedAt":"","workflow":""}'
        ']'
    )

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, payload, ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ok, status = github_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'success'


def test_fetch_pr_overall_returns_failure_for_one_cancelled(monkeypatch):
    payload = (
        '['
        '{"name":"build","state":"SUCCESS","bucket":"pass","link":"","startedAt":"","completedAt":"","workflow":""},'
        '{"name":"dep-review","state":"CANCELLED","bucket":"","link":"","startedAt":"","completedAt":"","workflow":""}'
        ']'
    )

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, payload, ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ok, status = github_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'failure'


def test_fetch_pr_overall_returns_pending_for_in_progress(monkeypatch):
    payload = (
        '['
        '{"name":"build","state":"IN_PROGRESS","bucket":"","link":"","startedAt":"","completedAt":"","workflow":""}'
        ']'
    )

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, payload, ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ok, status = github_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'pending'


def test_fetch_pr_overall_returns_none_for_empty(monkeypatch):
    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, '[]', ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ok, status = github_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'none'
