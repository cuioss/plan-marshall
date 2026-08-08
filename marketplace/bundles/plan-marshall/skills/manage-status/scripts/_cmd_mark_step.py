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
``--force``.

The SHA is also the DELTA ANCHOR a later review round scopes itself against
(``self_review surface --since-ref``), so on a ``done`` outcome its absence is
refused rather than tolerated: when the step's authoritative doc declares
``head_dependent: true`` and no ``--head-at-completion`` was supplied, the
handler returns ``error: missing_head_at_completion`` and writes NOTHING. The
declaration is read through the registry's own discovery path, so no second
frontmatter parser exists to drift from it. When that derivation cannot run at
all, the record IS written and carries a ``warning`` field naming the
unresolved derivation — an unresolvable derivation must not manufacture an
unsubstantiated refusal, but must not pass silently either. The obligation is
declared in ``extension-api/standards/ext-point-finalize-step.md``.

The ``--loop-back-target`` flag classifies loop-back outcomes
into the two granularity tiers — ``5-execute`` for fix-task-required
dispositions (full phase rollback) and ``6-finalize`` for inline-fixable
dispositions (replay the same finalize step from the resumable re-entry
check). The flag is REQUIRED on every ``loop_back`` outcome and FORBIDDEN
on every other outcome; the validation has no backwards-compat fallback
(breaking-change contract per the finalize-loopback plan, Deliverable 3).

The repeatable ``--fact KEY=VALUE`` flag records structured per-step facts.
The accumulated pairs are parsed into a ``dict[str, str]`` and persisted under
an optional ``facts`` key, following the same omit-when-absent convention as
``head_at_completion`` / ``loop_back_target``: a caller that supplies no
``--fact`` writes the byte-identical historical record shape. The keys a step
may record are declared by its ``records_facts`` frontmatter obligation (see
``extension-api/standards/ext-point-finalize-step.md``); this handler does not
validate keys against that declaration — it only parses, rejecting a malformed
token (no ``=``, or an empty key) with ``error: invalid_fact`` naming the
offending token. ``facts`` participates in the idempotency comparison and in
the ``previous_*`` echo fields, so a re-call that changes only the facts is
reported as ``changed: true`` rather than silently swallowed.
"""

import argparse
from pathlib import Path
from typing import Any

from _status_core import require_status, write_status
from _step_key_canonical import canonicalize_step_key

VALID_OUTCOMES = ('done', 'skipped', 'loop_back', 'failed')
VALID_LOOP_BACK_TARGETS = ('5-execute', '6-finalize')

#: The ext-point whose implementors declare the ``head_dependent`` fact.
_FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The frontmatter key that IS the head-dependence declaration.
_HEAD_DEPENDENT_KEY = 'head_dependent'


def _derive_head_dependence(step: str) -> tuple[bool, str | None]:
    """Derive whether ``step`` declares ``head_dependent: true`` in its own doc.

    Reuses the registry's OWN discovery path — ``find_implementors`` for the
    population and ``extension_discovery._read_frontmatter_fields`` for the fact —
    so no second frontmatter parser exists to drift from the one the dispatcher
    and the derivation guard already read. Both sides of the comparison are run
    through :func:`canonicalize_step_key`, because discovery names a built-in step
    ``default:{name}`` while the caller writes the bare canonical key.

    Returns ``(is_head_dependent, unresolved_reason)``:

    * ``(True, None)`` / ``(False, None)`` — the derivation RESOLVED. A step that
      is simply absent from the finalize-step population resolves to ``False``
      rather than "unresolved": ``mark-step-done`` records steps for every phase,
      so a phase-5 step legitimately matches no finalize-step implementor and must
      not raise a warning on every call.
    * ``(False, reason)`` — the derivation MACHINERY could not run at all (import
      failure, discovery error, or an empty implementor population). The caller
      writes the record and carries the reason as a ``warning``, following this
      project's diagnosable-WARNING idiom: an unresolvable derivation must not
      manufacture an unsubstantiated refusal, but it must not pass silently
      either.
    """
    try:
        import extension_discovery
        from extension_discovery import find_implementors
    except ImportError as exc:
        return False, f'extension_discovery is not importable ({exc})'

    try:
        records = find_implementors(_FINALIZE_STEP_EXT_POINT)
    except Exception as exc:  # noqa: BLE001 - any discovery failure is diagnosable, not fatal
        return False, f'find_implementors({_FINALIZE_STEP_EXT_POINT!r}) failed ({exc})'

    if not records:
        return False, (
            f'find_implementors({_FINALIZE_STEP_EXT_POINT!r}) discovered no finalize-step '
            'implementors, so head-dependence could not be derived for any step'
        )

    for record in records:
        if canonicalize_step_key(str(record.get('name', ''))) != step:
            continue
        fields = extension_discovery._read_frontmatter_fields(
            Path(str(record.get('path', ''))), (_HEAD_DEPENDENT_KEY,)
        )
        return bool(fields.get(_HEAD_DEPENDENT_KEY, False)), None

    return False, None


def _parse_facts(raw: list[str] | None) -> tuple[dict[str, str] | None, str | None]:
    """Parse repeated ``KEY=VALUE`` tokens into a dict.

    Returns ``(facts, None)`` on success — ``facts`` is ``None`` when the caller
    supplied no ``--fact`` at all, so the persisted record keeps its historical
    shape. Returns ``(None, offending_token)`` when a token is malformed: it
    carries no ``=`` separator, or its key is empty. The value half MAY contain
    ``=`` (split is on the FIRST separator only) and MAY be empty — only the key
    is constrained. A later token for the same key overwrites the earlier one.
    """
    if not raw:
        return None, None
    facts: dict[str, str] = {}
    for token in raw:
        key, sep, value = token.partition('=')
        if not sep or not key:
            return None, token
        facts[key] = value
    return facts, None


def _with_warning(result: dict[str, Any], warning: str | None) -> dict[str, Any]:
    """Attach a diagnosable ``warning`` to a success record, when one was raised.

    Omitted entirely when no warning applies, so the ordinary record keeps its
    historical shape — the same omit-when-absent convention ``head_at_completion``
    and ``loop_back_target`` follow.
    """
    if warning:
        result['warning'] = warning
    return result


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
    # Canonicalize the step key at the mark-step-done boundary via the shared
    # resolver so the recorded key always equals the bare manifest key the
    # dispatcher reads back — no more step_record_mismatched_key orphans.
    step = canonicalize_step_key(args.step) if args.step else args.step
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

    facts, bad_fact_token = _parse_facts(getattr(args, 'fact', None))
    if bad_fact_token is not None:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_fact',
            'phase': phase,
            'step': step,
            'offending_token': bad_fact_token,
            'message': (
                f'--fact expects KEY=VALUE with a non-empty KEY, got: {bad_fact_token!r}'
            ),
        }

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

    # Head-anchor validation: a head-dependent step's terminal ``done`` record is
    # what the NEXT round scopes its delta against (self_review --since-ref), and
    # what the dispatcher's re-entry check compares the live HEAD to. A ``done``
    # with no SHA therefore records a verdict nobody can locate in history — it
    # reads as green for a diff it may never have examined. The absence is refused
    # rather than tolerated; the obligation is declared in
    # ``extension-api/standards/ext-point-finalize-step.md``.
    head_derivation_warning: str | None = None
    if outcome == 'done':
        is_head_dependent, head_derivation_warning = _derive_head_dependence(step)
        if is_head_dependent and not head_at_completion:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'missing_head_at_completion',
                'phase': phase,
                'step': step,
                'message': (
                    f'Step {step!r} declares head_dependent: true, so --head-at-completion '
                    'is required when --outcome=done. Nothing was written. Resolve the '
                    'worktree HEAD immediately before this call and pass it as '
                    '--head-at-completion {sha}. See the ext-point-finalize-step.md '
                    '"head_dependent" field contract for the fail-closed obligation.'
                ),
            }

    metadata: dict[str, Any] = status.setdefault('metadata', {})
    phase_steps: dict[str, Any] = metadata.setdefault('phase_steps', {})
    phase_entry: dict[str, Any] = phase_steps.setdefault(phase, {})

    # Prefer an exact match under the canonical key. When it misses, fall back to
    # a canonicalized-match scan so a stale legacy (pre-migration) key such as
    # ``default:push`` is still located when the caller writes the canonical
    # ``push``. Tracking ``existing_key`` lets the conflict check fire against the
    # true existing outcome AND lets the write below pop the stale key so a
    # duplicate legacy-vs-canonical pair never survives a re-run.
    existing = phase_entry.get(step)
    existing_key: str | None = step if existing is not None else None
    if existing is None:
        for stored_key, stored_entry in phase_entry.items():
            if canonicalize_step_key(stored_key) == step:
                existing = stored_entry
                existing_key = stored_key
                break

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

    new_entry = _build_entry(outcome, display_detail, head_at_completion, loop_back_target, facts)

    if isinstance(existing, dict):
        existing_outcome = existing.get('outcome')
        existing_detail = existing.get('display_detail')
        existing_head = existing.get('head_at_completion')
        existing_loop_back_target = existing.get('loop_back_target')
        existing_facts = existing.get('facts')
        if (
            existing_outcome == outcome
            and existing_detail == display_detail
            and existing_head == head_at_completion
            and existing_loop_back_target == loop_back_target
            and existing_facts == facts
        ):
            return _with_warning(
                {
                    'status': 'success',
                    'plan_id': args.plan_id,
                    'phase': phase,
                    'step': step,
                    'outcome': outcome,
                    'display_detail': display_detail,
                    'head_at_completion': head_at_completion,
                    'loop_back_target': loop_back_target,
                    'facts': facts,
                    'changed': False,
                },
                head_derivation_warning,
            )
        if existing_outcome == outcome and (
            existing_detail != display_detail
            or existing_head != head_at_completion
            or existing_loop_back_target != loop_back_target
            or existing_facts != facts
        ):
            if existing_key is not None and existing_key != step:
                phase_entry.pop(existing_key, None)
            phase_entry[step] = new_entry
            write_status(args.plan_id, status)
            return _with_warning(
                {
                    'status': 'success',
                    'plan_id': args.plan_id,
                    'phase': phase,
                    'step': step,
                    'outcome': outcome,
                    'display_detail': display_detail,
                    'head_at_completion': head_at_completion,
                    'loop_back_target': loop_back_target,
                    'facts': facts,
                    'changed': True,
                    'previous_outcome': existing_outcome,
                    'previous_display_detail': existing_detail,
                    'previous_head_at_completion': existing_head,
                    'previous_loop_back_target': existing_loop_back_target,
                    'previous_facts': existing_facts,
                },
                head_derivation_warning,
            )
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
    previous_facts = None
    if isinstance(existing, dict):
        previous_outcome = existing.get('outcome')
        previous_detail = existing.get('display_detail')
        previous_head = existing.get('head_at_completion')
        previous_loop_back_target = existing.get('loop_back_target')
        previous_facts = existing.get('facts')

    if existing_key is not None and existing_key != step:
        phase_entry.pop(existing_key, None)
    phase_entry[step] = new_entry
    write_status(args.plan_id, status)

    return _with_warning(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'phase': phase,
            'step': step,
            'outcome': outcome,
            'display_detail': display_detail,
            'head_at_completion': head_at_completion,
            'loop_back_target': loop_back_target,
            'facts': facts,
            'changed': True,
            'previous_outcome': previous_outcome,
            'previous_display_detail': previous_detail,
            'previous_head_at_completion': previous_head,
            'previous_loop_back_target': previous_loop_back_target,
            'previous_facts': previous_facts,
        },
        head_derivation_warning,
    )


def _build_entry(
    outcome: str,
    display_detail: str | None,
    head_at_completion: str | None,
    loop_back_target: str | None,
    facts: dict[str, str] | None,
) -> dict[str, Any]:
    """Build the phase_entry[step] dict, omitting optional keys when None.

    Legacy compatibility: callers that omit ``--head-at-completion`` produce
    the historical two-key shape ``{"outcome": ..., "display_detail": ...}``.
    Only when a SHA is supplied does the third key appear in the persisted
    record. Same shape applies to ``loop_back_target`` — it appears only on
    ``loop_back`` outcome rows (the validation above guarantees it is always
    present when the outcome is ``loop_back`` and never present otherwise) —
    and to ``facts``, which appears only when the caller supplied at least one
    ``--fact KEY=VALUE``.
    """
    entry: dict[str, Any] = {'outcome': outcome, 'display_detail': display_detail}
    if head_at_completion is not None:
        entry['head_at_completion'] = head_at_completion
    if loop_back_target is not None:
        entry['loop_back_target'] = loop_back_target
    if facts:
        entry['facts'] = facts
    return entry
