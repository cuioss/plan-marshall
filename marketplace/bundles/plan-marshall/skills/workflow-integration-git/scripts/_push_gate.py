#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-push gate-head binding for the two push verbs of ``git-workflow``.

The pre-push quality gate is the last settle step before the push barrier, and the
``head_at_completion`` it persists on its ``done`` record IS the tree it validated.
Nothing used to compare that record with the HEAD a push would actually ship, so a
commit made after the gate — a fix commit, a rebase, an amend — was pushed as
"gated" when no gate had seen it. ``pre-push-quality-gate.md`` states the rule in
prose; this module is its mechanism.

Two answers, and their difference is load-bearing:

* **no recorded head** — the plan has no ``pre-push-quality-gate`` record (an early
  phase, a plan that never ran finalize, a plan whose status could not be read).
  Nothing was validated, so there is nothing to compare and the push proceeds. A
  refusal here would block every push a plan makes before finalize.
* **a recorded head that is not the HEAD being pushed** — the gate validated one
  tree and the push would ship another. Refused, naming both SHAs and the step.

The refusal is an ordinary ``status: error`` payload: the push verbs already return
those, and the caller treats any non-success as "the push did not happen".
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from file_ops import get_executor_path
from toon_parser import parse_toon

#: The phase whose step records carry gate heads.
FINALIZE_PHASE = '6-finalize'

#: The step whose ``head_at_completion`` anchors the push barrier.
PRE_PUSH_GATE_STEP = 'pre-push-quality-gate'

#: Refusal code for a HEAD the recorded gate never saw.
HEAD_NOT_GATED = 'head_not_validated_by_gate'

#: Refusal code for a push attempted while the PR is armed for an automatic merge.
ARMED_MERGE_REFUSAL = 'push_while_merge_armed'

_MANAGE_STATUS_NOTATION = 'plan-marshall:manage-status:manage-status'
_CI_NOTATION = 'plan-marshall:tools-integration-ci:ci'


def read_plan_status(plan_id: str) -> dict[str, Any] | None:
    """Return the plan's ``status.json`` payload, or ``None`` when it cannot be read.

    Goes through the executor (``manage-status read``), so the plan-context
    resolution is the skill's own — a plan that moved into its worktree is still
    found. ``None`` is the declared unknown: no record, nothing to compare.
    """
    try:
        executor = get_executor_path()
    except RuntimeError:
        # ``get_executor_path`` RAISES when no plan root resolves; it does not return
        # ``None``. An unresolvable executor is the declared unknown here — no status
        # to read, nothing to compare — and must not escape the push verb.
        return None
    if executor is None:
        return None
    try:
        completed = subprocess.run(
            [sys.executable, str(executor), _MANAGE_STATUS_NOTATION, 'read', '--plan-id', plan_id],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if not (completed.stdout or '').strip():
        return None
    try:
        parsed = parse_toon(completed.stdout)
    except Exception:
        return None
    if parsed.get('status') != 'success':
        return None
    plan = parsed.get('plan')
    return plan if isinstance(plan, dict) else None


def recorded_gate_head(plan_id: str, *, status: dict[str, Any] | None = None) -> str | None:
    """Return the HEAD the pre-push gate recorded for ``plan_id``, or ``None``."""
    plan = read_plan_status(plan_id) if status is None else status
    if not isinstance(plan, dict):
        return None
    metadata = plan.get('metadata')
    if not isinstance(metadata, dict):
        return None
    steps = metadata.get('phase_steps')
    if not isinstance(steps, dict):
        return None
    phase_steps = steps.get(FINALIZE_PHASE)
    if not isinstance(phase_steps, dict):
        return None
    record = phase_steps.get(PRE_PUSH_GATE_STEP)
    if not isinstance(record, dict):
        return None
    head = record.get('head_at_completion')
    return str(head).strip() if head else None


def head_gate_refusal(plan_id: str, head: str, *, status: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Refuse a push of ``head`` when the recorded gate head is a different commit.

    ``head`` is the commit the push would ship (the push verbs read it from the
    worktree). An empty ``plan_id`` or ``head``, an unreadable status and a plan with
    no gate record all answer ``None`` — see the module docstring for why the absent
    case is a pass rather than a refusal.
    """
    if not plan_id or not head:
        return None
    recorded = recorded_gate_head(plan_id, status=status)
    if not recorded or recorded == head.strip():
        return None
    return {
        'status': 'error',
        'error': HEAD_NOT_GATED,
        'plan_id': plan_id,
        'step': PRE_PUSH_GATE_STEP,
        'recorded_head': recorded,
        'head': head.strip(),
        'message': (
            f'The HEAD being pushed ({head.strip()}) is not the HEAD the '
            f'{PRE_PUSH_GATE_STEP} validated ({recorded}). Run the gate on the '
            'current tree and push again — a fix commit after the gate is an '
            'ungated push.'
        ),
    }


__all__ = [
    'ARMED_MERGE_REFUSAL',
    'FINALIZE_PHASE',
    'HEAD_NOT_GATED',
    'PRE_PUSH_GATE_STEP',
    'armed_merge_refusal',
    'evaluate_merge_arm_state',
    'head_gate_refusal',
    'read_merge_arm_state',
    'read_plan_status',
    'recorded_gate_head',
]


def _run_ci_verb(ci_args: list[str]) -> dict[str, Any]:
    """Run ``ci`` through the executor and return its parsed TOON (empty on failure)."""
    try:
        executor = get_executor_path()
    except RuntimeError:
        return {}
    if executor is None:
        return {}
    try:
        completed = subprocess.run(
            [sys.executable, str(executor), _CI_NOTATION, *ci_args],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if not (completed.stdout or '').strip():
        return {}
    try:
        parsed = parse_toon(completed.stdout)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_merge_arm_state(branch: str) -> dict[str, Any]:
    """Read the PR's merge-queue / auto-merge state for ``branch``, or an empty dict.

    Two provider reads through the executor: ``pr view --head {branch}`` names the
    PR, and ``pr queue-state`` reports ``in_queue`` and ``auto_merge_armed``. An
    empty dict is the declared unknown — no PR, an unreadable PR, a provider
    without these verbs — never "not armed" spelled as an absent field.
    """
    if not branch:
        return {}
    view = _run_ci_verb(['pr', 'view', '--head', branch])
    if view.get('status') != 'success' or str(view.get('state') or '') != 'open':
        return {}
    number = view.get('pr_number')
    if number in (None, '', 'unknown'):
        return {}
    queue_state = _run_ci_verb(['pr', 'queue-state', '--pr-number', str(number)])
    if queue_state.get('status') != 'success':
        return {}
    return {'pr_number': str(number), **queue_state}


def evaluate_merge_arm_state(state: dict[str, Any]) -> tuple[str, str] | None:
    """Return ``(condition, detail)`` when ``state`` shows an armed merge, else ``None``.

    Only a POSITIVE observation refuses: ``in_queue is True`` or
    ``auto_merge_armed is True``. ``False`` means the read said no, and
    ``indeterminate`` means the read could not answer — neither is evidence of an
    armed merge, so neither blocks a push (the gate-head binding still applies).
    """
    if state.get('in_queue') is True:
        return ('in_queue', f'the PR is in the merge queue (position {state.get("queue_position")})')
    if state.get('auto_merge_armed') is True:
        return ('auto_merge_armed', 'auto-merge is armed on the PR')
    return None


def armed_merge_refusal(branch: str) -> dict[str, Any] | None:
    """Refuse a push while the PR is armed for an automatic merge.

    An armed auto-merge or merge-queue entry is bound to the HEAD it was armed
    for: a push of a new HEAD must not slip past it. The push verb therefore
    REFUSES while the arm holds, rather than pushing and leaving a stale arm
    behind. The cheap alternative — disarming on push — would be a side effect
    the caller never asked for and could not see in the result.
    """
    state = read_merge_arm_state(branch)
    verdict = evaluate_merge_arm_state(state)
    if verdict is None:
        return None
    condition, detail = verdict
    pr_number = state.get('pr_number')
    return {
        'status': 'error',
        'error': ARMED_MERGE_REFUSAL,
        'condition': condition,
        'pr_number': pr_number,
        'branch': branch,
        'pushed': False,
        'message': (
            f'The PR (#{pr_number}) is armed for an automatic merge: {detail}. The arm is bound '
            'to the HEAD it was armed for, so a push of a new HEAD is refused. Disable auto-merge '
            'or dequeue the PR, push, then arm it again on the new HEAD.'
        ),
    }
