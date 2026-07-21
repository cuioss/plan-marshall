#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""GitHub-specific coverage for the ci/issue wait surface of github_ops.py.

The provider-agnostic poll-handler contract — dispatch-table registration, the
auth short-circuit, and the flip/timeout/``--expected`` matrix for the three
wait-for-* handlers — lives in ``_ci_wait_contract`` and is bound into this
module below, so it executes once for GitHub. What remains here is genuinely
GitHub-specific:

    - the ``gh``-shaped stub wiring (``run_gh`` / ``_RunGhStub``)
    - the ``gh run view --log-failed`` failure-path download + filter wiring,
      driven against the committed ``ci-logs/github/fail.log`` fixture
    - the p50-seeded first sleep and the ``gh run watch`` terminal-state tail,
      whose seams live in ``_github_ci``

Tests never shell out to the real ``gh`` CLI: every fetch helper and the auth
check are monkeypatched, and ``time.sleep`` is neutralised so timeout branches
run in constant time.
"""

import argparse

import _github_ci
import github_ops
import pytest
from _ci_wait_contract import (
    CI_LOG_FIXTURE_ROOT,
    CONTRACT_TESTS,
    _make_incrementing_clock,
    _noop_sleep,
    _ok_auth,
    _resolve_plan_relative,
    test_ci_wait_for_status_flip_auth_failure_short_circuits,  # noqa: F401
    test_ci_wait_for_status_flip_completes_on_flip,  # noqa: F401
    test_ci_wait_for_status_flip_expected_any_accepts_failure,  # noqa: F401
    test_ci_wait_for_status_flip_expected_any_accepts_success,  # noqa: F401
    test_ci_wait_for_status_flip_expected_success_rejects_failure,  # noqa: F401
    test_ci_wait_for_status_flip_times_out_when_status_never_changes,  # noqa: F401
    test_dispatch_ci_wait_for_status_flip_registered,  # noqa: F401
    test_dispatch_issue_wait_for_close_registered,  # noqa: F401
    test_dispatch_issue_wait_for_label_registered,  # noqa: F401
    test_issue_wait_for_close_auth_failure_short_circuits,  # noqa: F401
    test_issue_wait_for_close_completes_on_flip,  # noqa: F401
    test_issue_wait_for_close_times_out_when_state_never_changes,  # noqa: F401
    test_issue_wait_for_label_absent_completes_when_label_disappears,  # noqa: F401
    test_issue_wait_for_label_auth_failure_short_circuits,  # noqa: F401
    test_issue_wait_for_label_present_completes_when_label_appears,  # noqa: F401
    test_issue_wait_for_label_times_out_when_label_state_never_changes,  # noqa: F401
)

# Real committed GitHub-Actions-shaped failure log fixture. Fed as the mocked
# ``gh run view --log-failed`` raw-log source so the failure-path download +
# filter + store wiring is validated against REAL log content (not a toy string).
_GITHUB_FAIL_LOG = CI_LOG_FIXTURE_ROOT / 'github' / 'fail.log'


@pytest.fixture
def ci_ops():
    """Feed the provider-agnostic contract this module's provider ops module."""
    return github_ops


def test_contract_surface_is_bound_for_github():
    """Every provider-agnostic contract test is bound in this module.

    Guards the "the contract runs once per provider" invariant: a contract test
    added to ``_ci_wait_contract`` but never imported here would otherwise be
    silently uncollected for GitHub.
    """
    missing = [name for name in CONTRACT_TESTS if name not in globals()]
    assert missing == [], missing


# =============================================================================
# Failure-path log download + filter wiring
# =============================================================================
#
# These tests drive cmd_ci_status / cmd_ci_wait end-to-end through the failure
# branch with the REAL committed GitHub failure fixture
# (fixtures/ci-logs/github/fail.log) standing in for the
# ``gh run view --log-failed`` raw-log source. ``check_auth`` and ``run_gh`` are
# monkeypatched so no real ``gh`` CLI runs, while the download+filter+store hook
# (ci_base.enrich_failing_checks_with_logs -> manage-ci-artifacts.persist ->
# _ci_log_filter.filter_log) executes for real against the fixture content. The
# ``plan_context`` fixture redirects PLAN_BASE_DIR so persist writes the per-run
# artifact tree under tmp rather than the repo-local .plan/.


def _read_github_fail_fixture() -> str:
    """Load the REAL committed GitHub failure log fixture content."""
    return _GITHUB_FAIL_LOG.read_text(encoding='utf-8')


def _two_failing_check_rows():
    """Two distinctly-named failing GitHub check rows with distinct run ids.

    Distinct run ids (distinct ``link`` URLs) AND distinct names guarantee the
    enrichment hook slugs each entry to its own file — never a collision.
    """
    return [
        {
            'name': 'verify / verify',
            'state': 'FAILURE',
            'bucket': 'fail',
            'link': 'https://github.com/o/r/actions/runs/1001/job/9001',
            'startedAt': '2026-01-01T00:00:00Z',
            'completedAt': '2026-01-01T00:05:00Z',
            'workflow': 'verify',
        },
        {
            'name': 'lint / lint',
            'state': 'FAILURE',
            'bucket': 'fail',
            'link': 'https://github.com/o/r/actions/runs/1002/job/9002',
            'startedAt': '2026-01-01T00:00:00Z',
            'completedAt': '2026-01-01T00:04:00Z',
            'workflow': 'lint',
        },
    ]


def _wire_github_failure(monkeypatch, *, check_rows):
    """Monkeypatch auth / run_gh / raw-log fetch for a failure-path drive.

    ``run_gh`` answers ``pr checks`` with the supplied check rows and ``pr view
    --json headRefOid`` with a stable SHA; the raw failed-run log fetcher returns
    the REAL committed GitHub failure fixture so the filter runs on real content.
    """
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    fixture = _read_github_fail_fixture()

    def fake_run_gh(args, capture_json=False, timeout=60):
        if 'checks' in args:
            import json

            return 0, json.dumps(check_rows), ''
        if 'view' in args and '--json' in args:
            import json

            return 0, json.dumps({'headRefOid': 'deadbeefcafe'}), ''
        return 1, '', 'unexpected gh invocation'

    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)

    fetch_calls = {'run_ids': []}

    def fake_fetch_log(run_id, job_id=''):
        fetch_calls['run_ids'].append(str(run_id))
        return fixture

    monkeypatch.setattr(github_ops, '_fetch_failed_run_log', fake_fetch_log)
    return fixture, fetch_calls


def _assert_real_github_failure_enrichment(failing_checks, plan_context, *, fixture):
    """Assert >=2 entries each gained a distinct, non-empty filtered file.

    Validates the per-entry log_file / filtered_log_file wiring AND that the
    filtered file content was extracted from the REAL fixture (the captured
    pytest failure markers survive filtering).
    """
    # At least two failing checks, each with its own filtered path.
    assert len(failing_checks) >= 2
    filtered_paths = [e['filtered_log_file'] for e in failing_checks]
    log_paths = [e['log_file'] for e in failing_checks]
    # Every entry carries a non-empty per-entry path pair.
    assert all(filtered_paths), failing_checks
    assert all(log_paths), failing_checks
    # The filtered files are distinctly named (one per failing check).
    assert len(set(filtered_paths)) >= 2, filtered_paths
    assert len(set(log_paths)) >= 2, log_paths

    # Each filtered file exists, is non-empty, and contains the REAL failure's
    # error lines extracted from the fixture; passing-test noise is dropped.
    for entry in failing_checks:
        on_disk = _resolve_plan_relative(plan_context, entry['filtered_log_file'])
        content = on_disk.read_text(encoding='utf-8')
        assert content.strip(), f'filtered log empty: {on_disk}'
        # Real captured-failure markers from the GitHub fixture survive filtering.
        assert 'AssertionError' in content
        assert 'IndexError: list index out of range' in content
        # Proof real filtering happened: passing-test noise dropped from subset.
        assert 'test_create_interface PASSED' not in content
    # Sanity: the fixture itself is the real captured log (not a toy string).
    assert 'collected 78 items' in fixture


def _status_args(*, pr_number=77, plan_id, error_style='generic'):
    return argparse.Namespace(
        pr_number=pr_number,
        head=None,
        router_plan_id=plan_id,
        error_style=error_style,
    )


def test_ci_status_failure_enriches_each_failing_check_with_real_filtered_log(monkeypatch, plan_context):
    """cmd_ci_status failure TOON: each failing_checks[] entry gains its own
    log_file / filtered_log_file, fed from the REAL github/fail.log fixture."""
    rows = _two_failing_check_rows()
    fixture, fetch_calls = _wire_github_failure(monkeypatch, check_rows=rows)

    result = github_ops.cmd_ci_status(_status_args(plan_id=plan_context.plan_id))

    # failure overall, failing_checks present and enriched.
    assert result['status'] == 'success'
    assert result['overall_status'] == 'failure'
    assert 'failing_checks' in result
    _assert_real_github_failure_enrichment(result['failing_checks'], plan_context, fixture=fixture)
    # The raw-log fetcher was driven once per distinct run id.
    assert len(set(fetch_calls['run_ids'])) >= 2


def test_ci_status_success_path_has_no_failing_checks_key(monkeypatch, plan_context):
    """A green pipeline leaves the success TOON unchanged — no failing_checks,
    and the raw-log fetcher is never invoked."""
    # both checks pass.
    rows = _two_failing_check_rows()
    for row in rows:
        row['state'] = 'SUCCESS'
        row['bucket'] = 'pass'
    _, fetch_calls = _wire_github_failure(monkeypatch, check_rows=rows)

    result = github_ops.cmd_ci_status(_status_args(plan_id=plan_context.plan_id))

    # unchanged success envelope; enrichment never ran.
    assert result['status'] == 'success'
    assert result['overall_status'] == 'success'
    assert 'failing_checks' not in result
    assert fetch_calls['run_ids'] == []


def _wait_args(*, pr_number=77, plan_id, error_style='generic', timeout=5, interval=0):
    return argparse.Namespace(
        pr_number=pr_number,
        head=None,
        router_plan_id=plan_id,
        error_style=error_style,
        timeout=timeout,
        interval=interval,
    )


def test_ci_wait_failure_enriches_each_failing_check_with_real_filtered_log(monkeypatch, plan_context):
    """cmd_ci_wait natural-termination failure: each failing_checks[] entry
    gains its own log_file / filtered_log_file from the REAL fixture."""
    rows = _two_failing_check_rows()
    fixture, fetch_calls = _wire_github_failure(monkeypatch, check_rows=rows)
    _noop_sleep(monkeypatch)

    # the wait loop terminates immediately (no wait-state checks).
    result = github_ops.cmd_ci_wait(_wait_args(plan_id=plan_context.plan_id))

    assert result['status'] == 'success'
    assert result['final_status'] == 'failure'
    assert 'failing_checks' in result
    _assert_real_github_failure_enrichment(result['failing_checks'], plan_context, fixture=fixture)
    assert len(set(fetch_calls['run_ids'])) >= 2


def test_ci_wait_success_path_failing_checks_empty(monkeypatch, plan_context):
    """A green wait result carries an empty failing_checks list and never
    invokes the raw-log fetcher."""
    # both checks pass.
    rows = _two_failing_check_rows()
    for row in rows:
        row['state'] = 'SUCCESS'
        row['bucket'] = 'pass'
    _, fetch_calls = _wire_github_failure(monkeypatch, check_rows=rows)
    _noop_sleep(monkeypatch)

    result = github_ops.cmd_ci_wait(_wait_args(plan_id=plan_context.plan_id))

    assert result['status'] == 'success'
    assert result['final_status'] == 'success'
    assert result['failing_checks'] == []
    assert fetch_calls['run_ids'] == []


# =============================================================================
# p50-seeded first sleep + terminal-state watch-verb tail
# =============================================================================
#
# These drive the reworked cmd_ci_wait: a p50 first-sleep seed then a
# ``gh run watch`` terminal-state tail. The p50 read / record seams, the sleep
# seam, the watch-verb seam, and the monotonic clock all live in ``_github_ci``
# and are monkeypatched there (cmd_ci_wait resolves them in its own module
# namespace); ``check_auth`` / ``run_gh`` remain patched on ``github_ops``.


def _check_row(name, state, run_id, *, workflow='verify'):
    """Build a single ``gh pr checks --json`` row with a run-id-bearing link.

    ``state`` drives the canonical partition: ``IN_PROGRESS`` (wait),
    ``SUCCESS`` (non-failing), ``FAILURE`` (failing).
    """
    bucket = {'SUCCESS': 'pass', 'FAILURE': 'fail', 'IN_PROGRESS': 'pending'}.get(state, 'pending')
    return {
        'name': name,
        'state': state,
        'bucket': bucket,
        'link': f'https://github.com/o/r/actions/runs/{run_id}/job/9',
        'startedAt': '2026-01-01T00:00:00Z',
        'completedAt': '2026-01-01T00:05:00Z',
        'workflow': workflow,
    }


class _RunGhStub:
    """Stateful ``run_gh`` seam: ``pr checks`` returns ``pending_rows`` until the
    watch verb flips ``watched`` True, then ``terminal_rows``; ``pr view --json``
    answers with a stable head SHA. Any other invocation is an error."""

    def __init__(self, pending_rows, terminal_rows):
        self.pending_rows = pending_rows
        self.terminal_rows = terminal_rows
        self.watched = False
        self.checks_calls = 0

    def __call__(self, args, capture_json=False, timeout=60):
        import json

        if 'checks' in args:
            self.checks_calls += 1
            rows = self.terminal_rows if self.watched else self.pending_rows
            return 0, json.dumps(rows), ''
        if 'view' in args and '--json' in args:
            return 0, json.dumps({'headRefOid': 'deadbeefcafe'}), ''
        return 1, '', 'unexpected gh invocation'


def _p50_wait_args(*, pr_number=77, plan_id, timeout=600, interval=0):
    return argparse.Namespace(
        pr_number=pr_number,
        head=None,
        router_plan_id=plan_id,
        error_style='generic',
        timeout=timeout,
        interval=interval,
    )


def test_ci_wait_p50_seed_applied_then_watch_maps_success(monkeypatch, plan_context):
    """The watch tail is what completes the wait, and its terminal SUCCESS maps
    onto the result envelope.

    The stub only serves terminal rows once the watch verb has run against the
    in-progress run, so ``wait_outcome == 'completed'`` with the in-progress
    run's id is the observable proof that the watch tail drove the completion —
    no assertion on the watch seam's call sequence is needed.
    """
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    stub = _RunGhStub(
        pending_rows=[_check_row('verify / verify', 'IN_PROGRESS', 1001)],
        terminal_rows=[_check_row('verify / verify', 'SUCCESS', 1001)],
    )
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    monkeypatch.setattr(_github_ci, '_read_ci_wait_p50_seed', lambda: 120)
    monkeypatch.setattr(_github_ci, '_sleep_seed', lambda s: None)
    monkeypatch.setattr(_github_ci, '_monotonic', _make_incrementing_clock())

    def fake_watch(run_id, timeout):
        stub.watched = True
        return 0, '', ''

    monkeypatch.setattr(_github_ci, '_watch_run', fake_watch)
    recorded: list[int] = []
    monkeypatch.setattr(_github_ci, '_record_ci_wait_duration', lambda d: recorded.append(d))

    result = github_ops.cmd_ci_wait(_p50_wait_args(plan_id=plan_context.plan_id, timeout=600))

    assert result['status'] == 'success'
    assert result['final_status'] == 'success'
    assert result['wait_outcome'] == 'completed'
    assert result['run_id'] == '1001'
    # Observed wall-clock duration recorded back into the p50 window on success.
    assert len(recorded) == 1 and recorded[0] > 0


def test_ci_wait_p50_seed_skipped_on_empty_window(monkeypatch, plan_context):
    """An empty p50 window (None) skips the first-sleep seed entirely; an
    already-terminal snapshot needs no watch."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    stub = _RunGhStub(
        pending_rows=[_check_row('verify / verify', 'SUCCESS', 1001)],
        terminal_rows=[_check_row('verify / verify', 'SUCCESS', 1001)],
    )
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    monkeypatch.setattr(_github_ci, '_read_ci_wait_p50_seed', lambda: None)
    seed_sleeps: list[int] = []
    monkeypatch.setattr(_github_ci, '_sleep_seed', lambda s: seed_sleeps.append(s))

    watch_calls: list[str] = []

    def fake_watch(run_id, timeout):
        watch_calls.append(run_id)
        return 0, '', ''

    monkeypatch.setattr(_github_ci, '_watch_run', fake_watch)

    result = github_ops.cmd_ci_wait(_p50_wait_args(plan_id=plan_context.plan_id))

    assert result['final_status'] == 'success'
    # An absent window must produce no sleep at all — the seam records nothing.
    assert seed_sleeps == []
    # An already-terminal snapshot has no wait partition, so nothing is watched.
    assert watch_calls == []


@pytest.mark.parametrize(
    ('seed', 'timeout', 'expected_sleep'),
    [
        (120, 600, 120),  # seed under the ceiling is slept as-is
        (900, 300, 300),  # seed above the ceiling is clamped to --timeout
    ],
)
def test_ci_wait_p50_seed_bounded_by_timeout(monkeypatch, plan_context, seed, timeout, expected_sleep):
    """The p50 seed is slept exactly once, clamped to --timeout.

    The slept value is not surfaced anywhere in the result envelope, so the seed
    seam is the only surface that can prove the bound.
    """
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    stub = _RunGhStub(
        pending_rows=[_check_row('verify / verify', 'SUCCESS', 1001)],
        terminal_rows=[_check_row('verify / verify', 'SUCCESS', 1001)],
    )
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    monkeypatch.setattr(_github_ci, '_read_ci_wait_p50_seed', lambda: seed)
    seed_sleeps: list[int] = []
    monkeypatch.setattr(_github_ci, '_sleep_seed', lambda s: seed_sleeps.append(s))

    result = github_ops.cmd_ci_wait(_p50_wait_args(plan_id=plan_context.plan_id, timeout=timeout))

    assert result['final_status'] == 'success'
    assert seed_sleeps == [expected_sleep]


def test_ci_wait_deadline_exceeded_preserved_when_still_pending(monkeypatch, plan_context):
    """A check that never leaves the wait partition (even after the watch tail)
    yields the deadline_exceeded timeout envelope, and no duration is recorded."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    pending = [_check_row('verify / verify', 'IN_PROGRESS', 1001)]
    # terminal_rows also pending → the run never terminates.
    stub = _RunGhStub(pending_rows=pending, terminal_rows=pending)
    monkeypatch.setattr(github_ops, 'run_gh', stub)

    monkeypatch.setattr(_github_ci, '_read_ci_wait_p50_seed', lambda: None)
    monkeypatch.setattr(_github_ci, '_sleep_seed', lambda s: None)

    def fake_watch(run_id, timeout):
        stub.watched = True
        return 0, '', ''

    monkeypatch.setattr(_github_ci, '_watch_run', fake_watch)
    recorded: list[int] = []
    monkeypatch.setattr(_github_ci, '_record_ci_wait_duration', lambda d: recorded.append(d))

    result = github_ops.cmd_ci_wait(_p50_wait_args(plan_id=plan_context.plan_id))

    assert result['status'] == 'error'
    assert result['operation'] == 'ci_wait'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert 'failing_checks' in result
    assert result['run_id'] == '1001'
    # A non-success (timeout) completion never records into the p50 window.
    assert recorded == []
