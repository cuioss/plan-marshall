#!/usr/bin/env python3
"""Out-of-scope verify-failure classifier for phase-5-execute Step 11 triage.

Cross-references the file paths that produced a verify failure against the
plan's declared modified_files (from references.json) and returns a summary
that the triage step uses to annotate its [BLOCKED] message and AskUserQuestion
shape.

Usage:
    verify_failure_scope.py classify --plan-id <id> --error-paths <csv> [...]
    verify_failure_scope.py --help

Subcommands:
    classify  Classify a comma-separated list of error paths against
              references.json:modified_files; emit a summary TOON block.

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


def _resolve_plan_dir(plan_id: str) -> Path:
    """Resolve the plan directory under .plan/local/plans/{plan_id}/."""
    result = subprocess.run(
        ['git', 'rev-parse', '--git-common-dir'],
        check=True,
        capture_output=True,
        text=True,
    )
    git_common = Path(result.stdout.strip())
    if not git_common.is_absolute():
        git_common = (Path.cwd() / git_common).resolve()
    repo_root = git_common.parent
    return repo_root / '.plan' / 'local' / 'plans' / plan_id


def _read_modified_files(plan_dir: Path) -> list[str]:
    """Return the declared modified_files list, or raise FileNotFoundError."""
    refs_path = plan_dir / 'references.json'
    if not refs_path.exists():
        raise FileNotFoundError(str(refs_path))
    refs = json.loads(refs_path.read_text())
    return list(refs.get('modified_files', []) or [])


def classify_failure_scope(
    plan_id: str,
    error_paths: list[str],
    *,
    plan_dir: Path | None = None,
) -> dict:
    """Classify error_paths against the plan's modified_files.

    Args:
        plan_id:      Plan identifier (used to resolve references.json).
        error_paths:  Iterable of file paths reported by the failing verify
                      command. Empty list is a valid input (total=0).
        plan_dir:     Optional override for the plan directory (test seam).

    Returns:
        Dict with the TOON-serialisable summary fields.
    """
    if plan_dir is None:
        plan_dir = _resolve_plan_dir(plan_id)
    try:
        declared = set(_read_modified_files(plan_dir))
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
        help='Classify error paths against references.json:modified_files',
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
