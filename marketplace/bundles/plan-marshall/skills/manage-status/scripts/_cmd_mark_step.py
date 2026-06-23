#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
mark-step-done command handler for manage-status.

Persists phase step completion state into status.metadata.phase_steps so that
phase skills can record which intra-phase steps have finished. Outcomes are
``done``, ``skipped``, ``failed``, or ``loop_back``. The ``failed`` value
records that the step aborted with an error (e.g., a graceful timeout
degradation in the phase-6-finalize dispatcher); the dispatcher will retry
the step on next phase entry rather than treating it as terminal. The
``loop_back`` value records that the step deliberately re-fired (loop-back
iteration recorded; dispatcher will re-fire on next phase-6-finalize entry) and signals
the dispatcher to treat the step as a fresh dispatch on the next phase entry
rather than skipping it. The operation is idempotent when outcome,
display_detail, and head_at_completion all match and returns a ``conflict``
error when a step already has a different outcome unless ``--force`` is
supplied. An optional ``--display-detail`` one-line string is persisted
alongside the outcome so downstream renderers (e.g., phase-6-finalize
vertical-steps block) can surface user-facing step summaries. An optional
``--head-at-completion`` SHA is persisted alongside the outcome so resumable
phase dispatchers (e.g., phase-6-finalize Step 3 for ``pre-push-quality-gate``)
can detect when the worktree HEAD has advanced past the SHA at which the
previous run completed and re-fire the gate accordingly. The SHA is treated as
informational metadata: re-call with same outcome+display_detail but a
different head_at_completion is a "changed" overwrite without requiring
``--force``. The ``--loop-back-target`` flag classifies loop-back outcomes
into the two granularity tiers — ``5-execute`` for fix-task-required
dispositions (full phase rollback) and ``6-finalize`` for inline-fixable
dispositions (replay the same finalize step from the resumable re-entry
check). The flag is REQUIRED on every ``loop_back`` outcome and FORBIDDEN
on every other outcome; the validation has no backwards-compat fallback
(breaking-change contract per the finalize-loopback plan, Deliverable 3).

A dirty-worktree guard refuses ``--outcome done`` for steps in
``MAY_MUTATE_WORKTREE_STEPS`` (``automated-review``, ``sonar-roundtrip``,
``finalize-step-simplify``) when ``git status --porcelain`` reports a dirty
tree: marking such a step done while uncommitted changes sit in the worktree
would let the dispatcher advance past commit-push and silently drop the
mutation. The guard returns ``error: dirty_worktree_done_refused`` and
instructs the caller to re-issue the outcome as ``loop_back`` (inline replay
via target ``6-finalize`` or fix-task rollback via target ``5-execute``).
"""

import argparse
import subprocess
from typing import Any

from _status_core import require_status, write_status

VALID_OUTCOMES = ('done', 'skipped', 'loop_back', 'failed')
VALID_LOOP_BACK_TARGETS = ('5-execute', '6-finalize')

# Steps whose finalize-phase bodies may legitimately mutate the worktree
# (re-running formatters, applying review fixes, regenerating artifacts).
# When such a step reports ``--outcome done`` the worktree MUST be clean —
# otherwise the dispatcher would advance past commit-push while uncommitted
# changes sit in the tree, silently dropping the mutation. The dirty-tree
# guard below refuses the ``done`` transition for these steps and instructs
# the caller to re-issue the outcome as a loop_back so the change is either
# replayed inline (target 6-finalize) or rolled into a fix task (target
# 5-execute).
MAY_MUTATE_WORKTREE_STEPS = frozenset(
    {'automated-review', 'sonar-roundtrip', 'finalize-step-simplify'}
)


def _resolve_worktree_path(status: dict[Any, Any]) -> str:
    """Resolve the worktree path for the dirty-tree guard (tri-state).

    Returns ``'.'`` (the main checkout) when ``metadata.use_worktree`` is
    false or ``metadata.worktree_path`` is empty/absent; otherwise returns the
    persisted ``worktree_path``.
    """
    metadata = status.get('metadata') or {}
    if not metadata.get('use_worktree'):
        return '.'
    worktree_path = metadata.get('worktree_path') or ''
    return worktree_path if worktree_path else '.'


def _worktree_is_dirty(worktree_path: str) -> bool:
    """Return True when ``git -C {worktree_path} status --porcelain`` is non-empty."""
    completed = subprocess.run(
        ['git', '-C', worktree_path, 'status', '--porcelain'],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(completed.stdout.strip())


def cmd_mark_step_done(args: argparse.Namespace) -> dict | None:
    """Mark a phase step with an outcome inside status.metadata.phase_steps."""
    status = require_status(args)
    if status is None:
        return None

    outcome = args.outcome
    if outcome not in VALID_OUTCOMES:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_outcome',
            'message': f'Outcome must be one of {list(VALID_OUTCOMES)}, got: {outcome}',
        }

    phase = args.phase
    step = args.step
    if not phase or not step:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--phase and --step are required and must be non-empty',
        }

    display_detail = getattr(args, 'display_detail', None)
    head_at_completion = getattr(args, 'head_at_completion', None)
    loop_back_target = getattr(args, 'loop_back_target', None)

    # Loop-back target validation: required for loop_back outcomes, forbidden otherwise.
    # This is a breaking-change validation per Deliverable 3 of the finalize-loopback
    # plan — no backwards-compat fallback. Loop-back-emitting steps MUST classify
    # the disposition as inline-fixable (target=6-finalize) or fix-task-required
    # (target=5-execute) before persisting the outcome.
    if outcome == 'loop_back':
        if loop_back_target is None:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'missing_loop_back_target',
                'phase': phase,
                'step': step,
                'message': (
                    "--loop-back-target is required when --outcome=loop_back. "
                    f"Must be one of {list(VALID_LOOP_BACK_TARGETS)}. See the "
                    'phase-6-finalize "Loop-back Target Contract" subsection for '
                    'the granularity invariant.'
                ),
            }
        if loop_back_target not in VALID_LOOP_BACK_TARGETS:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_loop_back_target',
                'phase': phase,
                'step': step,
                'message': (
                    f'--loop-back-target must be one of '
                    f'{list(VALID_LOOP_BACK_TARGETS)}, got: {loop_back_target}'
                ),
            }
    elif loop_back_target is not None:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'unexpected_loop_back_target',
            'phase': phase,
            'step': step,
            'message': (
                f'--loop-back-target is only valid when --outcome=loop_back '
                f'(got --outcome={outcome}, --loop-back-target={loop_back_target})'
            ),
        }

    # Dirty-worktree refusal: a may-mutate-worktree step reporting ``done`` MUST
    # leave the worktree clean. When the tree is dirty the mutation has not been
    # committed and advancing past commit-push would silently drop it. Refuse the
    # transition and instruct the caller to re-issue as a loop_back. Fires only
    # for ``outcome == 'done'`` AND ``step in MAY_MUTATE_WORKTREE_STEPS``; all other
    # outcomes and steps fall through unchanged.
    if outcome == 'done' and step in MAY_MUTATE_WORKTREE_STEPS:
        worktree_path = _resolve_worktree_path(status)
        if _worktree_is_dirty(worktree_path):
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'dirty_worktree_done_refused',
                'phase': phase,
                'step': step,
                'dirty': True,
                'message': (
                    f'Step {step!r} in phase {phase!r} may mutate the worktree, but '
                    'the working tree is dirty — refusing to mark it done. Re-issue '
                    'with --outcome loop_back --loop-back-target 6-finalize to replay '
                    'the step inline (commit-push the change), or --outcome loop_back '
                    '--loop-back-target 5-execute to roll the change into a fix task.'
                ),
            }

    metadata: dict[str, Any] = status.setdefault('metadata', {})
    phase_steps: dict[str, Any] = metadata.setdefault('phase_steps', {})
    phase_entry: dict[str, Any] = phase_steps.setdefault(phase, {})

    existing = phase_entry.get(step)

    if isinstance(existing, str) and not args.force:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'legacy_string_entry',
            'phase': phase,
            'step': step,
            'existing_outcome': existing,
            'requested_outcome': outcome,
            'message': (
                f'Step {step!r} in phase {phase!r} has legacy bare-string storage '
                f'({existing!r}); re-run with --force to migrate the entry to the '
                'dict shape {"outcome": ..., "display_detail": ...}.'
            ),
        }

    new_entry = _build_entry(outcome, display_detail, head_at_completion, loop_back_target)

    if isinstance(existing, dict):
        existing_outcome = existing.get('outcome')
        existing_detail = existing.get('display_detail')
        existing_head = existing.get('head_at_completion')
        existing_loop_back_target = existing.get('loop_back_target')
        if (
            existing_outcome == outcome
            and existing_detail == display_detail
            and existing_head == head_at_completion
            and existing_loop_back_target == loop_back_target
        ):
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'phase': phase,
                'step': step,
                'outcome': outcome,
                'display_detail': display_detail,
                'head_at_completion': head_at_completion,
                'loop_back_target': loop_back_target,
                'changed': False,
            }
        if existing_outcome == outcome and (
            existing_detail != display_detail
            or existing_head != head_at_completion
            or existing_loop_back_target != loop_back_target
        ):
            phase_entry[step] = new_entry
            write_status(args.plan_id, status)
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'phase': phase,
                'step': step,
                'outcome': outcome,
                'display_detail': display_detail,
                'head_at_completion': head_at_completion,
                'loop_back_target': loop_back_target,
                'changed': True,
                'previous_outcome': existing_outcome,
                'previous_display_detail': existing_detail,
                'previous_head_at_completion': existing_head,
                'previous_loop_back_target': existing_loop_back_target,
            }
        if existing_outcome != outcome and not args.force:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'conflict',
                'phase': phase,
                'step': step,
                'existing_outcome': existing_outcome,
                'requested_outcome': outcome,
                'message': (
                    f'Step {step!r} in phase {phase!r} already marked as '
                    f'{existing_outcome!r}; use --force to overwrite with {outcome!r}'
                ),
            }

    previous_outcome = None
    previous_detail = None
    previous_head = None
    previous_loop_back_target = None
    if isinstance(existing, dict):
        previous_outcome = existing.get('outcome')
        previous_detail = existing.get('display_detail')
        previous_head = existing.get('head_at_completion')
        previous_loop_back_target = existing.get('loop_back_target')

    phase_entry[step] = new_entry
    write_status(args.plan_id, status)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': phase,
        'step': step,
        'outcome': outcome,
        'display_detail': display_detail,
        'head_at_completion': head_at_completion,
        'loop_back_target': loop_back_target,
        'changed': True,
        'previous_outcome': previous_outcome,
        'previous_display_detail': previous_detail,
        'previous_head_at_completion': previous_head,
        'previous_loop_back_target': previous_loop_back_target,
    }


def _build_entry(
    outcome: str,
    display_detail: str | None,
    head_at_completion: str | None,
    loop_back_target: str | None,
) -> dict[str, Any]:
    """Build the phase_entry[step] dict, omitting optional keys when None.

    Legacy compatibility: callers that omit ``--head-at-completion`` produce
    the historical two-key shape ``{"outcome": ..., "display_detail": ...}``.
    Only when a SHA is supplied does the third key appear in the persisted
    record. Same shape applies to ``loop_back_target`` — it appears only on
    ``loop_back`` outcome rows (the validation above guarantees it is always
    present when the outcome is ``loop_back`` and never present otherwise).
    """
    entry: dict[str, Any] = {'outcome': outcome, 'display_detail': display_detail}
    if head_at_completion is not None:
        entry['head_at_completion'] = head_at_completion
    if loop_back_target is not None:
        entry['loop_back_target'] = loop_back_target
    return entry
