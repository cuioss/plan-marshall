#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Accessors cluster of manage-ci-artifacts tests.

Behaviour scope: ``read`` / ``list`` / ``read_latest`` accessors —
missing-run errors, empty-list, read-latest selection by
``fetched_at`` timestamp (never lexicographic run_id), log-path
surfacing, and the no-runs error envelope.

Moved byte-for-byte from ``test_manage_ci_artifacts.py`` — no
behavioural edit, no class split.
"""

from __future__ import annotations

from conftest import get_scripts_dir, load_script_module

_SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'manage-ci-artifacts')


def _load_module(name: str, filename: str):
    return load_script_module('plan-marshall', 'manage-ci-artifacts', filename, name)


_mod = _load_module('manage_ci_artifacts', 'manage-ci-artifacts.py')
persist = _mod.persist
read_manifest = _mod.read_manifest
read_latest_manifest = _mod.read_latest_manifest
list_runs = _mod.list_runs
cmd_persist = _mod.cmd_persist
cmd_read = _mod.cmd_read
_run_dir = _mod._run_dir
_manifest_path = _mod._manifest_path
_safe_job_filename = _mod._safe_job_filename
parse_toon = _mod.parse_toon
serialize_toon = _mod.serialize_toon


def _rewrite_manifest_timestamp(plan_id: str, run_id: str, fetched_at: str) -> None:
    """Post-mutate a persisted manifest's ``fetched_at`` field.

    The persist() call writes a timestamp via ``datetime.now(UTC)``; tests
    that need to pin recency-by-timestamp (rather than recency-by-call-
    order) rewrite the field directly. The manifest file is small TOON;
    parse, mutate, serialize, write.
    """
    path = _manifest_path(plan_id, run_id)
    manifest = parse_toon(path.read_text(encoding='utf-8'))
    manifest['fetched_at'] = fetched_at
    path.write_text(serialize_toon(manifest), encoding='utf-8')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_fetcher(provider: str, run_id: str, job: dict) -> str:
    return f'STUB-LOG provider={provider} run_id={run_id} name={job.get("name", "")}\n'


def _job(name: str, conclusion: str = 'success') -> dict:
    return {
        'name': name,
        'conclusion': conclusion,
        'workflow_name': 'ci',
        'job_name': name,
        'started_at': '2026-05-19T00:00:00Z',
        'completed_at': '2026-05-19T00:01:00Z',
        'run_url': 'https://example/runs/x',
    }


# ---------------------------------------------------------------------------
# read / list edge cases
# ---------------------------------------------------------------------------


def test_read_missing_run_returns_error(plan_context):
    plan_id = 'ci-artifacts-missing'
    result = read_manifest(plan_id=plan_id, run_id='does-not-exist')
    assert result['status'] == 'error'


def test_list_empty_returns_zero_runs(plan_context):
    plan_id = 'ci-artifacts-empty-list'
    result = list_runs(plan_id=plan_id)
    assert result['status'] == 'success'
    assert result['run_count'] == 0


# ---------------------------------------------------------------------------
# read --latest accessor. Recency is decided by the
# manifest fetched_at timestamp, NEVER by lexicographic run_id sorting.
# ---------------------------------------------------------------------------


def test_read_latest_selects_newest_by_fetched_at_not_run_id(plan_context):
    """When run_id ordering and fetched_at ordering disagree, --latest MUST
    follow fetched_at. The test persists three runs whose run_ids would
    sort the OPPOSITE direction from their fetched_at values, then asserts
    that read_latest_manifest picks the timestamp-newest one.
    """
    plan_id = 'ci-artifacts-latest-by-timestamp'
    # Persist three runs. Then rewrite each manifest's fetched_at so
    # the chronological order is REVERSED relative to lexicographic
    # run_id order: run_id '001' gets the newest timestamp, '003'
    # gets the oldest. A run_id-sorted implementation would pick
    # '003' (lexicographic last); a timestamp-sorted implementation
    # MUST pick '001'.
    for run_id, sha in [
        ('001', 'sha-A'),
        ('002', 'sha-B'),
        ('003', 'sha-C'),
    ]:
        persist(
            plan_id=plan_id,
            run_id=run_id,
            head_sha=sha,
            pr_number=1,
            provider='github',
            jobs=[_job('build')],
            log_fetcher=_stub_fetcher,
        )
    # Reverse: '001' newest, '003' oldest.
    _rewrite_manifest_timestamp(plan_id, '001', '2026-12-31T23:59:59Z')
    _rewrite_manifest_timestamp(plan_id, '002', '2026-06-15T12:00:00Z')
    _rewrite_manifest_timestamp(plan_id, '003', '2026-01-01T00:00:00Z')

    result = read_latest_manifest(plan_id=plan_id)
    assert result['status'] == 'success', result
    assert result['run_id'] == '001', (
        f'read_latest_manifest selected {result["run_id"]!r}; '
        'expected "001" (the timestamp-newest manifest, even though '
        'it is lexicographically smallest)'
    )
    assert result['manifest']['head_sha'] == 'sha-A'


def test_read_latest_returns_log_paths(plan_context):
    """The --latest accessor returns the same shape as --run-id, including
    a populated ``log_paths`` list when the manifest has jobs with log
    paths.
    """
    plan_id = 'ci-artifacts-latest-log-paths'
    persist(
        plan_id=plan_id,
        run_id='42',
        head_sha='cafef00d',
        pr_number=1,
        provider='github',
        jobs=[_job('build'), _job('lint')],
        log_fetcher=_stub_fetcher,
    )

    result = read_latest_manifest(plan_id=plan_id)
    assert result['status'] == 'success'
    assert result['run_id'] == '42'
    # log_paths is sorted; both jobs persisted produce non-empty paths.
    assert len(result['log_paths']) == 2
    for path in result['log_paths']:
        assert path, 'log_paths entry must be non-empty'


def test_read_latest_errors_cleanly_when_no_runs_persisted(plan_context):
    """With no manifests under artifacts/ci-runs/, --latest MUST return a
    structured error envelope rather than crashing or returning bogus
    data.
    """
    plan_id = 'ci-artifacts-latest-empty'
    result = read_latest_manifest(plan_id=plan_id)
    assert result['status'] == 'error'
    assert result.get('error') == 'no_persisted_runs'
    assert result['plan_id'] == plan_id
