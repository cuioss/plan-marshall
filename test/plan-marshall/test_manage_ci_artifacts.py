#!/usr/bin/env python3
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

import importlib.util
import sys
from pathlib import Path

from conftest import PlanContext  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Module loading — load the script via importlib so we can call
# ``persist()`` / ``read_manifest()`` / ``list_runs()`` directly without
# spawning a subprocess.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
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


def test_persist_writes_manifest_and_logs():
    plan_id = 'ci-artifacts-happy'
    with PlanContext(plan_id=plan_id):
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


def test_persist_records_head_sha_in_manifest():
    plan_id = 'ci-artifacts-head-sha'
    with PlanContext(plan_id=plan_id):
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


def test_persist_is_idempotent_for_same_run_id():
    plan_id = 'ci-artifacts-idempotent'
    with PlanContext(plan_id=plan_id):
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


def test_multi_run_cascade_creates_independent_dirs():
    plan_id = 'ci-artifacts-cascade'
    with PlanContext(plan_id=plan_id):
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


def test_loop_back_does_not_overwrite_previous_run():
    """A second persist with a NEW run_id MUST NOT touch the prior run's manifest."""
    plan_id = 'ci-artifacts-no-overwrite'
    with PlanContext(plan_id=plan_id):
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


def test_read_missing_run_returns_error():
    plan_id = 'ci-artifacts-missing'
    with PlanContext(plan_id=plan_id):
        result = read_manifest(plan_id=plan_id, run_id='does-not-exist')
        assert result['status'] == 'error'


def test_list_empty_returns_zero_runs():
    plan_id = 'ci-artifacts-empty-list'
    with PlanContext(plan_id=plan_id):
        result = list_runs(plan_id=plan_id)
        assert result['status'] == 'success'
        assert result['run_count'] == 0


# ---------------------------------------------------------------------------
# Empty run_id rejected
# ---------------------------------------------------------------------------


def test_persist_rejects_empty_run_id():
    plan_id = 'ci-artifacts-empty-run-id'
    with PlanContext(plan_id=plan_id):
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
