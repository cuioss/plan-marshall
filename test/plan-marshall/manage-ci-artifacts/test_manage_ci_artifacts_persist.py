#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Persist cluster — ``persist`` core, head-sha, idempotence, cascade, slug variants."""

from __future__ import annotations

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('plan-marshall', 'manage-ci-artifacts', filename, name)


_mod = _load_module('manage_ci_artifacts', 'manage-ci-artifacts.py')
persist = _mod.persist
read_manifest = _mod.read_manifest
list_runs = _mod.list_runs
_run_dir = _mod._run_dir
_manifest_path = _mod._manifest_path
_safe_job_filename = _mod._safe_job_filename


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
    assert old_manifest_before == old_manifest_after, 'Loop-back commit must not modify a previous run directory'


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
    assert 'FILTERED error for verify / verify' in (run_dir / 'verify-verify.filtered.log').read_text(encoding='utf-8')


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
