#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""CI run artifact persistence layer.

Backs the ``ci-verify`` finalize step from lesson-2026-05-18-16-001
deliverable 7. Persists per-job CI logs plus a ``manifest.toon`` under
``.plan/local/plans/{plan_id}/artifacts/ci-runs/{run_id}/`` so retrospectives
that run after GitHub's 90-day log retention window can still consult
the evidence.

Subcommands:

    persist  Fetch and write the full run (eager mode). Idempotent — a
             second invocation for the same (plan_id, run_id) re-emits
             the existing manifest contents without re-fetching logs.
    read     Read a previously persisted manifest.
    list     Enumerate all persisted runs under the plan dir, sorted by
             ``fetched_at``.

The script is deterministic file-IO plus provider-API plumbing — no LLM
core. Provider integration flows through the
``plan-marshall:tools-integration-ci:ci`` abstraction (no direct gh/glab
calls in this script).

Storage layout (canonical):

    .plan/local/plans/{plan_id}/artifacts/ci-runs/{run_id}/
        manifest.toon
        {job_name}.log
        ...

Each loop-back commit produces a fresh ``{run_id}`` directory; previous
runs are never overwritten. See ``standards/persistence-layout.md`` for
the manifest schema and retention contract.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from file_ops import get_base_dir, get_plan_dir  # type: ignore[import-not-found]
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ARTIFACTS_SUBDIR = 'artifacts/ci-runs'
_MANIFEST_FILENAME = 'manifest.toon'

# Job name → log filename sanitiser. CI job names can contain slashes,
# colons, parentheses, etc.; the persistence layer normalises them to a
# safe file-name segment so the on-disk layout is portable.
_JOB_NAME_SAFE_RE = re.compile(r'[^A-Za-z0-9._-]+')


def _safe_job_filename(job_name: str) -> str:
    """Return a portable filename derived from a job name.

    Replaces every run of non-`[A-Za-z0-9._-]` characters with a single
    underscore; collapses leading/trailing underscores. Empty input
    yields ``unnamed-job``.
    """
    if not job_name:
        return 'unnamed-job'
    sanitised = _JOB_NAME_SAFE_RE.sub('_', job_name).strip('_')
    return sanitised or 'unnamed-job'


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _relative_anchor() -> Path:
    """Return the anchor used to express artifact paths as repo-relative.

    Resolves to the parent of ``get_base_dir()`` — i.e. the ``.plan``
    directory when ``get_base_dir()`` is the canonical ``.plan/local``
    tree, or the parent of ``PLAN_BASE_DIR`` in fixture mode. Used solely
    for the ``.relative_to`` calls in the persist return payload; never
    used to construct on-disk paths (those go through ``get_plan_dir``).
    """
    return get_base_dir().parent


def _run_dir(plan_id: str, run_id: str) -> Path:
    """Return the absolute path of the per-run artifact directory.

    Resolved via the canonical ``file_ops.get_plan_dir`` helper, so
    artifacts land under ``<repo>/.plan/local/plans/{plan_id}/...`` in
    production and under the fixture tree in tests. The previous
    ``_resolve_plan_base_dir`` helper resolved relative to the agent cwd
    when ``PLAN_BASE_DIR`` was unset and produced a ghost ``.plan/plans/``
    tree — see the fix-ghost-plan-dir lesson.
    """
    return get_plan_dir(plan_id) / _ARTIFACTS_SUBDIR / run_id


def _manifest_path(plan_id: str, run_id: str) -> Path:
    return _run_dir(plan_id, run_id) / _MANIFEST_FILENAME


def _runs_root(plan_id: str) -> Path:
    return get_plan_dir(plan_id) / _ARTIFACTS_SUBDIR


# ---------------------------------------------------------------------------
# Manifest schema
# ---------------------------------------------------------------------------


def _build_manifest(
    *,
    run_id: str,
    provider: str,
    head_sha: str,
    pr_number: int | str,
    plan_id: str,
    wait_outcome: str,
    final_status: str,
    jobs: list[dict],
    log_paths: dict[str, str],
) -> dict:
    """Build the manifest TOON payload.

    ``jobs`` are the per-job dicts taken from the ``ci wait`` envelope
    (or an equivalent ``ci status`` envelope). ``log_paths`` maps each
    job's canonical filename to its plan-dir-relative path.
    """
    fetched_at = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    job_rows: list[dict] = []
    for job in jobs:
        canonical = _safe_job_filename(job.get('job_name') or job.get('name', ''))
        job_rows.append(
            {
                'name': job.get('name', ''),
                'workflow_name': job.get('workflow_name') or '',
                'job_name': job.get('job_name') or '',
                'conclusion': job.get('conclusion') or '',
                'started_at': job.get('started_at') or '',
                'completed_at': job.get('completed_at') or '',
                'run_url': job.get('run_url') or '',
                'log_path': log_paths.get(canonical, ''),
            }
        )
    return {
        'run_id': run_id,
        'provider': provider,
        'head_sha': head_sha,
        'fetched_at': fetched_at,
        'pr_number': pr_number,
        'plan_id': plan_id,
        'wait_outcome': wait_outcome,
        'final_status': final_status,
        'jobs': job_rows,
    }


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------


def persist(
    *,
    plan_id: str,
    run_id: str,
    head_sha: str,
    pr_number: int | str,
    provider: str,
    jobs: list[dict],
    log_fetcher=None,
    wait_outcome: str = 'completed',
    final_status: str = '',
) -> dict:
    """Persist the per-run artifacts.

    Args:
        plan_id: Plan identifier; locates the plan dir.
        run_id: CI run identifier (GitHub ``run.databaseId`` or GitLab
            ``pipeline.id``). The per-run directory key.
        head_sha: Commit SHA the CI run executed against. Recorded in
            the manifest so the loop-back ↔ commit linkage is auditable.
        pr_number: PR / MR number to record in the manifest.
        provider: ``github`` or ``gitlab``.
        jobs: List of job dicts from the ``ci wait`` envelope. Each
            dict carries ``name``, ``job_name``, ``conclusion``,
            ``run_id`` etc. (See ``_build_failing_check_entry`` in the
            provider scripts for the canonical shape — non-failing
            jobs follow the same schema.)
        log_fetcher: Optional callable used as a test seam in place of
            the default log fetching path. Signature:
            ``(provider, run_id, job) -> str`` returning the log
            content for a single job.
        wait_outcome: ``completed`` or ``deadline_exceeded`` (from the
            wait envelope).
        final_status: ``success`` / ``failure`` / ``none`` / ``timeout``
            (from the wait envelope).

    Returns:
        Result dict matching the script's TOON output contract.

    Idempotence: when ``manifest.toon`` already exists for the
    ``(plan_id, run_id)`` pair, this function is a no-op that re-emits
    the existing manifest's job_count and log paths.
    """
    if not run_id:
        return {
            'status': 'error',
            'error': 'run_id must be a non-empty string',
        }

    run_dir = _run_dir(plan_id, run_id)
    manifest_path = _manifest_path(plan_id, run_id)

    # Idempotence: existing manifest → re-emit.
    if manifest_path.is_file():
        try:
            existing = parse_toon(manifest_path.read_text(encoding='utf-8'))
        except Exception as exc:
            return {
                'status': 'error',
                'error': f'existing manifest at {manifest_path} unparseable: {exc}',
            }
        existing_jobs = existing.get('jobs') or []
        existing_log_paths: list[str] = [
            j.get('log_path', '') for j in existing_jobs if j.get('log_path')
        ]
        return {
            'status': 'success',
            'plan_id': plan_id,
            'run_id': run_id,
            'run_dir': str(run_dir.relative_to(_relative_anchor()))
            if run_dir.is_absolute()
            else str(run_dir),
            'already_persisted': True,
            'job_count': len(existing_jobs),
            'manifest_path': str(manifest_path.relative_to(_relative_anchor()))
            if manifest_path.is_absolute()
            else str(manifest_path),
            'log_paths': existing_log_paths,
        }

    # Fresh persist: fetch every job's log slice and write to disk.
    run_dir.mkdir(parents=True, exist_ok=True)
    fetcher = log_fetcher or _default_log_fetcher
    log_paths: dict[str, str] = {}
    for job in jobs:
        canonical = _safe_job_filename(job.get('job_name') or job.get('name', ''))
        log_filename = f'{canonical}.log'
        log_target = run_dir / log_filename
        try:
            content = fetcher(provider, run_id, job)
        except Exception as exc:
            # A single-job fetch failure must not abort the whole
            # persist call — write an explanatory stub so the
            # retrospective still sees a per-job artifact.
            content = f'[fetch-failed] {exc}\n'
        log_target.write_text(content or '', encoding='utf-8')
        relative_log = (
            log_target.relative_to(_relative_anchor())
            if log_target.is_absolute()
            else log_target
        )
        log_paths[canonical] = str(relative_log)

    manifest = _build_manifest(
        run_id=run_id,
        provider=provider,
        head_sha=head_sha,
        pr_number=pr_number,
        plan_id=plan_id,
        wait_outcome=wait_outcome,
        final_status=final_status,
        jobs=jobs,
        log_paths=log_paths,
    )
    manifest_path.write_text(serialize_toon(manifest), encoding='utf-8')

    return {
        'status': 'success',
        'plan_id': plan_id,
        'run_id': run_id,
        'run_dir': str(run_dir.relative_to(_relative_anchor()))
        if run_dir.is_absolute()
        else str(run_dir),
        'already_persisted': False,
        'job_count': len(jobs),
        'manifest_path': str(manifest_path.relative_to(_relative_anchor()))
        if manifest_path.is_absolute()
        else str(manifest_path),
        'log_paths': sorted(log_paths.values()),
    }


def _default_log_fetcher(provider: str, run_id: str, job: dict) -> str:
    """Default log fetcher — delegates to ``tools-integration-ci``.

    This is a thin placeholder. The actual ``ci fetch-logs`` sub-verb
    on ``tools-integration-ci`` is documented in deliverable 7 as the
    canonical integration point. Until that sub-verb lands, this
    fetcher returns a stub note so the persistence layer still produces
    a deterministic on-disk artifact and tests of the persistence layer
    do not require live CI access. Tests inject their own ``log_fetcher``
    via the ``persist()`` keyword argument.
    """
    return (
        f'[manage-ci-artifacts] log fetch deferred to '
        f'tools-integration-ci ci fetch-logs (provider={provider}, '
        f'run_id={run_id}, job={job.get("name", "")})\n'
    )


# ---------------------------------------------------------------------------
# Read / list
# ---------------------------------------------------------------------------


def read_manifest(*, plan_id: str, run_id: str) -> dict:
    """Read a previously persisted manifest."""
    path = _manifest_path(plan_id, run_id)
    if not path.is_file():
        return {
            'status': 'error',
            'error': f'manifest not found for run_id={run_id}',
            'plan_id': plan_id,
            'run_id': run_id,
        }
    try:
        manifest = parse_toon(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return {
            'status': 'error',
            'error': f'manifest at {path} unparseable: {exc}',
        }
    return {
        'status': 'success',
        'plan_id': plan_id,
        'run_id': run_id,
        'manifest': manifest,
    }


def list_runs(*, plan_id: str) -> dict:
    """List all persisted runs under the plan dir, sorted by fetched_at."""
    root = _runs_root(plan_id)
    if not root.is_dir():
        return {
            'status': 'success',
            'plan_id': plan_id,
            'run_count': 0,
            'runs': [],
        }
    rows: list[dict] = []
    for run_dir in root.iterdir():
        if not run_dir.is_dir():
            continue
        manifest_path = run_dir / _MANIFEST_FILENAME
        if not manifest_path.is_file():
            continue
        try:
            manifest = parse_toon(manifest_path.read_text(encoding='utf-8'))
        except Exception:
            continue
        rows.append(
            {
                'run_id': manifest.get('run_id', run_dir.name),
                'head_sha': manifest.get('head_sha', ''),
                'fetched_at': manifest.get('fetched_at', ''),
                'job_count': len(manifest.get('jobs') or []),
            }
        )
    rows.sort(key=lambda r: r.get('fetched_at') or '')
    return {
        'status': 'success',
        'plan_id': plan_id,
        'run_count': len(rows),
        'runs': rows,
    }


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def cmd_persist(args: argparse.Namespace) -> int:
    # Jobs are passed as a JSON file (path) — the CLI surface accepts a
    # path so multi-line nested job structures do not need to be quoted
    # on the command line.
    jobs: list[dict] = []
    if args.jobs_file:
        try:
            jobs = json.loads(Path(args.jobs_file).read_text(encoding='utf-8'))
        except Exception as exc:
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'error': f'failed to load --jobs-file {args.jobs_file}: {exc}',
                    }
                )
            )
            return 1
        if not isinstance(jobs, list):
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'error': '--jobs-file must contain a JSON array of job dicts',
                    }
                )
            )
            return 1
    result = persist(
        plan_id=args.plan_id,
        run_id=args.run_id,
        head_sha=args.head_sha,
        pr_number=args.pr_number,
        provider=args.provider,
        jobs=jobs,
        wait_outcome=args.wait_outcome,
        final_status=args.final_status,
    )
    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_read(args: argparse.Namespace) -> int:
    result = read_manifest(plan_id=args.plan_id, run_id=args.run_id)
    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_list(args: argparse.Namespace) -> int:
    result = list_runs(plan_id=args.plan_id)
    print(serialize_toon(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Manage CI run artifact persistence under the plan directory.',
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    persist_p = sub.add_parser('persist', help='Persist a CI run', allow_abbrev=False)
    persist_p.add_argument('--plan-id', required=True, dest='plan_id')
    persist_p.add_argument('--run-id', required=True, dest='run_id')
    persist_p.add_argument('--head-sha', required=True, dest='head_sha')
    persist_p.add_argument('--pr-number', required=True, dest='pr_number')
    persist_p.add_argument(
        '--provider',
        required=True,
        choices=('github', 'gitlab'),
        dest='provider',
    )
    persist_p.add_argument(
        '--jobs-file',
        dest='jobs_file',
        help='Path to a JSON file containing the jobs array. Optional — '
        'an empty/missing file persists a manifest with zero jobs.',
    )
    persist_p.add_argument(
        '--wait-outcome',
        default='completed',
        choices=('completed', 'deadline_exceeded'),
        dest='wait_outcome',
    )
    persist_p.add_argument(
        '--final-status',
        default='',
        dest='final_status',
    )
    persist_p.set_defaults(func=cmd_persist)

    read_p = sub.add_parser('read', help='Read a persisted manifest', allow_abbrev=False)
    read_p.add_argument('--plan-id', required=True, dest='plan_id')
    read_p.add_argument('--run-id', required=True, dest='run_id')
    read_p.set_defaults(func=cmd_read)

    list_p = sub.add_parser('list', help='List all persisted runs', allow_abbrev=False)
    list_p.add_argument('--plan-id', required=True, dest='plan_id')
    list_p.set_defaults(func=cmd_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'persist',
    'read_manifest',
    'list_runs',
]
