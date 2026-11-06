#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Query command handlers for manage-tasks.py.

Contains: list, read, next, tasks-by-domain, tasks-by-profile, next-tasks,
loop-exit-guard subcommands.
"""

from _tasks_core import (
    calculate_progress,
    find_task_file,
    get_all_tasks,
    get_deliverable_context,
    get_plan_dir,
    get_tasks_dir,
    output_error,
    parse_task_file,
)
from toon_parser import ToonParseError, parse_toon

# ---------------------------------------------------------------------------
# B7 no-progress reclassification vocabulary
# ---------------------------------------------------------------------------
# The predicate, its threshold and its classification live HERE, in the script
# the orchestrator calls — never as a second statement in prose.
# ``plan-marshall/workflow/execution.md`` § "B7 — voluntary_checkpoint
# no-progress reclassification" states the rule once and cites this module;
# ``phase-5-execute/SKILL.md`` cites it too instead of restating the predicate.
B7_PROVISIONAL_CAUSE = 'voluntary_checkpoint'
B7_NO_PROGRESS_TOKEN_THRESHOLD = 50000
NO_PROGRESS_CAUSE = 'error'
VERIFICATION_HANDBACK_CAUSE = 'verification_handback'

#: The named error a mode entered without both predicate measurements returns.
#: ``--consumed-tokens`` or ``--completed-tasks-delta`` absent is NOT a zero:
#: a delta nobody supplied cannot be evidence that the loop made no progress.
NO_PROGRESS_NOT_DECIDABLE = 'no_progress_not_decidable'

#: The plan-local execution manifest, whose ``phase_5.verification_steps`` is
#: the composed list a hand-back's step ids are checked against. Mirrors
#: ``MANIFEST_FILENAME`` in ``manage-execution-manifest/scripts/_manifest_core.py``;
#: that module is not on this script's import path, and the file name is the
#: stable part of the cross-skill contract.
MANIFEST_FILENAME = 'execution.toon'


def _build_done_set(all_tasks: list) -> set[str]:
    """Build set of done task identifiers for dependency checking.

    Includes both zero-padded (TASK-001) and non-padded (TASK-1) formats
    to handle depends_on values stored in either format.
    """
    done = set()
    for _, t in all_tasks:
        if t.get('status') == 'done':
            n = t['number']
            done.add(f'TASK-{n:03d}')
            done.add(f'TASK-{n}')
    return done


def cmd_list(args) -> dict:
    """Handle 'list' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = _build_done_set(all_tasks)

    # Filter by deliverable if specified
    if args.deliverable:
        all_tasks = [(p, t) for p, t in all_tasks if args.deliverable == t.get('deliverable', 0)]

    # Filter by ready (dependencies satisfied) if specified
    if args.ready:
        all_tasks = [(p, t) for p, t in all_tasks if all(dep in done_tasks for dep in t.get('depends_on', []))]

    # Filter by domain if specified
    if getattr(args, 'domain', None):
        all_tasks = [(p, t) for p, t in all_tasks if t.get('domain') == args.domain]

    # Filter by profile if specified
    if getattr(args, 'profile', None):
        all_tasks = [(p, t) for p, t in all_tasks if t.get('profile') == args.profile]

    # Get filtered list for status filtering
    filtered_tasks = all_tasks
    if args.status and args.status != 'all':
        filtered_tasks = [(p, t) for p, t in all_tasks if t.get('status') == args.status]

    # Compute counts from filtered list
    pending = sum(1 for _, t in all_tasks if t.get('status') == 'pending')
    in_progress = sum(1 for _, t in all_tasks if t.get('status') == 'in_progress')
    done_count = sum(1 for _, t in all_tasks if t.get('status') == 'done')
    failed_count = sum(1 for _, t in all_tasks if t.get('status') == 'failed')
    blocked = sum(1 for _, t in all_tasks if t.get('status') == 'blocked')
    infeasible = sum(1 for _, t in all_tasks if t.get('status') == 'infeasible')

    # Build table data
    table = []
    for _path, task in filtered_tasks:
        completed, total = calculate_progress(task)
        deliverable = task.get('deliverable', 0)
        table.append(
            {
                'number': task['number'],
                'title': task['title'],
                'domain': task.get('domain'),
                'profile': task.get('profile'),
                'deliverable': deliverable,
                'status': task['status'],
                'progress': f'{completed}/{total}',
            }
        )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'counts': {
            'total': len(all_tasks),
            'pending': pending,
            'in_progress': in_progress,
            'done': done_count,
            'failed': failed_count,
            'blocked': blocked,
            'infeasible': infeasible,
        },
        'tasks_table': table,
    }


def cmd_read(args) -> dict:
    """Handle 'read' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task_number)
    if not filepath:
        return output_error(f'Task TASK-{args.task_number} not found')

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': filepath.name,
        'task': {
            'number': task['number'],
            'title': task['title'],
            'domain': task.get('domain'),
            'profile': task.get('profile'),
            'skills': task.get('skills', []),
            'origin': task.get('origin', 'plan'),
            'deliverable': task.get('deliverable', 0),
            'depends_on': task.get('depends_on', []),
            'status': task['status'],
            'current_step': task.get('current_step', 1),
            'description': task.get('description', ''),
            'steps': task.get('steps', []),
            'verification': task.get('verification', {}),
            'envelope_id': task.get('envelope_id'),
        },
    }


def cmd_exists(args) -> dict:
    """Handle 'exists' subcommand.

    Boolean presence probe: returns ``status: success`` with
    ``exists: true|false`` for any task number, never erroring on absence.
    Reuses the same task-file resolver as ``cmd_read`` (``find_task_file``)
    but maps the ``None`` outcome to ``exists: false`` instead of an
    error so callers can probe without polluting ``script-execution.log``
    with recoverable not-found rows.
    """
    task_dir = get_tasks_dir(args.plan_id)
    filepath = find_task_file(task_dir, args.task_number)
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'task': args.task_number,
        'exists': filepath is not None,
    }


def cmd_next(args) -> dict:
    """Handle 'next' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = _build_done_set(all_tasks)

    filtered_tasks = all_tasks

    total_tasks = len(filtered_tasks)
    completed_tasks = sum(1 for _, t in filtered_tasks if t.get('status') == 'done')
    in_progress_count = sum(1 for _, t in filtered_tasks if t.get('status') == 'in_progress')

    # Helper to check if dependencies are satisfied
    def deps_satisfied(task):
        if getattr(args, 'ignore_deps', False):
            return True
        deps = task.get('depends_on', [])
        return all(dep in done_tasks for dep in deps)

    # Find first in_progress or pending task with satisfied dependencies
    next_task = None
    blocked_tasks = []

    # First, look for in_progress tasks. A verification-owed task (see
    # _cmd_step.py, module-testing close rule) has every step terminal and no
    # actionable step — its orchestrator-tier build has not reported yet, so
    # selecting it would return a null next_step and read as queue drift.
    # Skip owed tasks that have nothing actionable; an owed task that gained
    # a pending step (via add-step) IS selectable again. An unmarked
    # all-terminal in_progress task is still selected, preserving the
    # pending-task drift signal for genuinely misclassified records.
    for _path, task in filtered_tasks:
        if task.get('status') == 'in_progress':
            if task.get('verification_owed') is True and not any(
                s.get('status') in ('pending', 'in_progress') for s in task.get('steps', [])
            ):
                continue
            next_task = task
            break

    # If no in_progress, find pending tasks with satisfied deps. A runnable
    # fix task (origin ``fix``) is returned ahead of the pending deliverable
    # tasks whose verification it blocks: triage allocates the fix after
    # packing, so number order alone would run it behind the deliverables it
    # gates. Number order is preserved within each class.
    if not next_task:
        runnable = []
        for _path, task in filtered_tasks:
            if task.get('status') == 'pending':
                if deps_satisfied(task):
                    runnable.append(task)
                else:
                    waiting_for = [dep for dep in task.get('depends_on', []) if dep not in done_tasks]
                    blocked_tasks.append(
                        {'number': task['number'], 'title': task['title'], 'waiting_for': ', '.join(waiting_for)}
                    )
        runnable.sort(key=lambda t: (0 if t.get('origin', 'plan') == 'fix' else 1, t['number']))
        if runnable:
            next_task = runnable[0]

    if not next_task:
        if blocked_tasks:
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'next': None,
                'blocked_tasks': blocked_tasks,
                'context': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'in_progress': in_progress_count,
                    'blocked_by_deps': len(blocked_tasks),
                    'message': 'Waiting for in-progress tasks to complete',
                },
            }
        else:
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'next': None,
                'context': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'message': 'All tasks completed',
                },
            }

    # Find next pending step in this task
    steps = next_task.get('steps', [])
    next_step = None
    completed_steps = 0

    for step in steps:
        if step['status'] in ('done', 'skipped'):
            completed_steps += 1
        elif step['status'] == 'in_progress':
            next_step = step
        elif step['status'] == 'pending' and not next_step:
            next_step = step

    remaining_steps = len(steps) - completed_steps

    if not next_step:
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'next': None,
            'context': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'message': 'All tasks completed',
            },
        }

    # Build base result
    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'next': {
            'task_number': next_task['number'],
            'task_title': next_task['title'],
            'domain': next_task.get('domain'),
            'profile': next_task.get('profile'),
            'skills': next_task.get('skills', []),
            'origin': next_task.get('origin', 'plan'),
            'deliverable': next_task.get('deliverable', 0),
            'cost_size': next_task.get('cost_size'),
            'predicted_cost_tokens': next_task.get('predicted_cost_tokens'),
            'envelope_id': next_task.get('envelope_id'),
            'step_number': next_step['number'],
            'step_target': next_step['target'],
        },
        'context': {
            'completed_steps': completed_steps,
            'remaining_steps': remaining_steps,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
        },
    }

    # Include deliverable context if requested
    if getattr(args, 'include_context', False):
        deliverable = next_task.get('deliverable', 0)
        if deliverable:
            deliverable_context = get_deliverable_context(deliverable)
            result['next'].update(deliverable_context)

    return result


def cmd_loop_exit_guard(args) -> dict:
    """Handle 'loop-exit-guard' subcommand.

    Script-level enforcement of the phase-5-execute "unfinished > 0 → must
    continue" invariant. The predicate is the union of two unfinished
    terminal-state buckets: ``pending`` (task never started) AND
    ``in_progress`` (task started but not finalized — e.g., the dispatch
    that began it terminated mid-flight). Returns ``status: continue`` when
    EITHER bucket is non-empty so the orchestrator MUST re-dispatch;
    returns ``status: success`` only when BOTH counts are zero.

    The TOON return carries both axis counts/ids in BOTH branches so callers
    can log which axis was non-empty and so downstream consumers (e.g., the
    ``unfinished_tasks_count`` handshake invariant) can read either field
    without conditional presence checks. The bucket traversal reuses the
    same ``get_all_tasks`` walk as ``cmd_list``/``cmd_next_tasks``; no
    behaviour change to existing query commands. The guard remains
    intentionally narrow — it answers exactly one question (is the queue
    empty by the broadened predicate?) and never tries to classify why a
    task is pending/in_progress or whether its dependencies are satisfied.
    The skill prose at ``phase-5-execute/SKILL.md`` § Step 12a names the
    contract; authoritative enforcement lives here.

    **The owed-verification split.** Every branch also reports
    ``owed_count`` / ``owed_ids`` — the subset of the ``in_progress`` bucket
    carrying ``verification_owed: true`` (a task waiting on an
    orchestrator-tier build). They remain BLOCKING: an owed task is not done
    before its build reports, so the clean-exit verdict is unchanged. The
    split exists because the no-progress predicate must not count a task the
    workflow itself is holding open (see ``evaluate_no_progress``).

    **No-progress mode (B7).** Passing any predicate input switches the verb
    into the deterministic B7 evaluation the orchestrator runs after a dispatch
    returns: the predicate, its three values, and the resulting classification
    are added to the result. The evaluation itself needs BOTH measurements —
    ``--consumed-tokens`` and ``--completed-tasks-delta`` — and a call that
    supplies one without the other is refused with ``no_progress_not_decidable``
    rather than evaluated with the absent input read as ``0``. The predicate is
    stated once in ``plan-marshall/workflow/execution.md`` § B7; the arithmetic
    lives here, not in prose.
    """
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    pending_ids = [t['number'] for _, t in all_tasks if t.get('status') == 'pending']
    in_progress_tasks = [t for _, t in all_tasks if t.get('status') == 'in_progress']
    in_progress_ids = [t['number'] for t in in_progress_tasks]
    owed_ids = [t['number'] for t in in_progress_tasks if t.get('verification_owed') is True]
    owed_count = len(owed_ids)
    pending_count = len(pending_ids)
    in_progress_count = len(in_progress_ids)
    # The done count is reported so ``completed_tasks_delta`` has a readable
    # source: the orchestrator snapshots this field per iteration and subtracts
    # the previous iteration's value. It is the same queue walk the counts above
    # come from, so the delta and the queue state can never disagree about which
    # tasks are done.
    done_count = sum(1 for _, t in all_tasks if t.get('status') == 'done')

    result: dict = {
        'plan_id': args.plan_id,
        'pending_count': pending_count,
        'pending_ids': pending_ids,
        'in_progress_count': in_progress_count,
        'in_progress_ids': in_progress_ids,
        'owed_count': owed_count,
        'owed_ids': owed_ids,
        'done_count': done_count,
    }

    if pending_count > 0 or in_progress_count > 0:
        if pending_count > 0 and in_progress_count > 0:
            message = (
                f'{pending_count} pending and {in_progress_count} in_progress '
                f'task(s) remain — orchestrator MUST re-dispatch the '
                f'execution-context before transitioning out of phase-5-execute.'
            )
        elif pending_count > 0:
            message = (
                f'{pending_count} pending task(s) remain — orchestrator MUST '
                f're-dispatch the execution-context before transitioning out '
                f'of phase-5-execute.'
            )
        else:
            message = (
                f'{in_progress_count} in_progress task(s) remain — orchestrator '
                f'MUST re-dispatch the execution-context before transitioning '
                f'out of phase-5-execute.'
            )
        result.update({'status': 'continue', 'message': message})
    else:
        result.update({'status': 'success', 'message': 'Unfinished queue empty — clean exit permitted.'})

    if _no_progress_mode_requested(args):
        completed_tasks_delta = _int_arg(args, 'completed_tasks_delta')
        consumed_tokens = _int_arg(args, 'consumed_tokens')
        if consumed_tokens is None or completed_tasks_delta is None:
            absent = [
                flag
                for flag, value in (
                    ('--consumed-tokens', consumed_tokens),
                    ('--completed-tasks-delta', completed_tasks_delta),
                )
                if value is None
            ]
            result.update(
                {
                    'status': 'error',
                    'error': NO_PROGRESS_NOT_DECIDABLE,
                    'message': (
                        'B7 no-progress mode needs both measurements; absent: '
                        f'{", ".join(absent)}. An absent input is not a measured zero, '
                        'so the dispatch is not decidable by the predicate.'
                    ),
                }
            )
            return result
        result.update(
            evaluate_no_progress(
                provisional_cause=getattr(args, 'provisional_cause', None) or B7_PROVISIONAL_CAUSE,
                in_progress_count=in_progress_count,
                owed_count=owed_count,
                completed_tasks_delta=completed_tasks_delta,
                consumed_tokens=consumed_tokens,
                verification_handback=bool(getattr(args, 'verification_handback', False)),
                pending_verify_steps=_step_ids_arg(args),
                manifest_verification_steps=_manifest_verification_steps(args.plan_id),
            )
        )

    return result


def _int_arg(args, name: str) -> int | None:
    """Read an optional integer flag, keeping absence distinguishable from ``0``.

    ``None`` is returned when the caller supplied no value, so the caller can
    refuse the evaluation instead of reading the absence as a measured zero.
    ``type(value) is int`` rather than ``isinstance`` — a bool is an int
    subclass, and ``True``/``False`` are not measurements.
    """
    value = getattr(args, name, None)
    return value if type(value) is int else None


def _step_ids_arg(args) -> list[str]:
    """Split the comma-separated ``--pending-verify-steps`` value into step ids."""
    raw = getattr(args, 'pending_verify_steps', None)
    if not isinstance(raw, str):
        return []
    return [part.strip() for part in raw.split(',') if part.strip()]


def _no_progress_mode_requested(args) -> bool:
    """True when the caller supplied any B7 predicate input.

    The mode is opt-in so the guard's pre-dispatch queue-peek call site keeps
    its exact previous shape: a caller that passes no predicate input gets no
    classification and no predicate fields. The discriminator is a SUPPLIED
    value, not mere attribute presence — the argparse surface gives
    ``--verification-handback`` a ``False`` default, so ``is not None`` would
    switch the mode on for every CLI call.

    Supplying a predicate input is not the same as supplying the predicate's
    two measurements: a mode entered without BOTH ``--consumed-tokens`` and
    ``--completed-tasks-delta`` is refused with ``no_progress_not_decidable``
    rather than evaluated with an absent input read as ``0``.
    """
    return (
        getattr(args, 'consumed_tokens', None) is not None
        or getattr(args, 'completed_tasks_delta', None) is not None
        or getattr(args, 'pending_verify_steps', None) is not None
        or getattr(args, 'verification_handback', False) is True
    )


def _manifest_verification_steps(plan_id: str) -> set[str] | None:
    """Return the composed ``phase_5.verification_steps`` of the plan's manifest.

    The manifest (``execution.toon``) is the write-time snapshot phase 5 consumes
    verbatim, so it is the authority for which step ids a hand-back may name.
    ``None`` means the manifest is absent or unreadable — a hand-back naming any
    step then exempts nothing, because there is no composed list to check it
    against (the fail-closed direction: an unverifiable exemption is no
    exemption).
    """
    try:
        manifest_path = get_plan_dir(plan_id) / MANIFEST_FILENAME
    except Exception:
        return None
    if not manifest_path.is_file():
        return None
    try:
        manifest = parse_toon(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ToonParseError, ValueError):
        return None
    if not isinstance(manifest, dict):
        return None
    phase_5 = manifest.get('phase_5')
    if not isinstance(phase_5, dict):
        return None
    steps = phase_5.get('verification_steps')
    if not isinstance(steps, list):
        return None
    return {step for step in steps if isinstance(step, str) and step}


def evaluate_no_progress(
    *,
    provisional_cause: str,
    in_progress_count: int,
    owed_count: int,
    completed_tasks_delta: int,
    consumed_tokens: int,
    verification_handback: bool,
    pending_verify_steps: list[str],
    manifest_verification_steps: set[str] | None = None,
) -> dict:
    """Evaluate the B7 no-progress predicate and classify a returning dispatch.

    The predicate is the one stated in ``plan-marshall/workflow/execution.md``
    § "B7 — voluntary_checkpoint no-progress reclassification"; this function
    is its only implementation, so the workflow prose cites it rather than
    restating the arithmetic.

    Two exemptions bound the predicate, and neither is a blanket one:

    1. **A hand-back exempts only the owed task(s) it names.** A return carrying
       the ``verification_handback`` discriminator beside a NON-EMPTY
       ``pending_verify_steps[]`` is classified ``verification_handback`` when
       the predicate does not hold — but a non-owed task that stalled in the
       SAME dispatch still decides it. The hand-back is the prescribed outcome
       FOR THE TASK IT HANDS BACK, not a licence to stall the rest of the
       queue. Its step ids are checked against the manifest's composed
       ``phase_5.verification_steps`` (``manifest_verification_steps``): an id
       outside that list names no obligation the plan composed, so it does not
       exempt. A missing or unreadable manifest therefore exempts nothing —
       an unverifiable exemption is no exemption.
    2. **An owed task does not count as in-progress progress.** A task held
       open with ``verification_owed: true`` is ``in_progress`` BY DESIGN, so
       it is subtracted from the predicate's ``in_progress_count``. It still
       blocks the clean exit (that verdict lives in ``cmd_loop_exit_guard``
       and is unchanged); it just cannot manufacture a no-progress verdict.

    The predicate decides BEFORE the hand-back does, in the order the workflow
    states: the hand-back's exemption is scoped to the task it names, so the
    predicate must be consulted first.

    The 50,000-token threshold and the ``error`` routing of a genuine stall
    are unchanged.

    Returns:
      - ``predicate_in_progress_count``: in-progress tasks MINUS owed ones
      - ``predicate_completed_tasks_delta`` / ``predicate_consumed_tokens``:
            the two forwarded values, echoed for the decision log
      - ``predicate_holds``: the three-way conjunction
      - ``verification_handback_valid``: True only when the discriminator, a
            non-empty ``pending_verify_steps[]``, and a step list every entry
            of which the manifest composed arrived together
      - ``verification_handback_unknown_steps``: the named ids the manifest
            does not carry — the reason an otherwise valid-looking hand-back
            exempts nothing
      - ``classification``: the final termination cause
      - ``classification_reason``: why that cause won
    """
    predicate_in_progress = max(in_progress_count - owed_count, 0)
    predicate_holds = (
        predicate_in_progress > 0 and completed_tasks_delta == 0 and consumed_tokens > B7_NO_PROGRESS_TOKEN_THRESHOLD
    )
    allowed_steps = manifest_verification_steps if manifest_verification_steps is not None else set()
    unknown_steps = [step for step in pending_verify_steps if step not in allowed_steps]
    handback_valid = verification_handback and bool(pending_verify_steps) and not unknown_steps

    if provisional_cause != B7_PROVISIONAL_CAUSE:
        classification, reason = provisional_cause, 'not_a_provisional_checkpoint'
    elif predicate_holds:
        classification = NO_PROGRESS_CAUSE
        reason = (
            'no_progress_predicate_holds_beside_handback' if verification_handback else 'no_progress_predicate_holds'
        )
    elif handback_valid:
        classification, reason = VERIFICATION_HANDBACK_CAUSE, 'declared_orchestrator_build_handback'
    else:
        classification, reason = B7_PROVISIONAL_CAUSE, 'no_progress_predicate_false'

    return {
        'predicate_in_progress_count': predicate_in_progress,
        'predicate_completed_tasks_delta': completed_tasks_delta,
        'predicate_consumed_tokens': consumed_tokens,
        'predicate_holds': predicate_holds,
        'verification_handback_valid': handback_valid,
        'verification_handback_unknown_steps': unknown_steps,
        'classification': classification,
        'classification_reason': reason,
    }


def cmd_next_tasks(args) -> dict:
    """Handle 'next-tasks' subcommand.

    Returns all tasks that are ready for parallel execution
    (all depends_on tasks are completed).
    """
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = _build_done_set(all_tasks)

    # Find all pending tasks with satisfied dependencies
    ready_tasks = []
    blocked_tasks = []

    for _path, task in all_tasks:
        if task.get('status') != 'pending':
            continue

        deps = task.get('depends_on', [])
        unmet_deps = [dep for dep in deps if dep not in done_tasks]

        if not unmet_deps:
            # All dependencies satisfied - ready for execution
            completed, total = calculate_progress(task)
            ready_tasks.append(
                {
                    'number': task['number'],
                    'title': task['title'],
                    'domain': task.get('domain'),
                    'profile': task.get('profile'),
                    'skills': task.get('skills', []),
                    'deliverable': task.get('deliverable', 0),
                    'progress': f'{completed}/{total}',
                }
            )
        else:
            # Has unmet dependencies
            blocked_tasks.append({'number': task['number'], 'title': task['title'], 'waiting_for': unmet_deps})

    # Also include in_progress tasks
    in_progress_tasks = []
    for _path, task in all_tasks:
        if task.get('status') == 'in_progress':
            completed, total = calculate_progress(task)
            in_progress_tasks.append(
                {
                    'number': task['number'],
                    'title': task['title'],
                    'domain': task.get('domain'),
                    'profile': task.get('profile'),
                    'skills': task.get('skills', []),
                    'progress': f'{completed}/{total}',
                }
            )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'ready_count': len(ready_tasks),
        'in_progress_count': len(in_progress_tasks),
        'blocked_count': len(blocked_tasks),
        'ready_tasks': ready_tasks,
        'in_progress_tasks': in_progress_tasks,
        'blocked_tasks': blocked_tasks,
    }
