#!/usr/bin/env python3
"""Collect and classify artifacts present in a plan directory.

Ported and adapted from ``.claude/skills/verify-workflow/scripts/collect-artifacts.py``.
Supports two modes:

- ``live``: resolve the plan directory from ``--plan-id`` using
  ``file_ops.base_path`` (reads ``PLAN_BASE_DIR`` env var or the project-local
  ``.plan/local`` tree).
- ``archived``: read the plan directory directly from
  ``--archived-plan-path``. No base-dir lookup happens.

Output: TOON manifest listing every file found under the plan directory,
grouped by kind (``status``, ``request``, ``solution_outline``,
``references``, ``tasks``, ``logs``, ``metrics``, ``reports``, ``other``).
The manifest is consumed by ``check-artifact-consistency.py`` and the
retrospective orchestrator.

Usage:
    python3 collect-plan-artifacts.py run --plan-id my-plan --mode live
    python3 collect-plan-artifacts.py run --archived-plan-path /abs/path --mode archived
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]

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


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan directory based on mode.

    Raises ``ValueError`` when the provided inputs are inconsistent or the
    resolved directory does not exist.
    """
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        plan_dir = base_path('plans', plan_id)
    elif mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        plan_dir = Path(archived_plan_path)
    else:
        raise ValueError(f"Unknown mode: {mode!r} — expected 'live' or 'archived'")

    if not plan_dir.exists():
        raise ValueError(f'Plan directory does not exist: {plan_dir}')
    if not plan_dir.is_dir():
        raise ValueError(f'Plan path is not a directory: {plan_dir}')
    return plan_dir


def collect_manifest(plan_dir: Path) -> dict[str, Any]:
    """Walk the plan directory and build the manifest.

    Each entry contains ``path`` (plan-relative), ``kind`` (classification
    label), and ``size_bytes``. Directories are not listed; only files.
    """
    entries: list[dict[str, Any]] = []
    by_kind: dict[str, int] = {}

    for path in sorted(plan_dir.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(plan_dir)
        kind = classify_file(rel)
        size = path.stat().st_size
        entries.append({'path': str(rel), 'kind': kind, 'size_bytes': size})
        by_kind[kind] = by_kind.get(kind, 0) + 1

    return {
        'entries': entries,
        'by_kind': by_kind,
        'total_files': len(entries),
    }


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    manifest = collect_manifest(plan_dir)

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
    run_parser.add_argument('--plan-id', help='Plan identifier (live mode)')
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
