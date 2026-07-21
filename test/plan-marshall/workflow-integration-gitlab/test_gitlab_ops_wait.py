#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""GitLab-specific coverage for the ci/issue wait surface of gitlab_ops.py.

The provider-agnostic poll-handler contract — dispatch-table registration, the
auth short-circuit, and the flip/timeout/``--expected`` matrix for the three
wait-for-* handlers — lives in ``_ci_wait_contract`` and is bound into this
module below, so it executes once for GitLab. What remains here is genuinely
GitLab-specific:

    - the ``glab``-shaped stub wiring (``run_glab`` / ``_GlStub``)
    - the ``glab ci trace`` failure-path download + filter wiring, driven
      against the committed ``ci-logs/gitlab/fail.log`` fixture
    - the p50-seeded first sleep and the ``glab ci status --wait`` terminal-state
      tail, whose seams live in ``gitlab_ops``

Tests never shell out to the real ``glab`` CLI: every fetch helper and the auth
check are monkeypatched, and ``time.sleep`` is neutralised so timeout branches
run in constant time.
"""

import argparse
import json

import gitlab_ops
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

# Real committed GitLab-job-trace-shaped failure log fixture. Fed as the mocked
# ``glab ci trace`` raw-trace source so the failure-path download + filter +
# store wiring is validated against REAL log content (not a toy string).
_GITLAB_FAIL_LOG = CI_LOG_FIXTURE_ROOT / 'gitlab' / 'fail.log'


@pytest.fixture
def ci_ops():
    """Feed the provider-agnostic contract this module's provider ops module."""
    return gitlab_ops


def test_contract_surface_is_bound_for_gitlab():
    """Every provider-agnostic contract test is bound in this module.

    Guards the "the contract runs once per provider" invariant: a contract test
    added to ``_ci_wait_contract`` but never imported here would otherwise be
    silently uncollected for GitLab.
    """
    missing = [name for name in CONTRACT_TESTS if name not in globals()]
    assert missing == [], missing


# =============================================================================
# Failure-path log download + filter wiring — GitLab provider
# =============================================================================
#
# Drives cmd_ci_status / cmd_ci_wait end-to-end through the failure branch with
# the REAL committed GitLab failure fixture (fixtures/ci-logs/gitlab/fail.log)
# standing in for the ``glab ci trace`` raw-trace source. ``check_auth`` and
# ``run_glab`` are monkeypatched so no real ``glab`` CLI runs, while the
# download+filter+store hook (ci_base.enrich_failing_checks_with_logs ->
# manage-ci-artifacts.persist -> _ci_log_filter.filter_log) executes for real
# against the fixture content. The ``plan_context`` fixture redirects
# PLAN_BASE_DIR so persist writes the per-run artifact tree under tmp rather
# than the repo-local .plan/.


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

    def fake_fetch_trace(run_id, job_id=''):
        fetch_calls['run_ids'].append(str(run_id))
        return fixture

    monkeypatch.setattr(gitlab_ops, '_fetch_failed_job_trace', fake_fetch_trace)
    return fixture, fetch_calls


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
    jobs = _two_failing_jobs()
    fixture, fetch_calls = _wire_gitlab_failure(monkeypatch, jobs=jobs)

    result = gitlab_ops.cmd_ci_status(_gl_status_args(plan_id=plan_context.plan_id))

    assert result['status'] == 'success'
    assert result['overall_status'] == 'failure'
    assert 'failing_checks' in result
    _assert_real_gitlab_failure_enrichment(result['failing_checks'], plan_context, fixture=fixture)
    # The raw-trace fetcher was driven once per failing job (shared run id).
    assert len(fetch_calls['run_ids']) >= 2


def test_ci_status_success_path_has_no_failing_checks_key(monkeypatch, plan_context):
    """A green pipeline leaves the success TOON unchanged — no failing_checks,
    and the raw-trace fetcher is never invoked."""
    jobs = _two_failing_jobs()
    for job in jobs:
        job['status'] = 'success'
    _, fetch_calls = _wire_gitlab_failure(monkeypatch, jobs=jobs)

    result = gitlab_ops.cmd_ci_status(_gl_status_args(plan_id=plan_context.plan_id))

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
    jobs = _two_failing_jobs()
    fixture, fetch_calls = _wire_gitlab_failure(monkeypatch, jobs=jobs)
    _noop_sleep(monkeypatch)

    # The wait loop terminates immediately (no wait-state jobs).
    result = gitlab_ops.cmd_ci_wait(_gl_wait_args(plan_id=plan_context.plan_id))

    assert result['status'] == 'success'
    assert result['final_status'] == 'failure'
    assert 'failing_checks' in result
    _assert_real_gitlab_failure_enrichment(result['failing_checks'], plan_context, fixture=fixture)
    assert len(fetch_calls['run_ids']) >= 2


def test_ci_wait_success_path_failing_checks_empty(monkeypatch, plan_context):
    """A green wait result carries an empty failing_checks list and never
    invokes the raw-trace fetcher."""
    jobs = _two_failing_jobs()
    for job in jobs:
        job['status'] = 'success'
    _, fetch_calls = _wire_gitlab_failure(monkeypatch, jobs=jobs)
    _noop_sleep(monkeypatch)

    result = gitlab_ops.cmd_ci_wait(_gl_wait_args(plan_id=plan_context.plan_id))

    assert result['status'] == 'success'
    assert result['final_status'] == 'success'
    assert result['failing_checks'] == []
    assert fetch_calls['run_ids'] == []


# =============================================================================
# p50-seeded first sleep + terminal-state watch-verb tail
# =============================================================================
#
# Drives the reworked cmd_ci_wait: a p50 first-sleep seed then a ``glab ci
# status --wait`` terminal-state tail. The p50 read / record seams, the sleep
# seam, the watch-pipeline seam, and the monotonic clock all live in
# ``gitlab_ops`` and are monkeypatched there; ``check_auth`` / ``run_glab``
# remain patched too.


def _job_row(name, status, *, pipeline_id=5005):
    """Build a single GitLab job row.

    ``status`` drives the canonical partition: ``running`` (wait), ``success``
    (non-failing), ``failed`` (failing).
    """
    return {
        'name': name,
        'status': status,
        'stage': 'test',
        'pipeline_id': pipeline_id,
        'web_url': f'https://gitlab.example.com/o/r/-/jobs/{name}',
    }


class _GlStub:
    """Stateful ``run_glab`` seam: ``mr view`` returns a pipeline envelope, ``ci
    view`` returns ``pending_jobs`` until the watch verb flips ``watched`` True,
    then ``terminal_jobs``. Any other call returns an empty JSON object."""

    def __init__(self, pending_jobs, terminal_jobs, *, pipeline_id=5005):
        self.pending_jobs = pending_jobs
        self.terminal_jobs = terminal_jobs
        self.pipeline_id = pipeline_id
        self.watched = False

    def __call__(self, args):
        if args[:2] == ['mr', 'view']:
            status = 'success' if self.watched else 'running'
            return 0, json.dumps({'pipeline': {'id': self.pipeline_id, 'status': status}, 'sha': 'feedface'}), ''
        if args[:2] == ['ci', 'view']:
            jobs = self.terminal_jobs if self.watched else self.pending_jobs
            return 0, json.dumps({'jobs': jobs}), ''
        return 0, json.dumps({}), ''


def _gl_p50_wait_args(*, pr_number=88, plan_id, timeout=600, interval=0):
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

    The stub only serves terminal jobs once ``glab ci status --wait`` has run
    against the running pipeline, so ``wait_outcome == 'completed'`` with that
    pipeline's id is the observable proof that the watch tail drove the
    completion — no assertion on the watch seam's call sequence is needed.
    """
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    stub = _GlStub(
        pending_jobs=[_job_row('verify', 'running')],
        terminal_jobs=[_job_row('verify', 'success')],
    )
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    monkeypatch.setattr(gitlab_ops, '_read_ci_wait_p50_seed', lambda: 120)
    monkeypatch.setattr(gitlab_ops, '_sleep_seed', lambda s: None)
    monkeypatch.setattr(gitlab_ops, '_monotonic', _make_incrementing_clock())

    def fake_watch(pipeline_id, timeout):
        stub.watched = True
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, '_watch_pipeline', fake_watch)
    recorded: list[int] = []
    monkeypatch.setattr(gitlab_ops, '_record_ci_wait_duration', lambda d: recorded.append(d))

    result = gitlab_ops.cmd_ci_wait(_gl_p50_wait_args(plan_id=plan_context.plan_id, timeout=600))

    assert result['status'] == 'success'
    assert result['final_status'] == 'success'
    assert result['wait_outcome'] == 'completed'
    assert result['run_id'] == '5005'
    # Observed wall-clock duration recorded back into the p50 window on success.
    assert len(recorded) == 1 and recorded[0] > 0


def test_ci_wait_p50_seed_skipped_on_empty_window(monkeypatch, plan_context):
    """An empty p50 window (None) skips the first-sleep seed; an already-terminal
    pipeline needs no watch."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    stub = _GlStub(
        pending_jobs=[_job_row('verify', 'success')],
        terminal_jobs=[_job_row('verify', 'success')],
    )
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    monkeypatch.setattr(gitlab_ops, '_read_ci_wait_p50_seed', lambda: None)
    seed_sleeps: list[int] = []
    monkeypatch.setattr(gitlab_ops, '_sleep_seed', lambda s: seed_sleeps.append(s))
    monkeypatch.setattr(gitlab_ops, '_record_ci_wait_duration', lambda d: None)

    watch_calls: list[str] = []

    def fake_watch(pipeline_id, timeout):
        watch_calls.append(pipeline_id)
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, '_watch_pipeline', fake_watch)

    result = gitlab_ops.cmd_ci_wait(_gl_p50_wait_args(plan_id=plan_context.plan_id))

    assert result['final_status'] == 'success'
    # An absent window must produce no sleep at all — the seam records nothing.
    assert seed_sleeps == []
    # An already-terminal pipeline has no wait partition, so nothing is watched.
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
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    stub = _GlStub(
        pending_jobs=[_job_row('verify', 'success')],
        terminal_jobs=[_job_row('verify', 'success')],
    )
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    monkeypatch.setattr(gitlab_ops, '_read_ci_wait_p50_seed', lambda: seed)
    seed_sleeps: list[int] = []
    monkeypatch.setattr(gitlab_ops, '_sleep_seed', lambda s: seed_sleeps.append(s))
    monkeypatch.setattr(gitlab_ops, '_record_ci_wait_duration', lambda d: None)

    result = gitlab_ops.cmd_ci_wait(_gl_p50_wait_args(plan_id=plan_context.plan_id, timeout=timeout))

    assert result['final_status'] == 'success'
    assert seed_sleeps == [expected_sleep]


def test_ci_wait_deadline_exceeded_preserved_when_still_pending(monkeypatch, plan_context):
    """A pipeline that never leaves the wait partition (even after the watch tail)
    yields the deadline_exceeded timeout envelope, and no duration is recorded."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    running = [_job_row('verify', 'running')]
    stub = _GlStub(pending_jobs=running, terminal_jobs=running)
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    monkeypatch.setattr(gitlab_ops, '_read_ci_wait_p50_seed', lambda: None)
    monkeypatch.setattr(gitlab_ops, '_sleep_seed', lambda s: None)
    monkeypatch.setattr(gitlab_ops, '_fetch_failed_job_trace', lambda run_id, job_id='': None)

    def fake_watch(pipeline_id, timeout):
        stub.watched = True
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, '_watch_pipeline', fake_watch)
    recorded: list[int] = []
    monkeypatch.setattr(gitlab_ops, '_record_ci_wait_duration', lambda d: recorded.append(d))

    result = gitlab_ops.cmd_ci_wait(_gl_p50_wait_args(plan_id=plan_context.plan_id))

    assert result['status'] == 'error'
    assert result['operation'] == 'ci_wait'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert 'failing_checks' in result
    assert result['run_id'] == '5005'
    assert recorded == []
