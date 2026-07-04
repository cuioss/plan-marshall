#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for gitlab_ops.py CI conclusion-state aggregation.

Mirror of test_workflow_integration_github_ci_aggregation.py for the GitLab
provider. Locks the canonical job-status → partition mapping established in
lesson-2026-05-18-16-001 deliverable 4:

    non-failing : success | skipped | manual
    failing     : failed | canceled | <unknown future status>
    wait        : created | pending | running | preparing | scheduled |
                  waiting_for_resource | <empty/null>

The aggregation seam appears in three call sites:

    _classify_check_buckets       — the partition helper (jobs in, partition out)
    cmd_ci_status                 — sync overall-status read
    cmd_ci_wait                   — wait-loop final_status
    _fetch_pr_overall_ci_status   — used by ci_wait_for_status_flip

The ``mixed`` outcome was deleted as part of the lesson — every input must
now resolve to one of ``pending | success | failure | none``.

Tests use the conftest run_glab monkeypatch seam — no live ``glab``
invocations.
"""

import argparse
import time

import ci_base
import gitlab_ops

# =============================================================================
# Helpers
# =============================================================================


def _job(status: str, name: str = 'job', stage: str = '', web_url: str = '') -> dict:
    """Build a minimal GitLab job row matching ``glab ci view --output json``."""
    return {
        'name': name,
        'status': status,
        'stage': stage,
        'web_url': web_url,
        'started_at': '',
        'finished_at': '',
        'created_at': '',
    }


def _ok_auth():
    return True, ''


def _noop_sleep(monkeypatch):
    monkeypatch.setattr(ci_base.time, 'sleep', lambda *_a, **_kw: None)
    monkeypatch.setattr(time, 'sleep', lambda *_a, **_kw: None)


# =============================================================================
# _classify_check_buckets — single-status partition table
# =============================================================================


def test_classify_success_is_non_failing():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('success')])
    assert failing == [] and wait == [] and len(non_failing) == 1


def test_classify_skipped_is_non_failing():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('skipped')])
    assert failing == [] and wait == [] and len(non_failing) == 1


def test_classify_manual_is_non_failing():
    """Manual jobs are operator gates, not failures."""
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('manual')])
    assert failing == [] and wait == [] and len(non_failing) == 1


def test_classify_failed_is_failing():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('failed')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_canceled_is_failing():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('canceled')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_created_is_wait():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('created')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_pending_is_wait():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('pending')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_running_is_wait():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('running')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_preparing_is_wait():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('preparing')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_scheduled_is_wait():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('scheduled')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_waiting_for_resource_is_wait():
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('waiting_for_resource')])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_null_status_is_wait():
    """A missing/null ``status`` field normalises to empty-string → wait partition."""
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([{'name': 'x'}])
    assert failing == [] and len(wait) == 1 and non_failing == []


def test_classify_unknown_status_defaults_to_failing():
    """Defense-in-depth: unknown future statuses land in the failing bucket."""
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('new_future_value')])
    assert len(failing) == 1 and wait == [] and non_failing == []


def test_classify_case_insensitive_normalisation():
    """``_normalize_job_status`` lower-cases the raw status, so upper-case input still partitions."""
    failing, wait, non_failing = gitlab_ops._classify_check_buckets([_job('SUCCESS')])
    assert failing == [] and wait == [] and len(non_failing) == 1


# =============================================================================
# _derive_overall_status — mixed-fixture aggregation
# =============================================================================


def test_derive_empty_returns_none():
    status, failing, wait = gitlab_ops._derive_overall_status([])
    assert status == 'none' and failing == [] and wait == []


def test_derive_success_plus_skipped_returns_success():
    jobs = [_job('success', name='build'), _job('skipped', name='license')]
    status, failing, wait = gitlab_ops._derive_overall_status(jobs)
    assert status == 'success' and failing == [] and wait == []


def test_derive_success_plus_manual_returns_success():
    jobs = [_job('success', name='build'), _job('manual', name='deploy-prod')]
    status, failing, _ = gitlab_ops._derive_overall_status(jobs)
    assert status == 'success'


def test_derive_success_plus_skipped_plus_manual_returns_success():
    jobs = [_job('success'), _job('skipped'), _job('manual')]
    status, failing, _ = gitlab_ops._derive_overall_status(jobs)
    assert status == 'success' and failing == []


def test_derive_success_plus_failed_returns_failure_with_failing_names():
    jobs = [_job('success', name='build'), _job('failed', name='lint')]
    status, failing, wait = gitlab_ops._derive_overall_status(jobs)
    assert status == 'failure'
    assert [c.get('name') for c in failing] == ['lint']
    assert wait == []


def test_derive_success_plus_canceled_returns_failure():
    jobs = [_job('success', name='build'), _job('canceled', name='test')]
    status, failing, _ = gitlab_ops._derive_overall_status(jobs)
    assert status == 'failure'
    assert [c.get('name') for c in failing] == ['test']


def test_derive_skipped_plus_manual_plus_canceled_returns_failure():
    """One failing partition member is enough to flip the aggregate."""
    jobs = [_job('skipped'), _job('manual'), _job('canceled', name='dep-review')]
    status, failing, _ = gitlab_ops._derive_overall_status(jobs)
    assert status == 'failure'
    assert [c.get('name') for c in failing] == ['dep-review']


def test_derive_success_plus_running_returns_pending():
    """A single wait-state job forces the aggregate into ``pending``."""
    jobs = [_job('success', name='build'), _job('running', name='deploy')]
    status, failing, wait = gitlab_ops._derive_overall_status(jobs)
    assert status == 'pending'
    assert failing == []
    assert [c.get('name') for c in wait] == ['deploy']


def test_derive_failed_plus_running_returns_pending():
    """Wait dominates failure — caller must wait before declaring failure."""
    jobs = [_job('failed', name='lint'), _job('running', name='build')]
    status, failing, wait = gitlab_ops._derive_overall_status(jobs)
    assert status == 'pending'
    assert failing == []
    assert [c.get('name') for c in wait] == ['build']


# =============================================================================
# Lesson regression — equivalent to PR #410's [success, success, success, skipped] shape
# =============================================================================


def test_lesson_regression_three_successes_one_skipped_is_success():
    """Lesson-2026-05-18-16-001: the GitLab mirror of PR #410's CI shape
    ``[success, success, success, skipped]`` MUST aggregate to ``success``.

    Before the fix the legacy STATUS_MAP at lines ~711-714 / ~850-853 also
    silently mis-bucketed success-plus-skipped via fall-through.
    """
    jobs = [
        _job('success', name='build'),
        _job('success', name='test'),
        _job('success', name='lint'),
        _job('skipped', name='license-check'),
    ]
    status, failing, wait = gitlab_ops._derive_overall_status(jobs)
    assert status == 'success', f'Lesson regression: expected success, got {status}'
    assert failing == []
    assert wait == []


# =============================================================================
# cmd_ci_status — end-to-end with stubbed run_glab
# =============================================================================


def _ci_status_args(pr_number=42):
    return argparse.Namespace(pr_number=pr_number, head=None)


def _make_run_glab_returning(mr_json: str, ci_view_json: str = '{"jobs": []}'):
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        if args[:2] == ['mr', 'view']:
            return 0, mr_json, ''
        if args[:2] == ['ci', 'view']:
            return 0, ci_view_json, ''
        return 0, '', ''

    return run_glab_stub, captured


def _mr_view_json(jobs_list: list[dict], pipeline_status: str = 'success', pipeline_id: int = 99) -> tuple[str, str]:
    """Build (mr_view_json, ci_view_json) pair for cmd_ci_status fixtures."""
    import json as _json

    mr = {
        'iid': 42,
        'pipeline': {'id': pipeline_id, 'status': pipeline_status},
        'sha': 'cafef00d',
        'diff_refs': {'head_sha': 'cafef00d'},
    }
    ci = {'jobs': jobs_list}
    return _json.dumps(mr), _json.dumps(ci)


def test_ci_status_returns_success_for_all_passing(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    mr_json, ci_json = _mr_view_json([_job('success', name='build')], pipeline_status='success')
    stub, _ = _make_run_glab_returning(mr_json, ci_json)
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    result = gitlab_ops.cmd_ci_status(_ci_status_args())

    assert result['status'] == 'success'
    assert result['overall_status'] == 'success'
    assert result['check_count'] == 1


def test_ci_status_returns_success_for_pass_plus_skipped(monkeypatch):
    """The lesson regression at the cmd_ci_status call site."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    mr_json, ci_json = _mr_view_json(
        [_job('success', name='build'), _job('skipped', name='license')],
        pipeline_status='success',
    )
    stub, _ = _make_run_glab_returning(mr_json, ci_json)
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    result = gitlab_ops.cmd_ci_status(_ci_status_args())

    assert result['overall_status'] == 'success'


def test_ci_status_returns_failure_for_one_failed(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    mr_json, ci_json = _mr_view_json(
        [_job('success', name='build'), _job('failed', name='lint')],
        pipeline_status='failed',
    )
    stub, _ = _make_run_glab_returning(mr_json, ci_json)
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    result = gitlab_ops.cmd_ci_status(_ci_status_args())

    assert result['overall_status'] == 'failure'


def test_ci_status_returns_pending_for_one_running(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    mr_json, ci_json = _mr_view_json(
        [_job('success', name='build'), _job('running', name='deploy')],
        pipeline_status='running',
    )
    stub, _ = _make_run_glab_returning(mr_json, ci_json)
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    result = gitlab_ops.cmd_ci_status(_ci_status_args())

    assert result['overall_status'] == 'pending'


def test_ci_status_returns_none_for_empty_jobs_and_unknown_pipeline(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    # Pipeline with no status and no jobs → overall is ``none``.
    import json as _json

    mr_json = _json.dumps({'iid': 42, 'pipeline': {}})
    stub, _ = _make_run_glab_returning(mr_json, _json.dumps({'jobs': []}))
    monkeypatch.setattr(gitlab_ops, 'run_glab', stub)

    result = gitlab_ops.cmd_ci_status(_ci_status_args())

    assert result['overall_status'] == 'none'


# =============================================================================
# cmd_ci_wait — final_status derivation after wait completes
# =============================================================================


def _ci_wait_args(pr_number=42, timeout=5, interval=0):
    return argparse.Namespace(pr_number=pr_number, timeout=timeout, interval=interval)


def test_ci_wait_final_status_success_for_pass_plus_skipped(monkeypatch):
    """Lesson regression at the cmd_ci_wait call site — the precondition source."""
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    mr_json, ci_json = _mr_view_json(
        [_job('success', name='build'), _job('skipped', name='license')],
        pipeline_status='success',
        pipeline_id=77,
    )

    def run_glab_stub(args):
        if args[:2] == ['mr', 'view']:
            return 0, mr_json, ''
        if args[:2] == ['ci', 'view']:
            return 0, ci_json, ''
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_ci_wait(_ci_wait_args())

    assert result['status'] == 'success', result
    assert result['final_status'] == 'success'
    assert result['failing_checks'] == []
    assert result['wait_outcome'] == 'completed'
    assert result['run_id'] == '77'


def test_ci_wait_final_status_failure_lists_failing_checks(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    mr_json, ci_json = _mr_view_json(
        [
            _job('success', name='build', stage='build'),
            _job('failed', name='lint', stage='quality', web_url='https://gitlab/x/-/jobs/123'),
        ],
        pipeline_status='failed',
        pipeline_id=88,
    )

    def run_glab_stub(args):
        if args[:2] == ['mr', 'view']:
            return 0, mr_json, ''
        if args[:2] == ['ci', 'view']:
            return 0, ci_json, ''
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_ci_wait(_ci_wait_args())

    assert result['final_status'] == 'failure'
    assert [e['name'] for e in result['failing_checks']] == ['lint']
    assert result['failing_checks'][0]['conclusion'] == 'failed'
    assert result['failing_checks'][0]['workflow_name'] == 'quality'
    assert result['failing_checks'][0]['run_url'] == 'https://gitlab/x/-/jobs/123'
    assert result['wait_outcome'] == 'completed'
    assert result['run_id'] == '88'


def test_ci_wait_envelope_carries_head_sha(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    mr_json, ci_json = _mr_view_json([_job('success', name='build')], pipeline_status='success', pipeline_id=55)

    def run_glab_stub(args):
        if args[:2] == ['mr', 'view']:
            return 0, mr_json, ''
        if args[:2] == ['ci', 'view']:
            return 0, ci_json, ''
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_ci_wait(_ci_wait_args())

    assert result['head_sha'] == 'cafef00d'


# =============================================================================
# _fetch_pr_overall_ci_status — used by ci_wait_for_status_flip
# =============================================================================


def test_fetch_pr_overall_returns_success_for_success_pipeline(monkeypatch):
    import json as _json

    def run_glab_stub(args):
        if args[:2] == ['mr', 'view']:
            return 0, _json.dumps({'iid': 42, 'pipeline': {'status': 'success'}}), ''
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ok, status = gitlab_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'success'


def test_fetch_pr_overall_returns_success_for_skipped_pipeline(monkeypatch):
    """A pipeline status of ``skipped`` is non-failing."""
    import json as _json

    def run_glab_stub(args):
        if args[:2] == ['mr', 'view']:
            return 0, _json.dumps({'iid': 42, 'pipeline': {'status': 'skipped'}}), ''
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ok, status = gitlab_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'success'


def test_fetch_pr_overall_returns_failure_for_canceled_pipeline(monkeypatch):
    import json as _json

    def run_glab_stub(args):
        if args[:2] == ['mr', 'view']:
            return 0, _json.dumps({'iid': 42, 'pipeline': {'status': 'canceled'}}), ''
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ok, status = gitlab_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'failure'


def test_fetch_pr_overall_returns_pending_for_running_pipeline(monkeypatch):
    import json as _json

    def run_glab_stub(args):
        if args[:2] == ['mr', 'view']:
            return 0, _json.dumps({'iid': 42, 'pipeline': {'status': 'running'}}), ''
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ok, status = gitlab_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'pending'


def test_fetch_pr_overall_returns_none_for_no_pipeline(monkeypatch):
    import json as _json

    def run_glab_stub(args):
        if args[:2] == ['mr', 'view']:
            return 0, _json.dumps({'iid': 42, 'pipeline': None}), ''
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ok, status = gitlab_ops._fetch_pr_overall_ci_status(42)

    assert ok is True
    assert status == 'none'
