#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The failing-check log pointer: filled when it can be, otherwise reasoned.

``ci checks status`` reports ``log_file`` / ``filtered_log_file`` on every
failing check. Two empty strings alone cannot tell a reader whether the log is
missing by design, unavailable because the call carried no plan, or failed to
download — so the enrich hook states the reason beside the empty pointer.
"""

from __future__ import annotations

import ci_base


def _check(name: str = 'build', run_id: str = '987654') -> dict:
    """Build a minimal failing-check entry for the enrich hook."""
    return {
        'name': name,
        'job_name': name,
        'workflow_name': 'ci',
        'conclusion': 'failure',
        'run_id': run_id,
        'started_at': '2026-05-19T00:00:00Z',
        'completed_at': '2026-05-19T00:01:00Z',
        'run_url': 'https://example/runs/987654/job/1',
        'head_sha': 'cafef00d',
        'pr_number': 7,
    }


def _enrich(entry: dict, *, plan_id: str | None, fetcher) -> dict:
    """Run the shared hook over one entry and return it."""
    return ci_base.enrich_failing_checks_with_logs(
        failing_checks=[entry],
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )[0]


def _stub_persist(result: dict):
    """Return a persist stand-in that always answers ``result``."""

    def persist(**_kwargs) -> dict:
        return result

    return persist


def test_a_check_with_no_plan_reports_no_plan_id():
    """Without a plan there is nowhere to persist a log — and the entry says so."""
    entry = _enrich(_check(), plan_id=None, fetcher=lambda *_args: 'raw log')

    assert entry['log_file'] == ''
    assert entry['filtered_log_file'] == ''
    assert entry['log_unavailable_reason'] == 'no_plan_id'


def test_a_check_without_a_run_id_reports_no_run_id():
    """A missing run id is reported as itself, not as a generic empty pointer."""
    entry = _enrich(_check(run_id=''), plan_id='p', fetcher=lambda *_args: 'raw log')

    assert entry['log_file'] == ''
    assert entry['log_unavailable_reason'] == 'no_run_id'


def test_a_log_that_could_not_be_fetched_reports_the_reason(monkeypatch):
    """A fetcher that yields nothing is named, never left as a bare empty string."""
    monkeypatch.setattr(ci_base, '_load_persist', lambda: _stub_persist({'status': 'success'}))

    entry = _enrich(_check(), plan_id='p', fetcher=lambda *_args: None)

    assert entry['log_file'] == ''
    assert entry['log_unavailable_reason'] == 'log_fetch_failed'


def test_a_failed_persist_is_reported_as_its_own_reason(monkeypatch):
    """A persist that refuses is distinguishable from a download that failed."""
    monkeypatch.setattr(ci_base, '_load_persist', lambda: _stub_persist({'status': 'error', 'error': 'boom'}))

    entry = _enrich(_check(), plan_id='p', fetcher=lambda *_args: 'raw log')

    assert entry['log_file'] == ''
    assert entry['log_unavailable_reason'] == 'persist_failed'


def test_a_persisted_log_fills_both_pointers_and_drops_the_reason(monkeypatch):
    """The success path carries both paths and no reason."""
    paths = {
        'status': 'success',
        'log_paths': ['artifacts/ci-runs/987654/build.log'],
        'filtered_log_paths': ['artifacts/ci-runs/987654/build.filtered.log'],
    }
    monkeypatch.setattr(ci_base, '_load_persist', lambda: _stub_persist(paths))

    entry = _enrich(_check(), plan_id='p', fetcher=lambda *_args: 'raw log')

    assert entry['log_file'].endswith('artifacts/ci-runs/987654/build.log')
    assert entry['filtered_log_file'].endswith('artifacts/ci-runs/987654/build.filtered.log')
    assert not entry.get('log_unavailable_reason', '')


def test_a_re_enrichment_clears_a_stale_reason(monkeypatch):
    """A later success must not keep the reason an earlier attempt recorded."""
    paths = {
        'status': 'success',
        'log_paths': ['artifacts/ci-runs/987654/build.log'],
        'filtered_log_paths': ['artifacts/ci-runs/987654/build.filtered.log'],
    }
    monkeypatch.setattr(ci_base, '_load_persist', lambda: _stub_persist(paths))
    entry = _check()
    entry['log_unavailable_reason'] = 'log_fetch_failed'

    enriched = _enrich(entry, plan_id='p', fetcher=lambda *_args: 'raw log')

    assert 'log_unavailable_reason' not in enriched


def test_a_missing_filtered_path_is_reported(monkeypatch):
    """One filled pointer beside one empty one is still an explained empty."""
    paths = {
        'status': 'success',
        'log_paths': ['artifacts/ci-runs/987654/build.log'],
        'filtered_log_paths': [],
    }
    monkeypatch.setattr(ci_base, '_load_persist', lambda: _stub_persist(paths))

    entry = _enrich(_check(), plan_id='p', fetcher=lambda *_args: 'raw log')

    assert entry['log_file'].endswith('artifacts/ci-runs/987654/build.log')
    assert entry['filtered_log_file'] == ''
    assert entry['log_unavailable_reason'] == 'log_path_missing'
