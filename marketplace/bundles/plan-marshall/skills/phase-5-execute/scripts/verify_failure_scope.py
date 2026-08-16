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
    footprint_resolved: true|false
    total: N
    in_scope_count: I
    out_of_scope_count: O
    exclusively_out_of_scope: true|false
    out_of_scope_paths[O]: [paths]
    unclassified_paths[N]: [paths]     # only when footprint_resolved: false

``footprint_resolved: false`` means the live footprint could not be derived, so
NO path was classified: both scope counts are zero, every error path is listed
under ``unclassified_paths``, and ``exclusively_out_of_scope`` is ``false``
because nothing substantiates it. An unmeasurable footprint is never reported as
an empty one — that read classified every failure as foreign to the plan.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _references_core import (
    compute_plan_branch_diff,
    resolve_base_ref,
)
from file_ops import WorktreeResolutionError, get_plan_dir, resolve_plan_context


def _resolve_declared_footprint(plan_dir: Path, plan_id: str) -> set[str] | None:
    """Return the live plan footprint, ``None`` if unmeasurable, or raise FileNotFoundError.

    Reads references.json only to resolve the base ref, then derives the
    footprint live from the worktree via ``compute_plan_branch_diff``.

    A failed git derivation (e.g. an archived plan whose worktree finalize
    already removed) returns ``None`` — the footprint is **unmeasurable**, which
    is NOT the empty set. The empty set is a measurement meaning "the plan
    touched no files", and returning it here classified every error path as
    out-of-scope and set ``exclusively_out_of_scope``, telling the triage step
    that none of the failures belonged to the plan — a confident attribution
    derived from an input nobody measured. See :func:`classify_failure_scope`
    for how the unmeasurable state is reported instead.

    The worktree face comes from the single plan-context resolver rather than a
    private re-derivation that hand-read ``status.metadata.worktree_path``.
    ``ensure=False`` keeps this a routing lookup: classifying a verify failure
    must not materialize or existence-check the plan. An unresolvable worktree
    degrades to the current working directory, preserving the previous
    non-fatal behaviour for archived plans and test seams.
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
    try:
        worktree = Path(resolve_plan_context(plan_id, ensure=False).worktree_path)
    except WorktreeResolutionError:
        worktree = Path.cwd()
    try:
        return compute_plan_branch_diff(worktree, base_ref)
    except subprocess.CalledProcessError:
        return None


def classify_failure_scope(
    plan_id: str,
    error_paths: list[str],
    *,
    plan_dir: Path | None = None,
) -> dict:
    """Classify error_paths against the plan's live footprint.

    When the footprint is UNMEASURABLE (:func:`_resolve_declared_footprint`
    returns ``None``), no path can be classified: the result reports
    ``footprint_resolved: false``, leaves both scope counts at zero, and forces
    ``exclusively_out_of_scope`` to ``false``. That flag drives a real action —
    phase-5-execute Step 11 offers "Stash foreign files and re-verify" as the
    DEFAULT remedy when it is true — so asserting it from an unmeasured footprint
    would recommend stashing on no evidence. ``false`` routes the caller to the
    ordinary triage path, where the plan owns its failures unless proven
    otherwise, and the explicit flag keeps the unmeasured state legible rather
    than disguising it as a measured "nothing foreign here".

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
        declared = _resolve_declared_footprint(plan_dir, plan_id)
    except FileNotFoundError as exc:
        return {
            'status': 'error',
            'error': 'references_json_missing',
            'detail': str(exc),
        }

    cleaned = [p for p in error_paths if p and p.strip()]

    if declared is None:
        return {
            'status': 'success',
            'footprint_resolved': False,
            'total': len(cleaned),
            'in_scope_count': 0,
            'out_of_scope_count': 0,
            'exclusively_out_of_scope': False,
            'out_of_scope_paths': [],
            'unclassified_paths': cleaned,
        }

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
        'footprint_resolved': True,
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
    # Emitted unconditionally: a consumer must be able to tell a measured
    # classification from one that could not be performed, and an absent field
    # would read as the measured case.
    print('footprint_resolved: ' + ('true' if payload.get('footprint_resolved') else 'false'))
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
    unclassified = payload.get('unclassified_paths') or []
    if unclassified:
        print(f'unclassified_paths[{len(unclassified)}]: {unclassified}')


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
