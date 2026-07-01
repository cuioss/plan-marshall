#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Out-of-scope verify-failure classifier for phase-5-execute Step 11 triage.

Cross-references the file paths that produced a verify failure against the
plan's live footprint — the on-demand ``compute-footprint`` derivation
(``{base}...HEAD`` ∪ porcelain) read straight from the worktree — and returns a
summary that the triage step uses to annotate its [BLOCKED] message and
AskUserQuestion shape.

Usage:
    verify_failure_scope.py classify --plan-id <id> --error-paths <csv> [...]
    verify_failure_scope.py --help

Subcommands:
    classify  Classify a comma-separated list of error paths against the live
              plan footprint; emit a summary TOON block.

Return TOON shape:
    status: success
    total: N
    in_scope_count: I
    out_of_scope_count: O
    exclusively_out_of_scope: true|false
    out_of_scope_paths[O]: [paths]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _references_core import (  # type: ignore[import-not-found]
    compute_plan_branch_diff,
    resolve_base_ref,
)
from file_ops import get_plan_dir  # type: ignore[import-not-found]


def _resolve_worktree_root(plan_dir: Path) -> Path:
    """Resolve the worktree root from status.metadata.worktree_path.

    Falls back to the current working directory when no worktree is
    materialised (main-checkout flow). The status.json is read directly to keep
    this command self-contained.
    """
    status_path = plan_dir / 'status.json'
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text())
        except (ValueError, OSError):
            status = {}
        if isinstance(status, dict):
            metadata = status.get('metadata', {})
            if isinstance(metadata, dict):
                worktree_path = metadata.get('worktree_path', '')
                if isinstance(worktree_path, str) and worktree_path:
                    candidate = Path(worktree_path)
                    if candidate.is_dir():
                        return candidate
    return Path.cwd()


def _resolve_declared_footprint(plan_dir: Path) -> set[str]:
    """Return the live plan footprint, or raise FileNotFoundError.

    Reads references.json only to resolve the base ref, then derives the
    footprint live from the worktree via ``compute_plan_branch_diff``. When the
    git derivation fails (e.g. an archived plan with no live worktree), the
    footprint degrades to the empty set so classification still proceeds — every
    error path is then treated as out-of-scope.
    """
    refs_path = plan_dir / 'references.json'
    if not refs_path.exists():
        raise FileNotFoundError(str(refs_path))
    try:
        refs = json.loads(refs_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        refs = {}
    if not isinstance(refs, dict):
        refs = {}
    base_ref = resolve_base_ref(None, refs)
    worktree = _resolve_worktree_root(plan_dir)
    try:
        return compute_plan_branch_diff(worktree, base_ref)
    except subprocess.CalledProcessError:
        return set()


def classify_failure_scope(
    plan_id: str,
    error_paths: list[str],
    *,
    plan_dir: Path | None = None,
) -> dict:
    """Classify error_paths against the plan's live footprint.

    Args:
        plan_id:      Plan identifier (used to resolve references.json).
        error_paths:  Iterable of file paths reported by the failing verify
                      command. Empty list is a valid input (total=0).
        plan_dir:     Optional override for the plan directory (test seam).

    Returns:
        Dict with the TOON-serialisable summary fields.
    """
    if plan_dir is None:
        plan_dir = get_plan_dir(plan_id)
    try:
        declared = _resolve_declared_footprint(plan_dir)
    except FileNotFoundError as exc:
        return {
            'status': 'error',
            'error': 'references_json_missing',
            'detail': str(exc),
        }

    cleaned = [p for p in error_paths if p and p.strip()]
    in_scope: list[str] = []
    out_of_scope: list[str] = []
    for path in cleaned:
        if path in declared:
            in_scope.append(path)
        else:
            out_of_scope.append(path)

    total = len(cleaned)
    exclusively = total > 0 and len(in_scope) == 0 and len(out_of_scope) == total
    return {
        'status': 'success',
        'total': total,
        'in_scope_count': len(in_scope),
        'out_of_scope_count': len(out_of_scope),
        'exclusively_out_of_scope': exclusively,
        'out_of_scope_paths': out_of_scope,
    }


def _emit_toon(payload: dict) -> None:
    """Print a minimal TOON block matching the documented contract."""
    print(f'status: {payload.get("status", "success")}')
    if payload.get('status') == 'error':
        print(f'error: {payload.get("error", "unknown")}')
        if 'detail' in payload:
            print(f'detail: {payload["detail"]}')
        return
    print(f'total: {payload["total"]}')
    print(f'in_scope_count: {payload["in_scope_count"]}')
    print(f'out_of_scope_count: {payload["out_of_scope_count"]}')
    print(
        'exclusively_out_of_scope: '
        + ('true' if payload['exclusively_out_of_scope'] else 'false')
    )
    paths = payload['out_of_scope_paths']
    if paths:
        print(f'out_of_scope_paths[{len(paths)}]: {paths}')


def cmd_classify(args: argparse.Namespace) -> int:
    """Run the classifier and emit the summary TOON to stdout."""
    error_paths = []
    if args.error_paths:
        error_paths = [p.strip() for p in args.error_paths.split(',') if p.strip()]
    payload = classify_failure_scope(args.plan_id, error_paths)
    _emit_toon(payload)
    return 0 if payload.get('status') == 'success' else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description='Out-of-scope verify-failure classifier.',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    classify_parser = subparsers.add_parser(
        'classify',
        help='Classify error paths against the live plan footprint',
        allow_abbrev=False,
    )
    classify_parser.add_argument('--plan-id', required=True)
    classify_parser.add_argument(
        '--error-paths',
        default='',
        help='Comma-separated list of error file paths',
    )
    classify_parser.set_defaults(func=cmd_classify)

    args = parser.parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
