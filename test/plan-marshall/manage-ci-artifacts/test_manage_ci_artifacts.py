#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the manage-ci-artifacts persistence layer.

Lesson-2026-05-18-16-001 deliverable 7 success criteria pinned by this
file:

1. ``persist`` writes ``artifacts/ci-runs/{run_id}/`` containing one
   ``.log`` per job plus a ``manifest.toon`` enumerating every job.
2. ``head_sha`` is recorded in every manifest (loop-back ↔ commit
   auditability).
3. Multi-run persistence: N loop-back commits produce N+1 run
   directories — no directory is overwritten.
4. ``persist`` is idempotent: re-invoking for an existing ``run_id``
   re-emits the existing manifest without re-fetching logs.
5. ``read`` and ``list`` subcommands return the persisted state.

Tests use a deterministic ``log_fetcher`` injected via the ``persist``
keyword argument so no live CI / subprocess calls are required.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Module loading — load the script via importlib so we can call
# ``persist()`` / ``read_manifest()`` / ``list_runs()`` directly without
# spawning a subprocess.
#
# This test file lives at test/plan-marshall/manage-ci-artifacts/ — three
# path segments below the repo root — so the repo anchor walks four
# parents of ``__file__`` (file → manage-ci-artifacts → plan-marshall →
# test → repo root).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    _REPO_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-ci-artifacts'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


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
# _safe_job_filename
# ---------------------------------------------------------------------------


def test_safe_job_filename_passes_safe_names():
    assert _safe_job_filename('build') == 'build'
    assert _safe_job_filename('build-1') == 'build-1'
    assert _safe_job_filename('build_test') == 'build_test'


def test_safe_job_filename_sanitises_unsafe_chars():
    assert _safe_job_filename('build / test') == 'build_test'
    assert _safe_job_filename('build:matrix(1)') == 'build_matrix_1'


def test_safe_job_filename_empty_yields_unnamed_job():
    assert _safe_job_filename('') == 'unnamed-job'


# ---------------------------------------------------------------------------
# persist — happy path
# ---------------------------------------------------------------------------


def test_persist_writes_manifest_and_logs(plan_context):
    plan_id = 'ci-artifacts-happy'
    jobs = [_job('build', 'success'), _job('lint', 'failed')]
    result = persist(
        plan_id=plan_id,
        run_id='42',
        head_sha='cafef00d',
        pr_number=123,
        provider='github',
        jobs=jobs,
        log_fetcher=_stub_fetcher,
        wait_outcome='completed',
        final_status='failure',
    )

    assert result['status'] == 'success'
    assert result['already_persisted'] is False
    assert result['job_count'] == 2

    run_dir = _run_dir(plan_id, '42')
    assert (run_dir / 'manifest.toon').is_file()
    assert (run_dir / 'build.log').is_file()
    assert (run_dir / 'lint.log').is_file()
    # Log content is the stub fetcher's output (not the real CI log).
    assert 'STUB-LOG' in (run_dir / 'build.log').read_text(encoding='utf-8')


def test_persist_records_head_sha_in_manifest(plan_context):
    plan_id = 'ci-artifacts-head-sha'
    persist(
        plan_id=plan_id,
        run_id='42',
        head_sha='abc12345',
        pr_number=1,
        provider='github',
        jobs=[_job('build')],
        log_fetcher=_stub_fetcher,
    )
    result = read_manifest(plan_id=plan_id, run_id='42')
    assert result['status'] == 'success'
    assert result['manifest']['head_sha'] == 'abc12345'


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


def test_persist_is_idempotent_for_same_run_id(plan_context):
    plan_id = 'ci-artifacts-idempotent'
    jobs = [_job('build')]
    fetch_calls: list[str] = []

    def counting_fetcher(provider: str, run_id: str, job: dict) -> str:
        fetch_calls.append(job.get('name', ''))
        return f'log-{job.get("name", "")}\n'

    first = persist(
        plan_id=plan_id,
        run_id='99',
        head_sha='sha1',
        pr_number=1,
        provider='github',
        jobs=jobs,
        log_fetcher=counting_fetcher,
    )
    assert first['already_persisted'] is False
    assert len(fetch_calls) == 1

    second = persist(
        plan_id=plan_id,
        run_id='99',
        head_sha='sha1',
        pr_number=1,
        provider='github',
        jobs=jobs,
        log_fetcher=counting_fetcher,
    )
    assert second['already_persisted'] is True
    # The second call MUST NOT re-fetch logs — fetch_calls unchanged.
    assert len(fetch_calls) == 1


# ---------------------------------------------------------------------------
# Multi-run cascade
# ---------------------------------------------------------------------------


def test_multi_run_cascade_creates_independent_dirs(plan_context):
    plan_id = 'ci-artifacts-cascade'
    for run_id, sha in [('101', 'sha-A'), ('102', 'sha-B'), ('103', 'sha-C')]:
        persist(
            plan_id=plan_id,
            run_id=run_id,
            head_sha=sha,
            pr_number=42,
            provider='github',
            jobs=[_job('build')],
            log_fetcher=_stub_fetcher,
        )
    # All three run dirs exist independently.
    for run_id in ('101', '102', '103'):
        assert _manifest_path(plan_id, run_id).is_file()
    # ``list`` enumerates all three.
    listing = list_runs(plan_id=plan_id)
    assert listing['status'] == 'success'
    assert listing['run_count'] == 3
    run_ids = sorted(r['run_id'] for r in listing['runs'])
    assert run_ids == ['101', '102', '103']


def test_loop_back_does_not_overwrite_previous_run(plan_context):
    """A second persist with a NEW run_id MUST NOT touch the prior run's manifest."""
    plan_id = 'ci-artifacts-no-overwrite'
    persist(
        plan_id=plan_id,
        run_id='201',
        head_sha='sha-old',
        pr_number=1,
        provider='github',
        jobs=[_job('build')],
        log_fetcher=_stub_fetcher,
    )
    old_manifest_before = _manifest_path(plan_id, '201').read_text(encoding='utf-8')

    persist(
        plan_id=plan_id,
        run_id='202',
        head_sha='sha-new',
        pr_number=1,
        provider='github',
        jobs=[_job('build'), _job('lint')],
        log_fetcher=_stub_fetcher,
    )
    old_manifest_after = _manifest_path(plan_id, '201').read_text(encoding='utf-8')
    assert old_manifest_before == old_manifest_after, (
        'Loop-back commit must not modify a previous run directory'
    )


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
# Empty run_id rejected
# ---------------------------------------------------------------------------


def test_persist_rejects_empty_run_id(plan_context):
    plan_id = 'ci-artifacts-empty-run-id'
    result = persist(
        plan_id=plan_id,
        run_id='',
        head_sha='abc',
        pr_number=1,
        provider='github',
        jobs=[],
        log_fetcher=_stub_fetcher,
    )
    assert result['status'] == 'error'
    assert 'run_id' in result['error']


# ---------------------------------------------------------------------------
# cmd_persist with a populated --jobs-file — deliverable 3. The CLI surface
# accepts a JSON file path so the green-CI path can persist per-job
# evidence. The manifest MUST carry one jobs[] row per input job, each with
# a non-empty log_path, and the manifest+return MUST be labelled
# jobs_source: enumerated.
# ---------------------------------------------------------------------------


def _persist_args(**overrides) -> argparse.Namespace:
    """Build an argparse.Namespace matching the ``persist`` subparser."""
    base = {
        'plan_id': 'ci-artifacts-cmd-jobs',
        'run_id': '777',
        'head_sha': 'deadbeef',
        'pr_number': 55,
        'provider': 'github',
        'jobs_file': None,
        'wait_outcome': 'completed',
        'final_status': 'success',
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_cmd_persist_with_populated_jobs_file_writes_job_rows(tmp_path, capsys, plan_context):
    """cmd_persist handed a non-empty --jobs-file MUST write one jobs[]
    manifest row per input job, each with a non-empty log_path, and label
    the manifest jobs_source: enumerated.
    """
    plan_id = 'ci-artifacts-cmd-jobs-populated'
    jobs = [_job('build', 'success'), _job('lint', 'success')]
    jobs_file = tmp_path / 'jobs.json'
    jobs_file.write_text(json.dumps(jobs), encoding='utf-8')

    exit_code = cmd_persist(
        _persist_args(
            plan_id=plan_id,
            run_id='777',
            jobs_file=str(jobs_file),
        )
    )
    assert exit_code == 0
    # The captured TOON output carries jobs_source + job_count.
    out = capsys.readouterr().out
    assert 'jobs_source: enumerated' in out
    assert 'job_count: 2' in out

    # The persisted manifest enumerates both jobs with log paths.
    result = read_manifest(plan_id=plan_id, run_id='777')
    assert result['status'] == 'success'
    manifest = result['manifest']
    assert manifest['jobs_source'] == 'enumerated'
    manifest_jobs = manifest['jobs']
    assert len(manifest_jobs) == 2
    assert {j['name'] for j in manifest_jobs} == {'build', 'lint'}
    for row in manifest_jobs:
        assert row['log_path'], (
            f'job row {row["name"]!r} has an empty log_path — the '
            'green-CI persist path must record per-job evidence'
        )


def test_cmd_persist_with_empty_jobs_file_labels_zero_jobs_manifest(
    tmp_path, capsys, plan_context
):
    """An empty --jobs-file MUST produce a clearly-labelled zero-jobs
    manifest (jobs_source: empty) rather than silently looking like a
    run where no CI executed.
    """
    plan_id = 'ci-artifacts-cmd-jobs-empty'
    jobs_file = tmp_path / 'jobs-empty.json'
    jobs_file.write_text('[]', encoding='utf-8')

    exit_code = cmd_persist(
        _persist_args(
            plan_id=plan_id,
            run_id='778',
            jobs_file=str(jobs_file),
        )
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'jobs_source: empty' in out
    assert 'job_count: 0' in out

    result = read_manifest(plan_id=plan_id, run_id='778')
    assert result['status'] == 'success'
    assert result['manifest']['jobs_source'] == 'empty'
    assert (result['manifest'].get('jobs') or []) == []


def test_cmd_persist_without_jobs_file_labels_empty_source(capsys, plan_context):
    """A missing --jobs-file (None) is treated the same as an empty file —
    the manifest is labelled jobs_source: empty.
    """
    plan_id = 'ci-artifacts-cmd-jobs-missing'
    exit_code = cmd_persist(
        _persist_args(
            plan_id=plan_id,
            run_id='779',
            jobs_file=None,
        )
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'jobs_source: empty' in out

    result = read_manifest(plan_id=plan_id, run_id='779')
    assert result['status'] == 'success'
    assert result['manifest']['jobs_source'] == 'empty'


# ---------------------------------------------------------------------------
# read --latest accessor — deliverable 4. Recency is decided by the
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


def test_cmd_read_latest_dispatches_to_latest_accessor(capsys, plan_context):
    """The ``read --latest`` CLI surface MUST route through
    read_latest_manifest. We assert via the captured TOON output rather
    than monkeypatching so the test pins the full CLI plumbing.
    """
    plan_id = 'ci-artifacts-cmd-latest'
    persist(
        plan_id=plan_id,
        run_id='888',
        head_sha='c0ffee',
        pr_number=1,
        provider='github',
        jobs=[_job('build')],
        log_fetcher=_stub_fetcher,
    )

    args = argparse.Namespace(
        plan_id=plan_id,
        run_id=None,
        latest=True,
    )
    exit_code = cmd_read(args)
    assert exit_code == 0
    out = capsys.readouterr().out
    # The latest manifest's run_id appears in the TOON output.
    assert "'888'" in out or '"888"' in out or 'run_id: 888' in out


def test_cmd_read_latest_error_envelope_when_no_runs(capsys, plan_context):
    """When no runs are persisted, ``read --latest`` MUST emit the
    structured error envelope and exit 0.

    Operation failure (no persisted runs) is NOT a script crash — the
    script ran successfully, only the operation failed. Per the output
    contract (pm-plugin-development:plugin-script-architecture →
    output-contract.md), cmd_read exits 0 and carries the verdict in the
    TOON ``status: error`` / ``no_persisted_runs`` payload on stdout.
    Callers branch on ``status``, never on the process exit code. Exit 1
    is reserved for genuine script crashes; exit 2 for argparse.
    """
    plan_id = 'ci-artifacts-cmd-latest-empty'
    args = argparse.Namespace(
        plan_id=plan_id,
        run_id=None,
        latest=True,
    )
    exit_code = cmd_read(args)
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'status: error' in out
    assert 'no_persisted_runs' in out


# ---------------------------------------------------------------------------
# Regression: every cmd-level operation failure exits 0 with status: error
#
# Operation failures (manifest not found, no persisted runs, empty run_id,
# unloadable --jobs-file) are NOT script crashes — the script ran
# successfully, only the operation failed. Per the output contract
# (pm-plugin-development:plugin-script-architecture → output-contract.md),
# these exit 0 and carry the verdict in the TOON ``status: error`` payload on
# stdout. Callers branch on ``status``, never on the process exit code. A
# future regression of any cmd handler back to a non-zero exit on operation
# failure fails this gate.
# ---------------------------------------------------------------------------


def test_cmd_read_missing_run_exits_zero_with_toon_error(capsys, plan_context):
    """cmd_read for a missing run_id exits 0 with a TOON status:error payload."""
    plan_id = 'ci-artifacts-cmd-read-missing'
    args = argparse.Namespace(plan_id=plan_id, run_id='no-such-run', latest=False)
    exit_code = cmd_read(args)
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'status: error' in out


def test_cmd_persist_empty_run_id_exits_zero_with_toon_error(capsys, plan_context):
    """cmd_persist with an empty run_id exits 0 with a TOON status:error payload.

    persist() rejects the empty run_id with a status:error dict; cmd_persist
    must emit that TOON and exit 0 (operation failure, not a script crash).
    """
    plan_id = 'ci-artifacts-cmd-persist-empty-run-id'
    exit_code = cmd_persist(_persist_args(plan_id=plan_id, run_id=''))
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'status: error' in out
    assert 'run_id' in out


def test_cmd_persist_unloadable_jobs_file_exits_zero_with_toon_error(
    tmp_path, capsys, plan_context
):
    """cmd_persist handed an unparseable --jobs-file exits 0 with status:error.

    Malformed JSON in the jobs file is an operation failure, not a script
    crash — the handler reports it via the TOON ``status: error`` payload and
    exits 0. Callers branch on ``status``, never on the exit code.
    """
    plan_id = 'ci-artifacts-cmd-persist-bad-jobs-file'
    bad_jobs = tmp_path / 'bad-jobs.json'
    bad_jobs.write_text('{not valid json', encoding='utf-8')

    exit_code = cmd_persist(
        _persist_args(plan_id=plan_id, run_id='780', jobs_file=str(bad_jobs))
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'status: error' in out
    assert 'jobs-file' in out


# ---------------------------------------------------------------------------
# Slug-disambiguated failing-check variants — the failing-check log-download
# path persists two checks that SHARE one run_id by giving each a slug-named
# raw + filtered file. Neither overwrites the other, the manifest records every
# slugged raw/filtered path, and an idempotent re-emit returns all filtered
# paths.
# ---------------------------------------------------------------------------


def _failing_job(name: str, slug: str) -> dict:
    """A failing-check job carrying a slug + pre-fetched raw + filtered content.

    Mirrors the dict shape ``enrich_failing_checks_with_logs`` hands to
    ``persist`` — a slug (filename stem), inline ``raw_content`` (bypasses the
    log_fetcher) and a ``filtered_content`` error-extraction variant.
    """
    return {
        'name': name,
        'job_name': name,
        'workflow_name': 'ci',
        'conclusion': 'failure',
        'started_at': '2026-05-19T00:00:00Z',
        'completed_at': '2026-05-19T00:01:00Z',
        'run_url': 'https://example/runs/x',
        'slug': slug,
        'raw_content': f'RAW log for {name}\n',
        'filtered_content': f'FILTERED error for {name}\n',
    }


def test_persist_writes_slug_named_variants_for_shared_run_id(plan_context):
    """Two failing checks sharing one run_id get distinct slug-named raw +
    filtered files; neither overwrites the other.
    """
    plan_id = 'ci-artifacts-slug-shared-run'
    jobs = [
        _failing_job('verify / verify', 'verify-verify'),
        _failing_job('build (3.12)', 'build-3-12'),
    ]
    result = persist(
        plan_id=plan_id,
        run_id='500',
        head_sha='cafef00d',
        pr_number=7,
        provider='github',
        jobs=jobs,
    )
    assert result['status'] == 'success'
    assert result['job_count'] == 2

    run_dir = _run_dir(plan_id, '500')
    # Distinct slug-named raw + filtered files on disk for each check.
    assert (run_dir / 'verify-verify.log').is_file()
    assert (run_dir / 'verify-verify.filtered.log').is_file()
    assert (run_dir / 'build-3-12.log').is_file()
    assert (run_dir / 'build-3-12.filtered.log').is_file()
    # No overwrite: each raw file carries its own check's content.
    assert 'verify / verify' in (run_dir / 'verify-verify.log').read_text(encoding='utf-8')
    assert 'build (3.12)' in (run_dir / 'build-3-12.log').read_text(encoding='utf-8')
    # Filtered content is the error-extraction variant, distinct per check.
    assert 'FILTERED error for verify / verify' in (
        run_dir / 'verify-verify.filtered.log'
    ).read_text(encoding='utf-8')


def test_persist_manifest_records_every_slugged_path(plan_context):
    """The manifest enumerates every slugged raw + filtered path for a shared run_id."""
    plan_id = 'ci-artifacts-slug-manifest'
    jobs = [
        _failing_job('verify / verify', 'verify-verify'),
        _failing_job('build (3.12)', 'build-3-12'),
    ]
    result = persist(
        plan_id=plan_id,
        run_id='501',
        head_sha='abc',
        pr_number=7,
        provider='github',
        jobs=jobs,
    )
    # The return payload lists both raw and both filtered paths.
    assert len(result['log_paths']) == 2
    assert len(result['filtered_log_paths']) == 2

    manifest = read_manifest(plan_id=plan_id, run_id='501')['manifest']
    rows = manifest['jobs']
    assert len(rows) == 2
    by_slug = {r['slug']: r for r in rows}
    assert set(by_slug) == {'verify-verify', 'build-3-12'}
    for slug, row in by_slug.items():
        assert row['log_path'].endswith(f'{slug}.log'), row
        assert row['filtered_log_path'].endswith(f'{slug}.filtered.log'), row


def test_persist_additive_merge_second_check_same_run_id(plan_context):
    """A second persist adding a NEW slug to an existing run_id merges additively.

    The prior check's files are preserved and the manifest gains the new
    slugged raw + filtered rows — multiple failing checks of one run_id each
    gain their own files without overwriting the prior persist's artifacts.
    """
    plan_id = 'ci-artifacts-slug-additive'
    first = persist(
        plan_id=plan_id,
        run_id='600',
        head_sha='abc',
        pr_number=7,
        provider='github',
        jobs=[_failing_job('verify / verify', 'verify-verify')],
    )
    assert first['already_persisted'] is False
    assert first['job_count'] == 1

    run_dir = _run_dir(plan_id, '600')
    first_raw_before = (run_dir / 'verify-verify.log').read_text(encoding='utf-8')

    second = persist(
        plan_id=plan_id,
        run_id='600',
        head_sha='abc',
        pr_number=7,
        provider='github',
        jobs=[_failing_job('build (3.12)', 'build-3-12')],
    )
    # New slug → not a pure re-emit; the manifest now records both checks.
    assert second['already_persisted'] is False
    assert second['job_count'] == 2
    assert len(second['filtered_log_paths']) == 2

    # The first check's raw file is untouched.
    assert (run_dir / 'verify-verify.log').read_text(encoding='utf-8') == first_raw_before
    # The newly-added check's files now exist alongside it.
    assert (run_dir / 'build-3-12.log').is_file()
    assert (run_dir / 'build-3-12.filtered.log').is_file()

    manifest = read_manifest(plan_id=plan_id, run_id='600')['manifest']
    slugs = {r['slug'] for r in manifest['jobs']}
    assert slugs == {'verify-verify', 'build-3-12'}


def test_persist_idempotent_reemit_includes_all_filtered_paths(plan_context):
    """Re-persisting the SAME slugs is a pure re-emit returning all filtered paths."""
    plan_id = 'ci-artifacts-slug-reemit'
    jobs = [
        _failing_job('verify / verify', 'verify-verify'),
        _failing_job('build (3.12)', 'build-3-12'),
    ]
    first = persist(
        plan_id=plan_id,
        run_id='700',
        head_sha='abc',
        pr_number=7,
        provider='github',
        jobs=jobs,
    )
    assert first['already_persisted'] is False

    # Re-invoke with the identical slug set → pure re-emit (no new stems).
    second = persist(
        plan_id=plan_id,
        run_id='700',
        head_sha='abc',
        pr_number=7,
        provider='github',
        jobs=jobs,
    )
    assert second['already_persisted'] is True
    # The re-emit still surfaces both filtered paths (not dropped on re-emit).
    assert len(second['filtered_log_paths']) == 2
    assert sorted(second['filtered_log_paths']) == sorted(first['filtered_log_paths'])


def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: ``_run_dir``'s docstring
    must spell the artifact location as ``.plan/local/plans/`` — the legacy
    bare ``.plan/plans/`` form is incorrect since runtime state moved under
    ``.plan/local``.
    """
    import re

    source = (_SCRIPTS_DIR / 'manage-ci-artifacts.py').read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'
