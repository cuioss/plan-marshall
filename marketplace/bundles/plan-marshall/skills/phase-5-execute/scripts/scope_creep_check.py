#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-task scope-creep guard for phase-5-execute.

Computes the residual file-set drift since plan creation - files modified that
are NOT declared in the union of all deliverables' affected_files - and files a
``triage`` Q-Gate finding carrying the rule key ``scope_creep_warning`` when the
residual cardinality exceeds the configured threshold.

Usage:
    scope_creep_check.py check --plan-id <id> [--threshold <int>]
    scope_creep_check.py --help

Subcommands:
    check  Compute residual and emit finding when residual_count > threshold

The script reads `plan_creation_sha` from references.json, computes the file
diff between that sha and the current worktree HEAD, subtracts the union of
each deliverable's `affected_files`, and persists the warning through the
in-process `add_qgate_finding` primitive when the residual exceeds threshold.
The record is filed as type `triage` — the type the peer guards use for their
own Q-Gate findings — with `rule: scope_creep_warning` as the key that names
this guard. A persist the primitive REJECTS is reported as `status: error` with
`error: finding_persist_failed` and a non-zero return code — never as a success
carrying `finding_emitted: false`, which is indistinguishable from "no creep".

A residual set already settled is not filed again
-------------------------------------------------
The detail carries a digest of the COMPLETE sorted residual list
(`residual_set=` plus twelve hex characters), because the title names ten paths
at most and two different sets must not read as the same one. Before persisting,
the guard reads the phase-5 Q-Gate store: when a record with this rule, this
title and this detail is already resolved as `accepted` or `suppressed`, the
same residual set has been decided and nothing is filed. That one case reports
the measured shape with `finding_emitted: false` plus `finding_resolved_as` and
`finding_hash_id`, the two fields that appear in no other case. A changed set
has a different digest, so it is filed as a new finding. Every other outcome —
no such record, a record resolved any other way, or a store read that did not
succeed — goes to the primitive exactly as before: a pending record is
deduplicated and a record resolved any other way is reopened.

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
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from _findings_core import QGATE_PERSIST_OK, add_qgate_finding, query_qgate_findings
from constants import RESOLUTION_ACCEPTED, RESOLUTION_SUPPRESSED
from file_ops import WorktreeResolutionError, get_plan_dir, resolve_plan_context
from toon_parser import serialize_toon

DEFAULT_THRESHOLD = 5

_PHASE = '5-execute'
_FINDING_TYPE = 'triage'
_RULE = 'scope_creep_warning'
_RESIDUAL_DIGEST_LENGTH = 12

_SETTLED_RESOLUTIONS = frozenset({RESOLUTION_ACCEPTED, RESOLUTION_SUPPRESSED})
"""Resolutions that mean an operator has decided this exact residual set.

Only these two stop a re-file. A record resolved any other way (``fixed``,
``taken_into_account``, ``rejected``) claims the residual is gone or was never
real, so measuring the same set again is a genuine re-detection and the persist
primitive reopens it.
"""

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
    print(
        serialize_toon(
            {
                'status': STATUS_COULD_NOT_LOOK,
                'reason': reason,
                'detail': detail,
                'threshold': threshold,
                'finding_emitted': False,
            }
        )
    )
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


def _residual_digest(residual: list[str]) -> str:
    """Return a short digest of the COMPLETE sorted residual list.

    The title names ten paths at most, so two residual sets that share their
    first ten sorted paths would otherwise produce the same title and the same
    count-and-threshold detail. The digest covers every path, which is what lets
    the detail tell one set from another.
    """
    joined = '\n'.join(sorted(residual))
    return hashlib.sha256(joined.encode('utf-8')).hexdigest()[:_RESIDUAL_DIGEST_LENGTH]


def _finding_content(residual: list[str], threshold: int) -> tuple[str, str]:
    """Return the ``(title, detail)`` the warning is filed under.

    Built in one place because the settled-record lookup and the persist call
    must compare and write the SAME two strings.
    """
    title = f'Scope creep detected: {", ".join(sorted(residual)[:10])}'
    detail = (
        f'{len(residual)} file(s) outside declared scope (threshold={threshold}); '
        f'residual_set={_residual_digest(residual)}'
    )
    return title, detail


def _find_settled_finding(plan_id: str, title: str, detail: str) -> dict[str, Any] | None:
    """Return the record that already settled this exact residual set, if any.

    A match carries this guard's rule, the title and detail about to be filed,
    and a resolution of ``accepted`` or ``suppressed``.

    Returns ``None`` when the store read does not return ``success``. An
    unreadable store is no evidence that the set was settled, so the caller
    files the finding as before and the persist primitive reports the store's
    own failure.
    """
    result = query_qgate_findings(plan_id, _PHASE)
    if result.get('status') != 'success':
        return None
    for record in result.get('findings') or []:
        if (
            record.get('rule') == _RULE
            and record.get('title') == title
            and record.get('detail') == detail
            and record.get('resolution') in _SETTLED_RESOLUTIONS
        ):
            settled: dict[str, Any] = record
            return settled
    return None


def _emit_finding(plan_id: str, residual: list[str], threshold: int) -> dict[str, str] | None:
    """File the scope-creep warning as a ``triage`` Q-Gate finding.

    The record carries ``rule: scope_creep_warning``; the type is ``triage``,
    the one the peer guards file their Q-Gate findings under. Calls
    ``add_qgate_finding`` directly — the same primitive the peer callers use —
    so there is no argv to construct and no return code to misread. The outcome
    is tested against the published ``QGATE_PERSIST_OK`` partition.

    The caller skips this function when the same residual set is already
    resolved as ``accepted`` or ``suppressed`` (see :func:`_find_settled_finding`).

    Returns ``None`` when the finding reached the store, and a failure descriptor
    — ``{'title', 'detail', 'message'}`` — when the primitive REJECTED it, so
    ``cmd_check`` can fail loud with the rejected content inline.
    """
    title, detail = _finding_content(residual, threshold)
    result = add_qgate_finding(
        plan_id=plan_id,
        phase=_PHASE,
        source='qgate',
        finding_type=_FINDING_TYPE,
        title=title,
        detail=detail,
        component='plan-marshall:phase-5-execute:scope_creep_check',
        severity='warning',
        rule=_RULE,
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
    base_sha = (refs.get('plan_creation_sha') or '').strip()
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
        print(serialize_toon({'status': 'error', 'error': f'git_diff_failed: {exc}'}))
        return 1

    declared = _collect_declared_files(plan_dir)
    residual = sorted(set(changed) - declared)
    emitted = False
    settled: dict[str, Any] | None = None
    if len(residual) > threshold:
        settled = _find_settled_finding(plan_id, *_finding_content(residual, threshold))
    if len(residual) > threshold and settled is None:
        failure = _emit_finding(plan_id, residual, threshold)
        if failure is not None:
            # A lost finding is never absorbed: reporting `status: success` with
            # `finding_emitted: false` here would be indistinguishable from "no
            # scope creep". Fail loud with the rejected finding's content inline.
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'error': 'finding_persist_failed',
                        'message': failure['message'],
                        'finding_title': failure['title'],
                        'finding_detail': failure['detail'],
                        'residual_count': len(residual),
                        'threshold': threshold,
                        'residual_files': residual,
                    }
                )
            )
            return 1
        emitted = True

    emitted_payload: dict[str, object] = {
        'status': 'success',
        'residual_count': len(residual),
        'threshold': threshold,
        'finding_emitted': emitted,
    }
    if settled is not None:
        # The one case in which these two fields appear: this exact residual set
        # was already decided, so nothing was filed.
        emitted_payload['finding_resolved_as'] = settled.get('resolution')
        emitted_payload['finding_hash_id'] = settled.get('hash_id')
    if residual:
        emitted_payload['residual_files'] = residual
    print(serialize_toon(emitted_payload))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description='Pre-task scope-creep guard.',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    check_parser = subparsers.add_parser('check', help='Run scope-creep check', allow_abbrev=False)
    check_parser.add_argument('--plan-id', required=True)
    check_parser.add_argument('--threshold', type=int, default=None)
    check_parser.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
