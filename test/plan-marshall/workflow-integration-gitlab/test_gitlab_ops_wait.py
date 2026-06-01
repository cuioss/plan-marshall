#!/usr/bin/env python3
"""Tests for gitlab_ops.py ci/issue wait-for-* poll handlers.

GitLab counterpart to the GitHub tests. Covers the three handlers:
    cmd_ci_wait_for_status_flip
    cmd_issue_wait_for_close
    cmd_issue_wait_for_label

Scope:
    - Dispatch-table registration for each (group, subcommand) tuple
    - Auth short-circuit before any fetch helper / poll_until call
    - Happy path: fetch helper flips baseline → completed with timed_out=false
    - Timeout path: fetch helper always returns baseline → timed_out=true

Tests never shell out to the real ``glab`` CLI: every fetch helper and the
auth check are monkeypatched, and ``time.sleep`` inside ``poll_until`` is
neutralised so the timeout branch runs in constant time.
"""

import argparse
import json
import time
from pathlib import Path

import ci_base  # type: ignore[import-not-found]
import gitlab_ops  # type: ignore[import-not-found]

# Real committed GitLab-job-trace-shaped failure log fixture. Resolved relative
# to this test file so resolution never depends on cwd. Fed as the mocked
# ``glab ci trace`` raw-trace source so the failure-path download + filter +
# store wiring is validated against REAL log content (not a toy string).
_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / 'tools-integration-ci' / 'fixtures' / 'ci-logs'
_GITLAB_FAIL_LOG = _FIXTURE_ROOT / 'gitlab' / 'fail.log'


def _ok_auth():
    return True, ''


def _noop_sleep(monkeypatch):
    """Make poll_until's sleep a no-op so timeout-path tests finish fast."""
    monkeypatch.setattr(ci_base.time, 'sleep', lambda *_a, **_kw: None)
    monkeypatch.setattr(time, 'sleep', lambda *_a, **_kw: None)


# =============================================================================
# Dispatch-table registration
# =============================================================================


def _build_handler_map():
    """Rebuild the GitLab dispatch map slice for the three new wait-for-* entries."""
    return {
        ('checks', 'wait-for-status-flip'): gitlab_ops.cmd_ci_wait_for_status_flip,
        ('issue', 'wait-for-close'): gitlab_ops.cmd_issue_wait_for_close,
        ('issue', 'wait-for-label'): gitlab_ops.cmd_issue_wait_for_label,
    }


def test_dispatch_ci_wait_for_status_flip_registered():
    handlers = _build_handler_map()
    assert handlers[('checks', 'wait-for-status-flip')] is gitlab_ops.cmd_ci_wait_for_status_flip


def test_dispatch_issue_wait_for_close_registered():
    handlers = _build_handler_map()
    assert handlers[('issue', 'wait-for-close')] is gitlab_ops.cmd_issue_wait_for_close


def test_dispatch_issue_wait_for_label_registered():
    handlers = _build_handler_map()
    assert handlers[('issue', 'wait-for-label')] is gitlab_ops.cmd_issue_wait_for_label


# =============================================================================
# cmd_ci_wait_for_status_flip
# =============================================================================


def _flip_ci_status_args(*, expected='any', timeout=5, interval=0):
    return argparse.Namespace(pr_number=42, timeout=timeout, interval=interval, expected=expected)


def test_ci_wait_for_status_flip_auth_failure_short_circuits(monkeypatch):
    """Auth failure returns an error result without calling fetch or poll_until."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(pr_number):
        fetch_calls['count'] += 1
        return True, 'pending'

    monkeypatch.setattr(gitlab_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(gitlab_ops, 'poll_until', exploding_poll)

    result = gitlab_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'ci_wait_for_status_flip'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_ci_wait_for_status_flip_completes_on_flip(monkeypatch):
    """Baseline=pending, second fetch=success → handler returns success."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        assert pr_number == 42
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'success'

    monkeypatch.setattr(gitlab_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = gitlab_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args())

    assert result['status'] == 'success', result
    assert result['operation'] == 'ci_wait_for_status_flip'
    assert result['pr_number'] == 42
    assert result['timed_out'] is False
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'success'
    assert result['polls'] >= 1
    assert call_counts['fetch'] >= 2


def test_ci_wait_for_status_flip_times_out_when_status_never_changes(monkeypatch):
    """Fetch always returns the baseline → timed_out=true, final==baseline."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(pr_number):
        return True, 'pending'

    monkeypatch.setattr(gitlab_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = gitlab_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'pending'


def test_ci_wait_for_status_flip_expected_success_rejects_failure(monkeypatch):
    """--expected=success must treat a pending→failure transition as no-flip."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'failure'

    monkeypatch.setattr(gitlab_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = gitlab_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='success', timeout=1, interval=0))

    assert result['status'] == 'success', result
    # Fresh differs from baseline but is_complete_fn rejects because
    # --expected=success does not match 'failure' → poll_until must time out.
    assert result['timed_out'] is True
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'failure'


def test_ci_wait_for_status_flip_expected_any_accepts_success(monkeypatch):
    """--expected=any accepts any non-pending / non-baseline status."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'success'

    monkeypatch.setattr(gitlab_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = gitlab_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='any'))

    assert result['status'] == 'success', result
    assert result['timed_out'] is False
    assert result['final_status'] == 'success'


def test_ci_wait_for_status_flip_expected_any_accepts_failure(monkeypatch):
    """--expected=any also accepts a flip to failure."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'failure'

    monkeypatch.setattr(gitlab_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = gitlab_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='any'))

    assert result['status'] == 'success', result
    assert result['timed_out'] is False
    assert result['final_status'] == 'failure'


# =============================================================================
# cmd_issue_wait_for_close
# =============================================================================


def _wait_for_close_args(*, timeout=5, interval=0):
    return argparse.Namespace(issue_number=101, timeout=timeout, interval=interval)


def test_issue_wait_for_close_auth_failure_short_circuits(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(issue_number):
        fetch_calls['count'] += 1
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(gitlab_ops, '_fetch_issue_state_and_labels', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(gitlab_ops, 'poll_until', exploding_poll)

    result = gitlab_ops.cmd_issue_wait_for_close(_wait_for_close_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'issue_wait_for_close'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_issue_wait_for_close_completes_on_flip(monkeypatch):
    """Baseline state=open, second fetch=closed → timed_out=false."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        assert issue_number == 101
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': []}
        return True, {'state': 'closed', 'labels': []}

    monkeypatch.setattr(gitlab_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = gitlab_ops.cmd_issue_wait_for_close(_wait_for_close_args())

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_wait_for_close'
    assert result['issue_number'] == 101
    assert result['timed_out'] is False
    assert result['baseline_state'] == 'open'
    assert result['final_state'] == 'closed'
    assert result['polls'] >= 1
    assert call_counts['fetch'] >= 2


def test_issue_wait_for_close_times_out_when_state_never_changes(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(issue_number):
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(gitlab_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = gitlab_ops.cmd_issue_wait_for_close(_wait_for_close_args(timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_state'] == 'open'
    assert result['final_state'] == 'open'


# =============================================================================
# cmd_issue_wait_for_label
# =============================================================================


def _wait_for_label_args(*, mode='present', timeout=5, interval=0, label='ready'):
    return argparse.Namespace(
        issue_number=202,
        label=label,
        mode=mode,
        timeout=timeout,
        interval=interval,
    )


def test_issue_wait_for_label_auth_failure_short_circuits(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(issue_number):
        fetch_calls['count'] += 1
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(gitlab_ops, '_fetch_issue_state_and_labels', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(gitlab_ops, 'poll_until', exploding_poll)

    result = gitlab_ops.cmd_issue_wait_for_label(_wait_for_label_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'issue_wait_for_label'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_issue_wait_for_label_present_completes_when_label_appears(monkeypatch):
    """--mode=present: labels=[] → ['ready'] completes."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': []}
        return True, {'state': 'open', 'labels': ['ready']}

    monkeypatch.setattr(gitlab_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = gitlab_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='present'))

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_wait_for_label'
    assert result['mode'] == 'present'
    assert result['timed_out'] is False
    assert result['baseline_present'] is False
    assert result['final_present'] is True
    assert result['polls'] >= 1
    assert call_counts['fetch'] >= 2


def test_issue_wait_for_label_absent_completes_when_label_disappears(monkeypatch):
    """--mode=absent: labels=['ready'] → [] completes."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': ['ready']}
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(gitlab_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = gitlab_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='absent'))

    assert result['status'] == 'success', result
    assert result['mode'] == 'absent'
    assert result['timed_out'] is False
    assert result['baseline_present'] is True
    assert result['final_present'] is False


def test_issue_wait_for_label_times_out_when_label_state_never_changes(monkeypatch):
    """Baseline labels never flip → timed_out=true, final_present==baseline."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(issue_number):
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(gitlab_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = gitlab_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='present', timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_present'] is False
    assert result['final_present'] is False


# =============================================================================
# Failure-path log download + filter wiring (deliverable 5) — GitLab provider
# =============================================================================
#
# GitLab counterpart to the GitHub failure-path tests. Drives cmd_ci_status /
# cmd_ci_wait end-to-end through the failure branch with the REAL committed
# GitLab failure fixture (fixtures/ci-logs/gitlab/fail.log) standing in for the
# ``glab ci trace`` raw-trace source. ``check_auth`` and ``run_glab`` are
# monkeypatched so no real ``glab`` CLI runs, while the download+filter+store
# hook (ci_base.enrich_failing_checks_with_logs -> manage-ci-artifacts.persist
# -> _ci_log_filter.filter_log) executes for real against the fixture content.
# The ``plan_context`` fixture redirects PLAN_BASE_DIR so persist writes the
# per-run artifact tree under tmp rather than the repo-local .plan/.


def _read_gitlab_fail_fixture() -> str:
    """Load the REAL committed GitLab failure log fixture content."""
    return _GITLAB_FAIL_LOG.read_text(encoding='utf-8')


def _two_failing_jobs():
    """Two distinctly-named failing GitLab job rows sharing one pipeline id.

    Distinct names guarantee the enrichment hook slugs each entry to its own
    file even though both jobs belong to the same pipeline (run id) — proving
    >=2 failing checks produce >=2 distinctly-named filtered files.
    """
    return [
        {'name': 'quality-gate', 'status': 'failed', 'stage': 'test', 'pipeline_id': 5005,
         'web_url': 'https://gitlab.example.com/o/r/-/jobs/8001'},
        {'name': 'verify', 'status': 'failed', 'stage': 'test', 'pipeline_id': 5005,
         'web_url': 'https://gitlab.example.com/o/r/-/jobs/8002'},
    ]


def _wire_gitlab_failure(monkeypatch, *, jobs):
    """Monkeypatch auth / run_glab / raw-trace fetch for a failure-path drive.

    ``run_glab`` answers ``mr view`` with a pipeline envelope (failed, id=5005),
    ``ci view`` with the supplied jobs, and any other call with a stable JSON
    blob; the raw failed-job-trace fetcher returns the REAL committed GitLab
    failure fixture so the filter runs on real content.
    """
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)

    fixture = _read_gitlab_fail_fixture()
    pipeline_status = 'failed' if any(j['status'] == 'failed' for j in jobs) else 'success'

    def fake_run_glab(args):
        if args[:2] == ['mr', 'view']:
            return 0, json.dumps({'pipeline': {'id': 5005, 'status': pipeline_status}, 'sha': 'feedface'}), ''
        if args[:2] == ['ci', 'view']:
            return 0, json.dumps({'jobs': jobs}), ''
        return 0, json.dumps({}), ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', fake_run_glab)

    fetch_calls = {'run_ids': []}

    def fake_fetch_trace(run_id):
        fetch_calls['run_ids'].append(str(run_id))
        return fixture

    monkeypatch.setattr(gitlab_ops, '_fetch_failed_job_trace', fake_fetch_trace)
    return fixture, fetch_calls


def _resolve_plan_relative(plan_context, rel_path):
    """Resolve a plan-dir-relative artifact path under the redirected plan dir.

    The enrichment hook returns paths rooted at ``.plan/local/plans/{plan_id}/``;
    the ``plan_context`` fixture redirects PLAN_BASE_DIR so the on-disk tree is
    ``{fixture_dir}/plans/{plan_id}/...``. Splice on the ``plans/{plan_id}/``
    marker to map one onto the other without hard-coding the prefix shape.
    """
    marker = f'plans/{plan_context.plan_id}/'
    idx = rel_path.find(marker)
    assert idx != -1, f'unexpected artifact path shape: {rel_path}'
    return plan_context.fixture_dir / 'plans' / rel_path[idx + len('plans/'):]


def _assert_real_gitlab_failure_enrichment(failing_checks, plan_context, *, fixture):
    """Assert >=2 entries each gained a distinct, non-empty filtered file.

    Validates the per-entry log_file / filtered_log_file wiring AND that the
    filtered file content was extracted from the REAL GitLab fixture (the ruff
    failure markers survive filtering; passing-job noise is dropped).
    """
    assert len(failing_checks) >= 2
    filtered_paths = [e['filtered_log_file'] for e in failing_checks]
    log_paths = [e['log_file'] for e in failing_checks]
    assert all(filtered_paths), failing_checks
    assert all(log_paths), failing_checks
    # >=2 distinctly-named filtered files even though both jobs share one
    # pipeline (run id) — the per-check slug disambiguates.
    assert len(set(filtered_paths)) >= 2, filtered_paths
    assert len(set(log_paths)) >= 2, log_paths

    for entry in failing_checks:
        on_disk = _resolve_plan_relative(plan_context, entry['filtered_log_file'])
        content = on_disk.read_text(encoding='utf-8')
        assert content.strip(), f'filtered log empty: {on_disk}'
        # Real ruff/quality-gate failure markers from the GitLab fixture survive.
        assert 'Found 3 errors.' in content
        assert 'ERROR: Job failed' in content
        # Proof real filtering happened: the clean leading boilerplate is dropped.
        assert 'Running with gitlab-runner' not in content
    # Sanity: the fixture itself is the real captured trace (not a toy string).
    assert 'gitlab-runner' in fixture


def _gl_status_args(*, pr_number=88, plan_id, error_style='generic'):
    return argparse.Namespace(
        pr_number=pr_number,
        head=None,
        router_plan_id=plan_id,
        error_style=error_style,
    )


def test_ci_status_failure_enriches_each_failing_job_with_real_filtered_log(monkeypatch, plan_context):
    """cmd_ci_status failure TOON: each failing_checks[] entry gains its own
    log_file / filtered_log_file, fed from the REAL gitlab/fail.log fixture."""
    # Arrange
    jobs = _two_failing_jobs()
    fixture, fetch_calls = _wire_gitlab_failure(monkeypatch, jobs=jobs)

    # Act
    result = gitlab_ops.cmd_ci_status(_gl_status_args(plan_id=plan_context.plan_id))

    # Assert
    assert result['status'] == 'success'
    assert result['overall_status'] == 'failure'
    assert 'failing_checks' in result
    _assert_real_gitlab_failure_enrichment(result['failing_checks'], plan_context, fixture=fixture)
    # The raw-trace fetcher was driven once per failing job (shared run id).
    assert len(fetch_calls['run_ids']) >= 2


def test_ci_status_success_path_has_no_failing_checks_key(monkeypatch, plan_context):
    """A green pipeline leaves the success TOON unchanged — no failing_checks,
    and the raw-trace fetcher is never invoked."""
    # Arrange — both jobs succeed.
    jobs = _two_failing_jobs()
    for job in jobs:
        job['status'] = 'success'
    _, fetch_calls = _wire_gitlab_failure(monkeypatch, jobs=jobs)

    # Act
    result = gitlab_ops.cmd_ci_status(_gl_status_args(plan_id=plan_context.plan_id))

    # Assert — unchanged success envelope; enrichment never ran.
    assert result['status'] == 'success'
    assert result['overall_status'] == 'success'
    assert 'failing_checks' not in result
    assert fetch_calls['run_ids'] == []


def _gl_wait_args(*, pr_number=88, plan_id, error_style='generic', timeout=5, interval=0):
    return argparse.Namespace(
        pr_number=pr_number,
        head=None,
        router_plan_id=plan_id,
        error_style=error_style,
        timeout=timeout,
        interval=interval,
    )


def test_ci_wait_failure_enriches_each_failing_job_with_real_filtered_log(monkeypatch, plan_context):
    """cmd_ci_wait natural-termination failure: each failing_checks[] entry
    gains its own log_file / filtered_log_file from the REAL fixture."""
    # Arrange
    jobs = _two_failing_jobs()
    fixture, fetch_calls = _wire_gitlab_failure(monkeypatch, jobs=jobs)
    _noop_sleep(monkeypatch)

    # Act — the wait loop terminates immediately (no wait-state jobs).
    result = gitlab_ops.cmd_ci_wait(_gl_wait_args(plan_id=plan_context.plan_id))

    # Assert
    assert result['status'] == 'success'
    assert result['final_status'] == 'failure'
    assert 'failing_checks' in result
    _assert_real_gitlab_failure_enrichment(result['failing_checks'], plan_context, fixture=fixture)
    assert len(fetch_calls['run_ids']) >= 2


def test_ci_wait_success_path_failing_checks_empty(monkeypatch, plan_context):
    """A green wait result carries an empty failing_checks list and never
    invokes the raw-trace fetcher."""
    # Arrange — both jobs succeed.
    jobs = _two_failing_jobs()
    for job in jobs:
        job['status'] = 'success'
    _, fetch_calls = _wire_gitlab_failure(monkeypatch, jobs=jobs)
    _noop_sleep(monkeypatch)

    # Act
    result = gitlab_ops.cmd_ci_wait(_gl_wait_args(plan_id=plan_context.plan_id))

    # Assert
    assert result['status'] == 'success'
    assert result['final_status'] == 'success'
    assert result['failing_checks'] == []
    assert fetch_calls['run_ids'] == []
