#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Collect and classify artifacts present in a plan directory.

Supports two modes from a SINGLE plan root keyed by ``--plan-id``:

- ``live``: resolve the plan directory from ``--plan-id`` using
  ``file_ops.base_path`` (reads ``PLAN_BASE_DIR`` env var or the project-local
  ``.plan/local`` tree). A caller-supplied ``--archived-plan-path`` is ignored.
- ``archived``: resolve the plan directory from ``--plan-id`` plus the optional
  ``--archived-plan-path``. When the caller passes an explicit path it is used
  verbatim; otherwise a synthetic per-plan dir under the OS tmpdir
  (``<tmp>/plan-retrospective/plan-<plan_id>``) is used so audits without an
  explicit archive path never mutate any real archived plan directory.

Unreadable inputs (missing plan, missing directory, not-a-directory, I/O
failure while walking) degrade the block to ``not_evaluated`` with a reason
rather than to a clean verdict — a could-not-look must never carry the same
token as a nothing-to-look-at.

Output: TOON manifest listing every file found under the plan directory,
grouped by kind (``status``, ``request``, ``solution_outline``,
``references``, ``tasks``, ``logs``, ``metrics``, ``reports``, ``other``).
The manifest is consumed by ``check-artifact-consistency.py`` and the
retrospective orchestrator.

Usage:
    python3 collect-plan-artifacts.py run --plan-id EXAMPLE-PLAN --mode live
    python3 collect-plan-artifacts.py run --archived-plan-path /abs/path --mode archived
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)

# File classification. Keys are filename (or suffix) patterns; value is the
# ``kind`` tag recorded in the manifest.
_KIND_BY_FILENAME = {
    'status.toon': 'status',
    'status.json': 'status',
    'request.md': 'request',
    'solution_outline.md': 'solution_outline',
    'references.json': 'references',
    'references.toon': 'references',
    'metrics.md': 'metrics',
    'quality-verification-report.md': 'reports',
}

_KIND_BY_PREFIX = (
    ('lesson-', 'lessons'),
    ('TASK-', 'tasks'),
    ('quality-verification-report-audit-', 'reports'),
)


def classify_file(rel_path: Path) -> str:
    """Return the ``kind`` label for a plan-relative file path.

    The plan directory layout has ``logs/`` and ``tasks/`` subdirectories;
    files beneath them are classified by parent directory rather than
    filename. Everything else is classified by exact filename first, then
    by a small set of filename prefixes.
    """
    parts = rel_path.parts
    if parts and parts[0] == 'logs':
        return 'logs'
    if parts and parts[0] == 'tasks':
        return 'tasks'

    name = rel_path.name
    if name in _KIND_BY_FILENAME:
        return _KIND_BY_FILENAME[name]
    for prefix, kind in _KIND_BY_PREFIX:
        if name.startswith(prefix):
            return kind
    return 'other'


_ARCHIVED_TMP_SUBDIR = 'plan-retrospective'


def _resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Return the canonical single plan root for the given mode.

    The single source of truth for plan-root resolution: ``--plan-id`` is
    required in BOTH modes (it keys the synthetic archived fallback), ``live``
    mode resolves via ``base_path`` and ignores ``archived_plan_path``,
    ``archived`` mode honours an explicit ``archived_plan_path`` and otherwise
    falls back to a synthetic per-plan tmp directory so production audits
    without an explicit archive path never write into a real archived plan.

    Raises ``ValueError`` on unknown ``mode`` or missing ``plan_id``.
    """
    if not plan_id:
        raise ValueError('--plan-id is required')
    if mode == 'live':
        return base_path('plans', plan_id)
    if mode == 'archived':
        if archived_plan_path:
            return Path(archived_plan_path)
        return (Path(tempfile.gettempdir()) / _ARCHIVED_TMP_SUBDIR / f'plan-{plan_id}').resolve()
    raise ValueError(f"Unknown mode: {mode!r} — expected 'live' or 'archived'")


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan directory based on mode.

    Single-plan-root resolution via :func:`_resolve_plan_dir`, then the
    existence / is-dir validation. Raises ``ValueError`` when the provided
    inputs are inconsistent or the resolved directory does not exist.
    """
    plan_dir = _resolve_plan_dir(mode, plan_id, archived_plan_path)

    if not plan_dir.exists():
        raise ValueError(f'Plan directory does not exist: {plan_dir}')
    if not plan_dir.is_dir():
        raise ValueError(f'Plan path is not a directory: {plan_dir}')
    return plan_dir


def collect_manifest(plan_dir: Path) -> dict[str, Any]:
    """Walk the plan directory and build the manifest.

    Each entry contains ``path`` (plan-relative), ``kind`` (classification
    label), and ``size_bytes``. Directories are not listed; only files.
    Unreadable files (stat failures, mid-walk deletions) are skipped rather
    than aborting the walk — the manifest states what it could read.
    """
    entries: list[dict[str, Any]] = []
    by_kind: dict[str, int] = {}

    try:
        candidates = sorted(plan_dir.rglob('*'))
    except OSError as exc:
        raise ValueError(f'Plan directory could not be walked: {plan_dir}: {exc}') from exc
    for path in candidates:
        try:
            if not path.is_file():
                continue
        except OSError:
            continue
        try:
            rel = path.relative_to(plan_dir)
        except ValueError:
            continue
        kind = classify_file(rel)
        try:
            size = path.stat().st_size
        except OSError:
            continue
        entries.append({'path': str(rel), 'kind': kind, 'size_bytes': size})
        by_kind[kind] = by_kind.get(kind, 0) + 1

    return {
        'entries': entries,
        'by_kind': by_kind,
        'total_files': len(entries),
    }


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_id = args.plan_id
    try:
        plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    except (ValueError, OSError) as exc:
        # Degrade unreadable inputs to not_evaluated with a reason rather than
        # to a clean verdict: no manifest was observed, so nothing may pass.
        return {
            'status': 'not_evaluated',
            'mode': args.mode,
            'plan_id': plan_id or 'unknown',
            'plan_dir': '',
            'total_files': 0,
            'by_kind': {},
            'entries': [],
            'reason': str(exc),
        }
    try:
        manifest = collect_manifest(plan_dir)
    except (ValueError, OSError) as exc:
        return {
            'status': 'not_evaluated',
            'mode': args.mode,
            'plan_id': plan_id or plan_dir.name,
            'plan_dir': str(plan_dir),
            'total_files': 0,
            'by_kind': {},
            'entries': [],
            'reason': str(exc),
        }

    return {
        'status': 'success',
        'mode': args.mode,
        'plan_id': args.plan_id or plan_dir.name,
        'plan_dir': str(plan_dir),
        'total_files': manifest['total_files'],
        'by_kind': manifest['by_kind'],
        'entries': manifest['entries'],
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Collect and classify plan directory artifacts',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Collect artifacts', allow_abbrev=False)
    add_plan_id_arg(run_parser, required=True)
    run_parser.add_argument(
        '--archived-plan-path',
        default=None,
        help='Archived plan root (archived mode only; live mode ignores it). When omitted, archived mode falls back to a synthetic per-plan tmp dir.',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
