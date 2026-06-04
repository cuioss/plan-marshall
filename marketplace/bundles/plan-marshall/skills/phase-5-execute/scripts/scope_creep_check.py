#!/usr/bin/env python3
"""Pre-task scope-creep guard for phase-5-execute.

Computes the residual file-set drift since plan creation - files modified that
are NOT declared in the union of all deliverables' affected_files - and emits a
scope_creep_warning finding when the residual cardinality exceeds the
configured threshold.

Usage:
    scope_creep_check.py check --plan-id <id> [--threshold <int>]
    scope_creep_check.py --help

Subcommands:
    check  Compute residual and emit finding when residual_count > threshold

The script reads `plan_creation_sha` from references.json, computes the file
diff between that sha and the current worktree HEAD, subtracts the union of
each deliverable's `affected_files`, and emits a scope_creep_warning finding
via manage-findings qgate add when the residual exceeds threshold.

Threshold sources (precedence):
    1. --threshold CLI flag
    2. phase_5.scope_creep_threshold in marshal.json plan-scoped config
    3. Default: 5
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from file_ops import get_plan_dir  # type: ignore[import-not-found]

DEFAULT_THRESHOLD = 5


def _git_diff_files(worktree: Path, base_sha: str) -> list[str]:
    """Return the list of files changed between base_sha and HEAD."""
    result = subprocess.run(
        ['git', '-C', str(worktree), 'diff', '--name-only', f'{base_sha}..HEAD'],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _read_references(plan_dir: Path) -> dict:
    """Read references.json from the plan directory."""
    path = plan_dir / 'references.json'
    if not path.exists():
        return {}
    data: dict = json.loads(path.read_text())
    return data


def _collect_declared_files(plan_dir: Path) -> set[str]:
    """Collect the union of affected_files and every TASK-*.json step target."""
    declared: set[str] = set()
    refs = _read_references(plan_dir)
    declared.update(refs.get('affected_files', []) or [])
    for task_file in sorted(plan_dir.glob('TASK-*.json')):
        try:
            task = json.loads(task_file.read_text())
        except json.JSONDecodeError:
            continue
        for step in task.get('steps', []) or []:
            target = step.get('target')
            if target:
                declared.add(target)
    return declared


def _resolve_worktree(plan_id: str) -> Path:
    """Resolve the active worktree path for the plan, or fall back to cwd."""
    result = subprocess.run(
        [
            'python3',
            '.plan/execute-script.py',
            'plan-marshall:manage-status:manage-status',
            'get-worktree-path',
            '--plan-id',
            plan_id,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith('worktree_path:'):
            value = line.split(':', 1)[1].strip().strip('"').strip("'")
            if value and value != '""':
                return Path(value)
    return Path.cwd()


def _emit_finding(plan_id: str, residual: list[str], threshold: int) -> bool:
    """Emit a scope_creep_warning finding via manage-findings qgate add."""
    detail = f'{len(residual)} file(s) outside declared scope (threshold={threshold})'
    message = f'Scope creep detected: {", ".join(sorted(residual)[:10])}'
    cmd = [
        'python3',
        '.plan/execute-script.py',
        'plan-marshall:manage-findings:manage-findings',
        'qgate',
        'add',
        '--plan-id',
        plan_id,
        '--phase',
        '5-execute',
        '--source',
        'qgate',
        '--type',
        'scope_creep_warning',
        '--severity',
        'warning',
        '--message',
        message,
        '--detail',
        detail,
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return result.returncode == 0


def cmd_check(args: argparse.Namespace) -> int:
    """Run the scope-creep check and emit a finding when residual exceeds threshold."""
    plan_id = args.plan_id
    threshold = args.threshold if args.threshold is not None else DEFAULT_THRESHOLD
    if threshold == 0:
        print('status: success')
        print('residual_count: 0')
        print(f'threshold: {threshold}')
        print('finding_emitted: false')
        print('disabled: true')
        return 0

    plan_dir = get_plan_dir(plan_id)
    worktree = _resolve_worktree(plan_id)
    refs = _read_references(plan_dir)
    base_sha = refs.get('plan_creation_sha')
    if not base_sha:
        # No baseline to compare against; treat as no drift.
        print('status: success')
        print('residual_count: 0')
        print(f'threshold: {threshold}')
        print('finding_emitted: false')
        print('reason: no_baseline_sha')
        return 0

    try:
        changed = _git_diff_files(worktree, base_sha)
    except subprocess.CalledProcessError as exc:
        print('status: error')
        print(f'error: git_diff_failed: {exc}')
        return 1

    declared = _collect_declared_files(plan_dir)
    residual = sorted(set(changed) - declared)
    emitted = False
    if len(residual) > threshold:
        emitted = _emit_finding(plan_id, residual, threshold)

    print('status: success')
    print(f'residual_count: {len(residual)}')
    print(f'threshold: {threshold}')
    print(f'finding_emitted: {"true" if emitted else "false"}')
    if residual:
        print(f'residual_files[{len(residual)}]: {residual}')
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description='Pre-task scope-creep guard.',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    check_parser = subparsers.add_parser(
        'check', help='Run scope-creep check', allow_abbrev=False
    )
    check_parser.add_argument('--plan-id', required=True)
    check_parser.add_argument('--threshold', type=int, default=None)
    check_parser.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
