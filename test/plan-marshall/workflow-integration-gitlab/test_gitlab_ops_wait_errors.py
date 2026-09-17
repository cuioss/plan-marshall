#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_ops.py wait — failure enrichment.
"""

from __future__ import annotations

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
    test_ci_wait_for_status_flip_auth_failure_short_circuits,
    test_ci_wait_for_status_flip_completes_on_flip,
    test_ci_wait_for_status_flip_expected_any_accepts_failure,
    test_ci_wait_for_status_flip_expected_any_accepts_success,
    test_ci_wait_for_status_flip_expected_success_rejects_failure,
    test_ci_wait_for_status_flip_times_out_when_status_never_changes,
    test_dispatch_ci_wait_for_status_flip_registered,
    test_dispatch_issue_wait_for_close_registered,
    test_dispatch_issue_wait_for_label_registered,
    test_issue_wait_for_close_auth_failure_short_circuits,
    test_issue_wait_for_close_completes_on_flip,
    test_issue_wait_for_close_times_out_when_state_never_changes,
    test_issue_wait_for_label_absent_completes_when_label_disappears,
    test_issue_wait_for_label_auth_failure_short_circuits,
    test_issue_wait_for_label_present_completes_when_label_appears,
    test_issue_wait_for_label_times_out_when_label_state_never_changes,
)


_GITLAB_FAIL_LOG = CI_LOG_FIXTURE_ROOT / 'gitlab' / 'fail.log'


@pytest.fixture
def ci_ops():
    """Feed the provider-agnostic contract this module's provider ops module."""
    return gitlab_ops


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
        {
            'name': 'quality-gate',
            'status': 'failed',
            'stage': 'test',
            'pipeline_id': 5005,
            'web_url': 'https://gitlab.example.com/o/r/-/jobs/8001',
        },
        {
            'name': 'verify',
            'status': 'failed',
            'stage': 'test',
            'pipeline_id': 5005,
            'web_url': 'https://gitlab.example.com/o/r/-/jobs/8002',
        },
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


def _gl_wait_args(*, pr_number=88, plan_id, error_style='generic', timeout=5, interval=0):
    return argparse.Namespace(
        pr_number=pr_number,
        head=None,
        router_plan_id=plan_id,
        error_style=error_style,
        timeout=timeout,
        interval=interval,
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

