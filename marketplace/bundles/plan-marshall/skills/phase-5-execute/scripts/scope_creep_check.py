#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-task scope-creep guard for phase-5-execute.

Computes the residual file-set drift of the plan's own changes since the branch
diverged from its base - files modified that are NOT declared in the union of
all deliverables' affected_files - and files a
``triage`` Q-Gate finding carrying the rule key ``scope_creep_warning`` when the
residual cardinality exceeds the configured threshold.

Usage:
    scope_creep_check.py check --plan-id <id> [--threshold <int>]
    scope_creep_check.py --help

Subcommands:
    check  Compute residual and emit finding when residual_count > threshold

The script reads `base_branch` from references.json (absent or blank reads as
`main`), resolves the merge-base of the worktree HEAD and `origin/{base_branch}`,
computes the file diff from that merge-base to HEAD, subtracts the union of
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
title and this `residual_set=` term is already resolved as `accepted` or
`suppressed`, the same residual set has been decided and nothing is filed. The
threshold the detail also names is not compared, so the decision holds when a
later run measures the same set at a different threshold. That one case reports
the measured shape with `finding_emitted: false` plus `finding_resolved_as` and
`finding_hash_id`, the two fields that appear in no other case. A changed set
has a different digest, so it is filed as a new finding. Every other outcome —
no such record, a record resolved any other way, or a store read that did not
succeed — goes to the primitive exactly as before: a pending record is
deduplicated and a record resolved any other way is reopened.

The baseline is the merge-base, recomputed on every run
-------------------------------------------------------
The range `{merge-base}..HEAD` is exactly the branch's own commits. It is the
same anchor and the same range `baseline-reconcile` uses for the files a plan
has in flight. A commit recorded when the plan was created cannot stand in for
it: when the worktree is branched from a newer commit of the base branch, or the
base is merged into the branch, a range starting at that older commit also
covers base commits the branch merely contains, and their files count as
residual although the plan never touched them.

The guard does not fetch. It compares against `origin/{base_branch}` as the
local repository already has it, so a run never changes any ref.

An UNMEASURED run cannot render as a measured clean one
-------------------------------------------------------
Two paths perform no comparison at all: an unresolved merge-base (`origin/
{base_branch}` does not resolve, or the two histories share no commit, so there
is no baseline to diff against) and an explicitly disabled guard (a resolved
threshold of `0`, from `--threshold 0` or from marshal.json). The count is the field consumers gate on, so a
`residual_count: 0` printed on either path would make "never measured"
indistinguishable from "measured, none found" — a `reason` beside it is advisory
and trivially dropped.

Those paths return `status: could_not_look` and OMIT `residual_count`
entirely. The absence is the point: a caller branching on `residual_count == 0`
finds no key rather than a zero it would read as a clean result, so the
unmeasured state is structurally unable to render as a measured one. The measured
paths are unchanged — a genuine zero still reports `status: success` with
`residual_count: 0`.

Threshold sources (precedence):
    1. --threshold CLI flag
    2. plan.phase-5-execute.scope_creep_threshold in marshal.json
    3. Default: 5

Every output that carries ``threshold`` names which of the three it came from in
``threshold_source`` (``flag`` / ``config`` / ``default``). The marshal.json key
is absent unless a project adds it; an absent key, an absent ``plan`` or
``phase-5-execute`` section and an absent marshal.json all mean "not
configured" and select the default silently.

A configuration that is PRESENT but unusable is a different state and is never
read as a value: a marshal.json that cannot be read or parsed, a section of the
wrong shape, or a key holding anything other than a non-negative integer. The
guard then runs at the default and says so — ``threshold_source: default`` plus
``threshold_config_error`` naming what was wrong. In particular an unusable
configuration never becomes ``0``: that value switches the guard off, and a
guard must not be switched off by a file nobody could read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _findings_core import QGATE_PERSIST_OK, add_qgate_finding, query_qgate_findings
from constants import RESOLUTION_ACCEPTED, RESOLUTION_SUPPRESSED
from file_ops import WorktreeResolutionError, get_plan_dir, resolve_plan_context
from toon_parser import serialize_toon

DEFAULT_THRESHOLD = 5
DEFAULT_BASE_BRANCH = 'main'

_PHASE = '5-execute'
_FINDING_TYPE = 'triage'
_RULE = 'scope_creep_warning'
_RESIDUAL_DIGEST_LENGTH = 12
_DETAIL_SEPARATOR = '; '

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


_CONFIG_PLAN_SECTION = 'plan'
_CONFIG_PHASE_SECTION = 'phase-5-execute'
_CONFIG_THRESHOLD_FIELD = 'scope_creep_threshold'
_CONFIG_THRESHOLD_KEY = f'{_CONFIG_PLAN_SECTION}.{_CONFIG_PHASE_SECTION}.{_CONFIG_THRESHOLD_FIELD}'
"""The marshal.json path of the threshold override, as documents name it."""

THRESHOLD_SOURCE_FLAG = 'flag'
THRESHOLD_SOURCE_CONFIG = 'config'
THRESHOLD_SOURCE_DEFAULT = 'default'


@dataclass(frozen=True)
class _Threshold:
    """The resolved threshold and where it came from.

    Attributes:
        value: The threshold the run uses. ``0`` switches the guard off.
        source: ``flag``, ``config`` or ``default``.
        config_error: Why a marshal.json value that is present could not be
            used, or ``None``. Only ever set beside ``source: default``.
    """

    value: int
    source: str
    config_error: str | None = None

    def fields(self) -> dict[str, Any]:
        """Return the output fields that report this threshold."""
        reported: dict[str, Any] = {'threshold': self.value, 'threshold_source': self.source}
        if self.config_error is not None:
            reported['threshold_config_error'] = self.config_error
        return reported


def _section(parent: dict[str, Any], key: str, path: str) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(section, problem)`` for the object ``parent[key]``.

    ``(None, None)`` when the key is absent, ``(None, problem)`` when it holds
    anything but an object.
    """
    if key not in parent:
        return None, None
    section = parent[key]
    if not isinstance(section, dict):
        return None, f'{path} in marshal.json is not an object'
    return section, None


def _read_configured_threshold() -> tuple[int | None, str | None]:
    """Read ``plan.phase-5-execute.scope_creep_threshold`` from marshal.json.

    Goes through ``manage-config``'s own reader (``_config_core.load_config``),
    the seam every other script reads marshal.json through, so this guard reads
    the same file a ``manage-config`` call in the same working directory does.
    The import is in-function: ``_config_core`` resolves its paths when it is
    imported, and a guard run outside any plan root must still be able to start.

    Returns:
        ``(value, problem)``. ``(value, None)`` for a usable configured value.
        ``(None, None)`` when nothing is configured - no marshal.json, or no such
        key. ``(None, problem)`` when a configuration is present and unusable;
        the caller falls back to the default and reports ``problem``. A boolean
        is rejected although it is an ``int`` in Python: ``true`` is not a count.
    """
    try:
        from _config_core import is_initialized, load_config
    except Exception as exc:  # importing executes another skill's module body
        return None, f'the marshal.json reader could not be loaded: {exc}'
    try:
        if not is_initialized():
            return None, None
        config = load_config()
    except (OSError, ValueError) as exc:
        return None, f'marshal.json could not be read: {exc}'

    plan, problem = _section(config, _CONFIG_PLAN_SECTION, _CONFIG_PLAN_SECTION)
    if plan is None:
        return None, problem
    phase, problem = _section(plan, _CONFIG_PHASE_SECTION, f'{_CONFIG_PLAN_SECTION}.{_CONFIG_PHASE_SECTION}')
    if phase is None or _CONFIG_THRESHOLD_FIELD not in phase:
        return None, problem
    value = phase[_CONFIG_THRESHOLD_FIELD]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None, f'{_CONFIG_THRESHOLD_KEY} must be a non-negative integer, got {value!r}'
    return value, None


def _resolve_threshold(flag_value: int | None) -> _Threshold:
    """Resolve the threshold: the flag, else marshal.json, else the default.

    An explicit flag wins outright and marshal.json is then not read at all, so
    an unreadable configuration cannot disturb a run that states its threshold.
    """
    if flag_value is not None:
        return _Threshold(flag_value, THRESHOLD_SOURCE_FLAG)
    configured, problem = _read_configured_threshold()
    if configured is not None:
        return _Threshold(configured, THRESHOLD_SOURCE_CONFIG)
    return _Threshold(DEFAULT_THRESHOLD, THRESHOLD_SOURCE_DEFAULT, problem)


def _emit_could_not_look(reason: str, detail: str, threshold: _Threshold) -> int:
    """Report that no comparison was performed, WITHOUT a residual count.

    Two paths reach this shape: the unresolved merge-base
    (``reason: merge_base_unresolved``) and the disabled guard
    (``reason: guard_disabled``).

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
        threshold: The resolved threshold and its source, echoed for the
            caller's audit trail.

    Returns:
        ``0`` — an unmeasurable guard is not a failure of the run it guards.
    """
    print(
        serialize_toon(
            {
                'status': STATUS_COULD_NOT_LOOK,
                'reason': reason,
                'detail': detail,
                **threshold.fields(),
                'finding_emitted': False,
            }
        )
    )
    return 0


def _resolve_merge_base(worktree: Path, base_branch: str) -> str | None:
    """Return ``merge-base(HEAD, origin/{base_branch})``, or ``None`` when unresolved.

    Recomputed from the local refs on every call and never fetched, so the guard
    changes no ref. ``None`` covers a non-zero exit (the remote-tracking ref does
    not resolve, or the two histories share no commit), empty output, and a git
    that could not be run at all — in each case there is no baseline to diff
    against.
    """
    try:
        result = subprocess.run(
            ['git', '-C', str(worktree), 'merge-base', 'HEAD', f'origin/{base_branch}'],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    merge_base = result.stdout.strip()
    if result.returncode != 0 or not merge_base:
        return None
    return merge_base


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


def _residual_set_term(residual: list[str]) -> str:
    """Return the ``residual_set=<digest>`` term that identifies one residual set.

    The one place the term is produced: the detail is written with it and the
    settled-record lookup searches for it, so the two cannot drift.
    """
    return f'residual_set={_residual_digest(residual)}'


def _finding_title(residual: list[str]) -> str:
    """Return the title the warning is filed under: the first ten sorted paths."""
    return f'Scope creep detected: {", ".join(sorted(residual)[:10])}'


def _finding_content(residual: list[str], threshold: int) -> tuple[str, str]:
    """Return the ``(title, detail)`` the warning is filed under.

    The detail has two ``; ``-separated terms. The first is for the reader: the
    residual count and the threshold the run used. The second is the
    ``residual_set=`` term, which together with the title is the identity of the
    residual set. The threshold is NOT part of that identity.
    """
    detail = (
        f'{len(residual)} file(s) outside declared scope (threshold={threshold}){_DETAIL_SEPARATOR}'
        f'{_residual_set_term(residual)}'
    )
    return _finding_title(residual), detail


def _find_settled_finding(plan_id: str, residual: list[str]) -> dict[str, Any] | None:
    """Return the record that already settled this exact residual set, if any.

    A record is identified by this guard's rule, the title of the residual set
    and its ``residual_set=`` term, and it settles the set when its resolution
    is ``accepted`` or ``suppressed``. The rest of the detail is not compared:
    it carries the threshold the filing run used, and a decision about a
    residual set holds at whatever threshold a later run measures it with.

    Returns ``None`` when the store read does not return ``success``. An
    unreadable store is no evidence that the set was settled, so the caller
    files the finding as before and the persist primitive reports the store's
    own failure.
    """
    result = query_qgate_findings(plan_id, _PHASE)
    if result.get('status') != 'success':
        return None
    title = _finding_title(residual)
    residual_set_term = _residual_set_term(residual)
    for record in result.get('findings') or []:
        if (
            record.get('rule') == _RULE
            and record.get('title') == title
            and residual_set_term in str(record.get('detail') or '').split(_DETAIL_SEPARATOR)
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
    resolved = _resolve_threshold(args.threshold)
    threshold = resolved.value
    if threshold == 0:
        # The guard is switched off, so it examined nothing. That is a
        # could-not-look, not a clean result.
        return _emit_could_not_look(
            'guard_disabled',
            'threshold=0 disables the guard, so no comparison was performed; '
            'residual_count is omitted because nothing was measured',
            resolved,
        )

    plan_dir = get_plan_dir(plan_id)
    worktree = _resolve_worktree(plan_id)
    refs = _read_references(plan_dir)
    base_branch = str(refs.get('base_branch') or '').strip() or DEFAULT_BASE_BRANCH
    merge_base = _resolve_merge_base(worktree, base_branch)
    if merge_base is None:
        # No merge-base means there was nothing to diff against — the guard
        # could not look. A zero here would read as a measured clean result.
        return _emit_could_not_look(
            'merge_base_unresolved',
            f'the merge-base of HEAD and origin/{base_branch} could not be resolved, '
            'so no diff was computed; residual_count is omitted because nothing was measured',
            resolved,
        )

    try:
        changed = _git_diff_files(worktree, merge_base)
    except subprocess.CalledProcessError as exc:
        print(serialize_toon({'status': 'error', 'error': f'git_diff_failed: {exc}'}))
        return 1

    declared = _collect_declared_files(plan_dir)
    residual = sorted(set(changed) - declared)
    emitted = False
    settled: dict[str, Any] | None = None
    if len(residual) > threshold:
        settled = _find_settled_finding(plan_id, residual)
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
                        **resolved.fields(),
                        'residual_files': residual,
                    }
                )
            )
            return 1
        emitted = True

    emitted_payload: dict[str, object] = {
        'status': 'success',
        'residual_count': len(residual),
        **resolved.fields(),
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
