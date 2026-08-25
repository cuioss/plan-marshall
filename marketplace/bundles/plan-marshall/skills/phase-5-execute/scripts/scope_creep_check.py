#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
each deliverable's `affected_files`, and persists a scope_creep_warning finding
through the in-process `add_qgate_finding` primitive when the residual exceeds
threshold. A persist the primitive REJECTS is reported as `status: error` with
`error: finding_persist_failed` and a non-zero return code — never as a success
carrying `finding_emitted: false`, which is indistinguishable from "no creep".

An UNMEASURED run cannot render as a measured clean one
-------------------------------------------------------
Two paths perform no comparison at all: a plan with no `plan_creation_sha` (no
baseline to diff against) and an explicitly disabled guard (`--threshold 0`).
Both used to print `status: success` with `residual_count: 0`, and the count is
the field consumers gate on — the `reason` that disambiguated it was advisory and
trivially dropped, so "never measured" was indistinguishable from "measured, none
found".

Those paths now return `status: could_not_look` and OMIT `residual_count`
entirely. The absence is the point: a caller branching on `residual_count == 0`
finds no key rather than a zero it would read as a clean result, so the
unmeasured state is structurally unable to render as a measured one. The measured
paths are unchanged — a genuine zero still reports `status: success` with
`residual_count: 0`.

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

from _findings_core import QGATE_PERSIST_OK, add_qgate_finding
from file_ops import WorktreeResolutionError, get_plan_dir, resolve_plan_context

DEFAULT_THRESHOLD = 5

STATUS_COULD_NOT_LOOK = 'could_not_look'
"""Status for a run that performed no comparison at all.

Distinct from ``success`` (the comparison ran) and from ``error`` (something
went wrong). Nothing failed here — the guard simply had nothing to measure — and
a run that measured nothing must not be reported in the vocabulary of one that
measured and found nothing.
"""


def _emit_could_not_look(reason: str, detail: str, threshold: int) -> int:
    """Report that no comparison was performed, WITHOUT a residual count.

    The omission is load-bearing and is the whole remedy: ``residual_count`` is
    the field consumers gate on, so publishing a ``0`` here would render an
    unmeasured state as a measured clean one. A caller reading the key finds it
    absent, which no consumer can mistake for "no scope creep".

    ``finding_emitted: false`` is still published because it is TRUE and
    unambiguous — no finding was emitted, and no reading of that field implies a
    comparison happened.

    Args:
        reason: Short token naming which half could not look.
        detail: One-line explanation of what was missing.
        threshold: The resolved threshold, echoed for the caller's audit trail.

    Returns:
        ``0`` — an unmeasurable guard is not a failure of the run it guards.
    """
    print(f'status: {STATUS_COULD_NOT_LOOK}')
    print(f'reason: {reason}')
    print(f'detail: {detail}')
    print(f'threshold: {threshold}')
    print('finding_emitted: false')
    return 0


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
    """Resolve the active worktree path for the plan, or fall back to cwd.

    Routes through the single plan-context resolver rather than re-implementing
    the ``manage-status get-worktree-path`` shell-out and hand-parsing its TOON.
    ``ensure=False`` keeps this a routing lookup: classifying scope creep must
    not materialize or existence-check the plan.

    The main-checkout flow (``use_worktree=false``) is handled inside the
    resolver, which returns the cwd-relative checkout root — strictly better
    than the bare ``Path.cwd()`` this used to fall back to, since it walks up to
    the checkout root instead of trusting wherever the caller happened to be.
    The ``Path.cwd()`` fallback survives only for the genuinely unresolvable
    case, preserving the previous non-fatal behaviour.
    """
    try:
        return Path(resolve_plan_context(plan_id, ensure=False).worktree_path)
    except WorktreeResolutionError:
        return Path.cwd()


def _emit_finding(plan_id: str, residual: list[str], threshold: int) -> dict[str, str] | None:
    """Persist a scope_creep_warning finding via the in-process Q-Gate primitive.

    Calls ``add_qgate_finding`` directly — the same primitive nine peer callers
    use — so there is no argv to construct and no return code to misread. The
    outcome is tested against the published ``QGATE_PERSIST_OK`` partition.

    Returns ``None`` when the finding reached the store, and a failure descriptor
    — ``{'title', 'detail', 'message'}`` — when the primitive REJECTED it, so
    ``cmd_check`` can fail loud with the rejected content inline.
    """
    title = f'Scope creep detected: {", ".join(sorted(residual)[:10])}'
    detail = f'{len(residual)} file(s) outside declared scope (threshold={threshold})'
    result = add_qgate_finding(
        plan_id=plan_id,
        phase='5-execute',
        source='qgate',
        finding_type='scope_creep_warning',
        title=title,
        detail=detail,
        component='plan-marshall:phase-5-execute:scope_creep_check',
        severity='warning',
    )
    if result.get('status') not in QGATE_PERSIST_OK:
        return {
            'title': title,
            'detail': detail,
            'message': str(result.get('message', '')),
        }
    return None


def cmd_check(args: argparse.Namespace) -> int:
    """Run the scope-creep check and emit a finding when residual exceeds threshold."""
    plan_id = args.plan_id
    threshold = args.threshold if args.threshold is not None else DEFAULT_THRESHOLD
    if threshold == 0:
        # The guard is switched off, so it examined nothing. That is a
        # could-not-look, not a clean result.
        return _emit_could_not_look(
            'guard_disabled',
            'threshold=0 disables the guard, so no comparison was performed; '
            'residual_count is omitted because nothing was measured',
            threshold,
        )

    plan_dir = get_plan_dir(plan_id)
    worktree = _resolve_worktree(plan_id)
    refs = _read_references(plan_dir)
    base_sha = refs.get('plan_creation_sha')
    if not base_sha:
        # No baseline sha means there was nothing to diff against — the guard
        # could not look. Reporting a zero here is the defect this branch fixes.
        return _emit_could_not_look(
            'no_baseline_sha',
            'references.json carries no plan_creation_sha, so no diff was computed; '
            'residual_count is omitted because nothing was measured',
            threshold,
        )

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
        failure = _emit_finding(plan_id, residual, threshold)
        if failure is not None:
            # A lost finding is never absorbed: reporting `status: success` with
            # `finding_emitted: false` here would be indistinguishable from "no
            # scope creep". Fail loud with the rejected finding's content inline.
            print('status: error')
            print('error: finding_persist_failed')
            print(f'message: {failure["message"]}')
            print(f'finding_title: {failure["title"]}')
            print(f'finding_detail: {failure["detail"]}')
            print(f'residual_count: {len(residual)}')
            print(f'threshold: {threshold}')
            print(f'residual_files[{len(residual)}]: {residual}')
            return 1
        emitted = True

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
