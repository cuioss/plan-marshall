#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""CI run artifact persistence layer.

Backs the ``ci-verify`` finalize step. Persists per-job CI logs plus a
``manifest.toon`` under
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
import os
import re
import sys
import tempfile
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
    production and under the fixture tree (``PLAN_BASE_DIR``) in tests.
    """
    return get_plan_dir(plan_id) / _ARTIFACTS_SUBDIR / run_id


def _manifest_path(plan_id: str, run_id: str) -> Path:
    return _run_dir(plan_id, run_id) / _MANIFEST_FILENAME


def _runs_root(plan_id: str) -> Path:
    return get_plan_dir(plan_id) / _ARTIFACTS_SUBDIR


# ---------------------------------------------------------------------------
# Manifest schema
# ---------------------------------------------------------------------------


def _job_stem(job: dict) -> str:
    """Return the on-disk filename stem for a job.

    A caller-supplied ``slug`` (the failing-check log-download path uses the
    slugified check name to disambiguate multiple failing checks that share a
    ``run_id``) takes precedence; otherwise the stem is derived from the job's
    ``job_name`` / ``name`` via :func:`_safe_job_filename`.
    """
    slug = job.get('slug')
    if slug:
        return str(slug)
    return _safe_job_filename(job.get('job_name') or job.get('name', ''))


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
    filtered_log_paths: dict[str, str] | None = None,
) -> dict:
    """Build the manifest TOON payload.

    ``jobs`` are the per-job dicts taken from the ``checks wait`` envelope
    (or an equivalent ``checks status`` envelope). ``log_paths`` maps each
    job's filename stem to its plan-dir-relative raw-log path;
    ``filtered_log_paths`` (optional) maps the same stem to the plan-dir-relative
    filtered-log path written for failing checks.
    """
    filtered_log_paths = filtered_log_paths or {}
    fetched_at = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    job_rows: list[dict] = []
    for job in jobs:
        stem = _job_stem(job)
        job_rows.append(
            {
                'name': job.get('name', ''),
                'workflow_name': job.get('workflow_name') or '',
                'job_name': job.get('job_name') or '',
                'slug': job.get('slug') or '',
                'conclusion': job.get('conclusion') or '',
                'started_at': job.get('started_at') or '',
                'completed_at': job.get('completed_at') or '',
                'run_url': job.get('run_url') or '',
                'log_path': log_paths.get(stem, ''),
                'filtered_log_path': filtered_log_paths.get(stem, ''),
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
        # ``jobs_source`` labels how the jobs[] array was populated so a
        # retrospective can tell a genuine zero-job run apart from a
        # persist call that simply was not handed the jobs array.
        # ``enumerated`` — the caller supplied a non-empty jobs list.
        # ``empty`` — the caller supplied no jobs (empty/missing
        # --jobs-file); the manifest records zero jobs deliberately, NOT
        # because no CI ran.
        'jobs_source': 'enumerated' if job_rows else 'empty',
        'jobs': job_rows,
    }


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------


def _relative_str(path: Path) -> str:
    """Express ``path`` relative to the artifact anchor when absolute."""
    return str(path.relative_to(_relative_anchor())) if path.is_absolute() else str(path)


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
        jobs: List of job dicts from the ``checks wait`` envelope. Each
            dict carries ``name``, ``job_name``, ``conclusion``,
            ``run_id`` etc. (See ``_build_failing_check_entry`` in the
            provider scripts for the canonical shape — non-failing
            jobs follow the same schema.) Failing-check downloads add
            three optional keys consumed here: ``slug`` (slugified check
            name → filename stem, disambiguating multiple failing checks
            sharing one ``run_id``), ``raw_content`` (pre-fetched raw log
            content; bypasses ``log_fetcher`` when present), and
            ``filtered_content`` (the filtered error-extraction variant —
            written alongside the raw log as ``{stem}.filtered.log``).
        log_fetcher: Optional callable used as a test seam in place of
            the default log fetching path. Signature:
            ``(provider, run_id, job) -> str`` returning the log
            content for a single job. Skipped for any job that already
            carries ``raw_content``.
        wait_outcome: ``completed`` or ``deadline_exceeded`` (from the
            wait envelope).
        final_status: ``success`` / ``failure`` / ``none`` / ``timeout``
            (from the wait envelope).

    Returns:
        Result dict matching the script's TOON output contract.

    Idempotence: when ``manifest.toon`` already exists for the
    ``(plan_id, run_id)`` pair, this function re-emits the existing
    manifest without re-fetching logs — UNLESS the call supplies jobs
    whose ``slug`` (filename stem) is not yet recorded in the manifest.
    In that case the new slug-named raw + filtered variants are written
    additively and merged into the manifest, so multiple failing checks
    of one ``run_id`` each gain their own files without overwriting the
    prior run's artifacts.
    """
    if not run_id:
        return {
            'status': 'error',
            'error': 'run_id must be a non-empty string',
        }

    run_dir = _run_dir(plan_id, run_id)
    manifest_path = _manifest_path(plan_id, run_id)

    existing_manifest: dict | None = None
    if manifest_path.is_file():
        try:
            existing_manifest = parse_toon(manifest_path.read_text(encoding='utf-8'))
        except Exception as exc:
            return {
                'status': 'error',
                'error': f'existing manifest at {manifest_path} unparseable: {exc}',
            }
        existing_jobs = existing_manifest.get('jobs') or []
        existing_stems = {j.get('slug') or _job_stem(j) for j in existing_jobs}
        new_stems = {_job_stem(j) for j in jobs}
        # Pure re-emit when the call adds no new filename stem.
        if new_stems <= existing_stems:
            return _reemit(plan_id, run_id, run_dir, manifest_path, existing_manifest)

    run_dir.mkdir(parents=True, exist_ok=True)
    fetcher = log_fetcher or _default_log_fetcher
    log_paths: dict[str, str] = {}
    filtered_log_paths: dict[str, str] = {}
    for job in jobs:
        stem = _job_stem(job)
        log_target = run_dir / f'{stem}.log'
        raw_content = job.get('raw_content')
        if raw_content is None:
            try:
                raw_content = fetcher(provider, run_id, job)
            except Exception as exc:
                # A single-job fetch failure must not abort the whole
                # persist call — write an explanatory stub so the
                # retrospective still sees a per-job artifact.
                raw_content = f'[fetch-failed] {exc}\n'
        log_target.write_text(raw_content or '', encoding='utf-8')
        log_paths[stem] = _relative_str(log_target)

        filtered_content = job.get('filtered_content')
        if filtered_content is not None:
            filtered_target = run_dir / f'{stem}.filtered.log'
            filtered_target.write_text(filtered_content or '', encoding='utf-8')
            filtered_log_paths[stem] = _relative_str(filtered_target)

    if existing_manifest is not None:
        manifest = _merge_into_manifest(
            existing_manifest,
            new_jobs=jobs,
            log_paths=log_paths,
            filtered_log_paths=filtered_log_paths,
        )
    else:
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
            filtered_log_paths=filtered_log_paths,
        )
    # Atomic write: parallel CI jobs sharing the same run_id could race on
    # manifest.toon. Write to a temp file in the same directory, then
    # os.replace() it into place (atomic on POSIX and Windows). The
    # try/finally unlinks the temp file if anything fails before the rename.
    tmp_file = tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=str(run_dir),
        prefix='.manifest-',
        suffix='.toon',
        delete=False,
    )
    try:
        with tmp_file:
            tmp_file.write(serialize_toon(manifest))
        os.replace(tmp_file.name, manifest_path)
    except BaseException:
        try:
            os.unlink(tmp_file.name)
        except OSError:
            pass
        raise

    manifest_jobs = manifest.get('jobs') or []
    return {
        'status': 'success',
        'plan_id': plan_id,
        'run_id': run_id,
        'run_dir': _relative_str(run_dir),
        'already_persisted': False,
        'job_count': len(manifest_jobs),
        'jobs_source': manifest['jobs_source'],
        'manifest_path': _relative_str(manifest_path),
        'log_paths': sorted(j.get('log_path', '') for j in manifest_jobs if j.get('log_path')),
        'filtered_log_paths': sorted(
            j.get('filtered_log_path', '') for j in manifest_jobs if j.get('filtered_log_path')
        ),
    }


def _reemit(
    plan_id: str,
    run_id: str,
    run_dir: Path,
    manifest_path: Path,
    existing: dict,
) -> dict:
    """Re-emit an existing manifest's contents without re-fetching logs."""
    existing_jobs = existing.get('jobs') or []
    return {
        'status': 'success',
        'plan_id': plan_id,
        'run_id': run_id,
        'run_dir': _relative_str(run_dir),
        'already_persisted': True,
        'job_count': len(existing_jobs),
        'jobs_source': existing.get('jobs_source') or ('enumerated' if existing_jobs else 'empty'),
        'manifest_path': _relative_str(manifest_path),
        'log_paths': [j.get('log_path', '') for j in existing_jobs if j.get('log_path')],
        'filtered_log_paths': [
            j.get('filtered_log_path', '') for j in existing_jobs if j.get('filtered_log_path')
        ],
    }


def _merge_into_manifest(
    existing: dict,
    *,
    new_jobs: list[dict],
    log_paths: dict[str, str],
    filtered_log_paths: dict[str, str],
) -> dict:
    """Merge newly-written slug-named jobs into an existing manifest.

    Existing job rows are preserved verbatim; each new job whose filename
    stem is not already recorded is appended with its raw + filtered paths.
    The ``fetched_at`` timestamp is left untouched so recency-by-timestamp
    selection stays anchored to the run's first persist.
    """
    rows: list[dict] = list(existing.get('jobs') or [])
    known_stems = {j.get('slug') or _job_stem(j) for j in rows}
    for job in new_jobs:
        stem = _job_stem(job)
        if stem in known_stems:
            continue
        known_stems.add(stem)
        rows.append(
            {
                'name': job.get('name', ''),
                'workflow_name': job.get('workflow_name') or '',
                'job_name': job.get('job_name') or '',
                'slug': job.get('slug') or '',
                'conclusion': job.get('conclusion') or '',
                'started_at': job.get('started_at') or '',
                'completed_at': job.get('completed_at') or '',
                'run_url': job.get('run_url') or '',
                'log_path': log_paths.get(stem, ''),
                'filtered_log_path': filtered_log_paths.get(stem, ''),
            }
        )
    merged = dict(existing)
    merged['jobs'] = rows
    merged['jobs_source'] = 'enumerated' if rows else 'empty'
    return merged


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
        f'tools-integration-ci:ci checks logs (provider={provider}, '
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
        'log_paths': sorted(
            j.get('log_path', '')
            for j in (manifest.get('jobs') or [])
            if j.get('log_path')
        ),
    }


def read_latest_manifest(*, plan_id: str) -> dict:
    """Read the most-recently-persisted manifest for ``plan_id``.

    Recency is determined by the ``fetched_at`` timestamp recorded
    inside each manifest — NEVER by lexicographic ``run_id`` sorting.
    Run-id monotonicity is a GitHub-specific assumption (and not even
    reliably monotonic across forks/reruns) that no caller should bake
    in; sourcing recency from the timestamp inside the manifest keeps
    the accessor provider-neutral.

    Returns:
        Dict matching the ``read`` subcommand's return shape (status,
        plan_id, run_id, manifest, log_paths) when at least one
        persisted manifest exists; otherwise a ``status: error``
        envelope with ``error: no_persisted_runs``.

    The implementation reuses :func:`list_runs`'s enumeration so the
    "which manifests are eligible?" predicate stays in one place — the
    only difference from ``list`` is that this verb picks the newest
    instead of returning all rows.
    """
    listing = list_runs(plan_id=plan_id)
    if listing.get('status') != 'success':
        return listing
    rows = listing.get('runs') or []
    if not rows:
        return {
            'status': 'error',
            'error': 'no_persisted_runs',
            'plan_id': plan_id,
        }
    # list_runs sorts ascending by fetched_at; the last row is the
    # newest. Manifests with an empty/missing fetched_at sort first and
    # would only be selected if every manifest carries an empty value
    # — in that degenerate case the newest is simply the last entry
    # produced by directory iteration order.
    latest = rows[-1]
    return read_manifest(plan_id=plan_id, run_id=str(latest.get('run_id', '')))


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
            # Operation failure → exit 0; the TOON status:error payload
            # above carries the verdict. Callers branch on status, not on
            # the process exit code. Exit 1 is reserved for script crashes.
            return 0
        if not isinstance(jobs, list):
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'error': '--jobs-file must contain a JSON array of job dicts',
                    }
                )
            )
            return 0
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
    # Operation failures exit 0 — the TOON status field carries the verdict.
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    if getattr(args, 'latest', False):
        result = read_latest_manifest(plan_id=args.plan_id)
    else:
        result = read_manifest(plan_id=args.plan_id, run_id=args.run_id)
    print(serialize_toon(result))
    # Operation failures (manifest not found, unparseable) exit 0 — the
    # TOON status field carries the verdict; callers branch on status.
    return 0


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
    # --run-id and --latest are mutually exclusive: a caller specifies
    # either the exact run identifier OR asks for the most-recent run
    # selected by manifest fetched_at timestamp. Exactly one of the two
    # must be supplied.
    read_group = read_p.add_mutually_exclusive_group(required=True)
    read_group.add_argument('--run-id', dest='run_id')
    read_group.add_argument(
        '--latest',
        action='store_true',
        dest='latest',
        help='Read the most-recently-persisted manifest, selected by the '
        'fetched_at timestamp inside each manifest (never by '
        'caller-side run_id sorting — run_id monotonicity is a '
        'GitHub-specific assumption).',
    )
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
    'read_latest_manifest',
    'list_runs',
]
