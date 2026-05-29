#!/usr/bin/env python3
"""
Manage status.json files with phase tracking, metadata, and lifecycle operations.

Handles plan status storage (JSON), phase operations, metadata management,
plan discovery, phase transitions, archiving, and routing.
Storage: JSON format (.plan/local/plans/{plan_id}/status.json)
Output: TOON format for API responses

Usage:
    python3 manage-status.py create --plan-id EXAMPLE-PLAN --title "Title" --phases 1-init,2-refine,3-outline
    python3 manage-status.py read --plan-id EXAMPLE-PLAN
    python3 manage-status.py set-phase --plan-id EXAMPLE-PLAN --phase 2-refine
    python3 manage-status.py update-phase --plan-id EXAMPLE-PLAN --phase 1-init --status done
    python3 manage-status.py progress --plan-id EXAMPLE-PLAN
    python3 manage-status.py metadata --plan-id EXAMPLE-PLAN --set --field change_type --value feature
    python3 manage-status.py metadata --plan-id EXAMPLE-PLAN --get --field change_type
    python3 manage-status.py get-context --plan-id EXAMPLE-PLAN
    python3 manage-status.py list
    python3 manage-status.py transition --plan-id EXAMPLE-PLAN --completed 1-init
    python3 manage-status.py archive --plan-id EXAMPLE-PLAN
    python3 manage-status.py route --phase 1-init
    python3 manage-status.py get-routing-context --plan-id EXAMPLE-PLAN
    python3 manage-status.py mark-step-done --plan-id EXAMPLE-PLAN --phase 5-execute --step discovery --outcome done
"""

import argparse

from _cmd_aggregate_confidence import cmd_aggregate_confidence
from _cmd_change_type_heuristic import cmd_change_type_heuristic
from _cmd_lifecycle import (
    cmd_archive,
    cmd_create,
    cmd_delete_plan,
    cmd_transition,
    verify_blocks_transition,
)
from _cmd_mark_step import VALID_LOOP_BACK_TARGETS, cmd_mark_step_done
from _cmd_merge_lock import (
    cmd_merge_lock_acquire,
    cmd_merge_lock_check,
    cmd_merge_lock_release,
)
from _cmd_routing import cmd_get_routing_context, cmd_route, cmd_self_test
from _status_query import (
    cmd_get_context,
    cmd_get_worktree_path,
    cmd_list,
    cmd_list_orphans,
    cmd_metadata,
    cmd_progress,
    cmd_read,
    cmd_set_phase,
    cmd_update_phase,
)
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_field_arg,
    add_phase_arg,
    add_plan_id_arg,
    parse_args_with_toon_errors,
)


def _loop_back_target_type(value: str) -> str:
    """Custom argparse type for --loop-back-target.

    Normalises the input (lowercases) and validates against VALID_LOOP_BACK_TARGETS.
    Raises argparse.ArgumentTypeError with the canonical error message format that
    matches the API-layer guard's `invalid_loop_back_target` error code.
    """
    normalised = value.lower()
    if normalised not in VALID_LOOP_BACK_TARGETS:
        raise argparse.ArgumentTypeError(
            f'--loop-back-target must be one of '
            f'{list(VALID_LOOP_BACK_TARGETS)}, got: {value}'
        )
    return normalised


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Manage status.json files with phase tracking and metadata', allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # create
    create_parser = subparsers.add_parser('create', help='Create status.json', allow_abbrev=False)
    add_plan_id_arg(create_parser)
    create_parser.add_argument('--title', required=True, help='Plan title')
    create_parser.add_argument(
        '--phases',
        required=True,
        help='Comma-separated phase names (e.g., 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize)',
    )
    create_parser.add_argument('--force', action='store_true', help='Overwrite existing status')
    create_parser.add_argument(
        '--use-worktree',
        action='store_true',
        help=(
            'Mark the plan as running in an isolated git worktree. When set, '
            '--worktree-branch is required and seeded into status.metadata; '
            '--worktree-path is optional and may be filled in later by '
            'phase-5-execute Step 2.5 (deferred materialization).'
        ),
    )
    create_parser.add_argument(
        '--worktree-path',
        default=None,
        help=(
            'Absolute path to the worktree root (optional with --use-worktree). '
            'When omitted, persisted as the empty-string sentinel marking the '
            'deferred-materialization window between phase-1 and phase-5; '
            'phase-5-execute Step 2.5 back-fills the resolved path once '
            '`git worktree add` runs. Persisted as status.metadata.worktree_path.'
        ),
    )
    create_parser.add_argument(
        '--worktree-branch',
        default=None,
        help=(
            'Feature branch ref checked out in the worktree (required with '
            '--use-worktree). Persisted as status.metadata.worktree_branch.'
        ),
    )
    create_parser.set_defaults(func=cmd_create)

    # read
    read_parser = subparsers.add_parser('read', help='Read plan status', allow_abbrev=False)
    add_plan_id_arg(read_parser)
    read_parser.set_defaults(func=cmd_read)

    # set-phase
    set_phase_parser = subparsers.add_parser('set-phase', help='Set current phase', allow_abbrev=False)
    add_plan_id_arg(set_phase_parser)
    add_phase_arg(set_phase_parser)
    set_phase_parser.set_defaults(func=cmd_set_phase)

    # update-phase
    update_phase_parser = subparsers.add_parser('update-phase', help='Update phase status', allow_abbrev=False)
    add_plan_id_arg(update_phase_parser)
    add_phase_arg(update_phase_parser)
    update_phase_parser.add_argument(
        '--status', required=True, choices=['pending', 'in_progress', 'done'], help='Phase status'
    )
    update_phase_parser.set_defaults(func=cmd_update_phase)

    # progress
    progress_parser = subparsers.add_parser('progress', help='Calculate progress', allow_abbrev=False)
    add_plan_id_arg(progress_parser)
    progress_parser.set_defaults(func=cmd_progress)

    # metadata
    metadata_parser = subparsers.add_parser('metadata', help='Get or set metadata fields', allow_abbrev=False)
    add_plan_id_arg(metadata_parser)
    metadata_parser.add_argument('--get', action='store_true', help='Get metadata field')
    metadata_parser.add_argument('--set', action='store_true', help='Set metadata field')
    add_field_arg(metadata_parser)
    metadata_parser.add_argument('--value', help='Metadata field value (required for --set)')
    metadata_parser.set_defaults(func=cmd_metadata)

    # get-context
    get_context_parser = subparsers.add_parser('get-context', help='Get combined status context', allow_abbrev=False)
    add_plan_id_arg(get_context_parser)
    get_context_parser.set_defaults(func=cmd_get_context)

    # get-worktree-path
    get_worktree_path_parser = subparsers.add_parser(
        'get-worktree-path',
        help='Resolve the persisted worktree path for a plan (returns empty when use_worktree==false)',
        allow_abbrev=False,
    )
    add_plan_id_arg(get_worktree_path_parser)
    get_worktree_path_parser.set_defaults(func=cmd_get_worktree_path)

    # list
    list_parser = subparsers.add_parser('list', help='Discover all plans', allow_abbrev=False)
    list_parser.add_argument('--filter', help='Filter by phases (comma-separated)')
    list_parser.set_defaults(func=cmd_list)

    # list-orphans
    list_orphans_parser = subparsers.add_parser(
        'list-orphans',
        help=(
            'Discover orphan plan directories — entries under .plan/local/plans/ with no readable '
            'status.json. Inverse of `list`; the archived-plans directory is excluded.'
        ),
        allow_abbrev=False,
    )
    list_orphans_parser.set_defaults(func=cmd_list_orphans)

    # transition
    transition_parser = subparsers.add_parser('transition', help='Transition to next phase', allow_abbrev=False)
    add_plan_id_arg(transition_parser)
    transition_parser.add_argument('--completed', required=True, help='Completed phase')
    transition_parser.set_defaults(func=cmd_transition)

    # archive
    archive_parser = subparsers.add_parser('archive', help='Archive completed plan', allow_abbrev=False)
    add_plan_id_arg(archive_parser)
    archive_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    archive_parser.add_argument(
        '--reason',
        default=None,
        help=(
            'Optional structured reason string recorded alongside the archive '
            '(e.g., low_confidence, dangling_worktree, orphan_directory, '
            'normal_completion). Persisted to status.metadata.archived_reason '
            'before the plan directory is moved into the archive. Referenced by '
            'plan-doctor Rule stuck-low-confidence-archive as the canonical '
            'remediation flag. When omitted, the archived status.json simply '
            'lacks the archived_reason field — no schema migration is required.'
        ),
    )
    archive_parser.set_defaults(func=cmd_archive)

    # route
    route_parser = subparsers.add_parser('route', help='Get skill for phase', allow_abbrev=False)
    add_phase_arg(route_parser)
    route_parser.set_defaults(func=cmd_route)

    # get-routing-context
    routing_context_parser = subparsers.add_parser(
        'get-routing-context',
        help='Get combined routing context (phase, skill, progress)',
        allow_abbrev=False,
    )
    add_plan_id_arg(routing_context_parser)
    routing_context_parser.set_defaults(func=cmd_get_routing_context)

    # delete-plan
    delete_plan_parser = subparsers.add_parser('delete-plan', help='Delete entire plan directory', allow_abbrev=False)
    add_plan_id_arg(delete_plan_parser)
    delete_plan_parser.add_argument(
        '--no-restore-lessons',
        dest='no_restore_lessons',
        action='store_true',
        help=(
            'Skip the default auto-restore of any lesson-{id}.md file inside the plan '
            'directory back to .plan/local/lessons-learned/ before deletion. Use only '
            'when the caller deliberately wants the moved lesson to be discarded.'
        ),
    )
    delete_plan_parser.set_defaults(func=cmd_delete_plan)

    # mark-step-done
    mark_step_parser = subparsers.add_parser(
        'mark-step-done',
        help='Mark a phase step outcome in status.metadata.phase_steps',
        allow_abbrev=False,
    )
    add_plan_id_arg(mark_step_parser)
    add_phase_arg(mark_step_parser)
    mark_step_parser.add_argument('--step', required=True, help='Step identifier within the phase')
    mark_step_parser.add_argument(
        '--outcome',
        required=True,
        choices=['done', 'skipped', 'loop_back', 'failed'],
        help=(
            'Step outcome. ``done`` and ``skipped`` are terminal markers (dispatcher will not re-fire). '
            '``loop_back`` records a loop-back iteration: dispatcher will re-fire the step on next phase entry '
            '(treat as no record - dispatch as fresh run). '
            '``failed`` records that the step aborted with an error (e.g., graceful timeout degradation); '
            'the dispatcher will retry the step on next phase entry.'
        ),
    )
    mark_step_parser.add_argument('--force', action='store_true', help='Overwrite an existing conflicting outcome')
    mark_step_parser.add_argument(
        '--display-detail',
        default=None,
        help='One-line user-facing detail string describing the step outcome (required for phase-6-finalize steps).',
    )
    mark_step_parser.add_argument(
        '--head-at-completion',
        default=None,
        help=(
            'Optional git SHA captured at step completion. Persisted alongside outcome and '
            'display_detail; consulted by resumable phase dispatchers (e.g., phase-6-finalize '
            'pre-push-quality-gate) to decide whether to skip or re-fire after the worktree HEAD '
            'has advanced.'
        ),
    )
    mark_step_parser.add_argument(
        '--loop-back-target',
        default=None,
        type=_loop_back_target_type,
        help=(
            'Loop-back target phase. REQUIRED when --outcome=loop_back, must be one of '
            '5-execute (full phase rollback for fix-task-required dispositions: FIX with '
            'fix_tasks_created > 0, overflow_deferred > 0) or 6-finalize (inline replay '
            'for inline-fixable dispositions: SUPPRESS, narrow-rationale ACCEPT, single-'
            'annotation FIX). Persisted in the step outcome record alongside display_detail '
            'and head_at_completion. The phase-6-finalize loop-back continuation hook reads '
            'this field to decide between full-phase rollback (re-dispatch phase-5-execute) '
            'and inline replay (re-fire the loop-back-marked step from the resumable '
            're-entry check). Forbidden when --outcome != loop_back.'
        ),
    )
    mark_step_parser.set_defaults(func=cmd_mark_step_done)

    # change-type-heuristic
    change_type_parser = subparsers.add_parser(
        'change-type-heuristic',
        help='Deterministic change-type classifier for phase-3-outline Step 4 (no LLM dispatch)',
        description=(
            "Classify a plan's clarified-request narrative against a fixed "
            "keyword table and return one of feature, bug_fix, tech_debt, "
            "enhancement, verification, analysis — or ambiguous=true when "
            "no keyword fires, when the top two scores tie, or when "
            "confidence falls below 0.7. Use --persist to write the result "
            "to status.metadata.change_type when the heuristic resolves "
            "(persistence is skipped in the ambiguous branch so the LLM "
            "detect-change-type workflow is the single writer there)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(change_type_parser)
    change_type_parser.add_argument(
        '--persist',
        action='store_true',
        help='Persist the resolved change_type to status.metadata.change_type when not ambiguous.',
    )
    change_type_parser.set_defaults(func=cmd_change_type_heuristic)

    # aggregate-confidence — weighted-math aggregator for phase-2-refine Step 10.
    aggregate_confidence_parser = subparsers.add_parser(
        'aggregate-confidence',
        help='Weighted-math confidence aggregator for phase-2-refine Step 10 (no LLM dispatch)',
        description=(
            "Compute the overall confidence from per-dimension scores using the "
            "fixed weights from phase-2-refine SKILL.md Step 10: correctness 20%, "
            "completeness 20%, consistency 20%, non-duplication 10%, ambiguity 20%, "
            "module-mapping 10%. Scores are 0..100; missing dimensions default to 0 "
            "and are reported in missing_dimensions. Use --scores-file PATH (JSON "
            "object keyed by dimension) for batch input, or pass individual "
            "--<dimension> N flags; the two forms are mutually exclusive when "
            "--scores-file is supplied (CLI flags still override file values for "
            "any keys they specify). With --persist, the overall confidence is "
            "written to status.metadata.confidence."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(aggregate_confidence_parser)
    aggregate_confidence_parser.add_argument(
        '--scores-file',
        dest='scores_file',
        default=None,
        help='Path to a JSON object keyed by dimension name (kebab- or snake-case).',
    )
    for flag, dest in (
        ('--correctness', 'correctness'),
        ('--completeness', 'completeness'),
        ('--consistency', 'consistency'),
        ('--non-duplication', 'non_duplication'),
        ('--ambiguity', 'ambiguity'),
        ('--module-mapping', 'module_mapping'),
    ):
        aggregate_confidence_parser.add_argument(
            flag,
            dest=dest,
            type=float,
            default=None,
            help=f'Score 0..100 for the {dest.replace("_", " ")} dimension.',
        )
    aggregate_confidence_parser.add_argument(
        '--persist',
        action='store_true',
        help='Persist the overall confidence to status.metadata.confidence.',
    )
    aggregate_confidence_parser.set_defaults(func=cmd_aggregate_confidence)

    # merge-lock — cross-plan merge-coordination mutex (acquire/check/release).
    merge_lock_parser = subparsers.add_parser(
        'merge-lock',
        help='Cross-plan merge-coordination mutex (acquire/check/release)',
        description=(
            "Acquire, check, or release the cross-plan merge-lock that "
            "serializes the merge-to-main critical section across "
            "concurrently-finalizing plans. The marker is stored under "
            "status.metadata.merging_on_main (plus merge_lock_acquired_at) "
            "of the acquiring plan. 'acquire' is BLOCKING: it polls "
            "(Python time.sleep, 5-minute window) until the lock frees or "
            "the window elapses, returning status: acquired or status: "
            "blocked with blocking_plan_id. 'check' is a non-blocking read "
            "(status: free | held). 'release' clears this plan's marker "
            "idempotently. AskUserQuestion is never issued here — the "
            "orchestrator owns the timeout escalation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    merge_lock_subparsers = merge_lock_parser.add_subparsers(dest='merge_lock_verb', required=True)

    merge_lock_acquire_parser = merge_lock_subparsers.add_parser(
        'acquire',
        help='Blocking acquire of the merge-lock (5-minute poll window)',
        allow_abbrev=False,
    )
    add_plan_id_arg(merge_lock_acquire_parser)
    merge_lock_acquire_parser.set_defaults(func=cmd_merge_lock_acquire)

    merge_lock_check_parser = merge_lock_subparsers.add_parser(
        'check',
        help='Non-blocking read of the current merge-lock holder',
        allow_abbrev=False,
    )
    add_plan_id_arg(merge_lock_check_parser)
    merge_lock_check_parser.set_defaults(func=cmd_merge_lock_check)

    merge_lock_release_parser = merge_lock_subparsers.add_parser(
        'release',
        help="Idempotently clear this plan's merge-lock marker",
        allow_abbrev=False,
    )
    add_plan_id_arg(merge_lock_release_parser)
    merge_lock_release_parser.set_defaults(func=cmd_merge_lock_release)

    # self-test
    self_test_parser = subparsers.add_parser('self-test', help='Verify manage-status health', allow_abbrev=False)
    self_test_parser.set_defaults(func=cmd_self_test)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    if result is not None:
        output_toon(result)
    # Strict-drift exit-code contract for ``transition``: the inline guard
    # in ``cmd_transition`` returns the verify result dict unchanged when
    # the boundary is guarded and verify reports drift (or one of the
    # worktree/main-checkout boundary refusals). Mirror the
    # ``phase_handshake verify --strict`` CLI semantics so callers that
    # used to gate on the standalone verify's exit code keep working.
    # The refusal classification is shared with ``cmd_transition``'s
    # in-process guard via ``verify_blocks_transition`` so the two contracts
    # cannot drift apart.
    if args.command == 'transition' and isinstance(result, dict) and verify_blocks_transition(result):
        return 1
    return 0


if __name__ == '__main__':
    main()
