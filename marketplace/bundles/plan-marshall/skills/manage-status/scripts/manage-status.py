#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    python3 manage-status.py assert-step-recorded --plan-id EXAMPLE-PLAN --phase 6-finalize --step ci-verify --require-terminal
    python3 manage-status.py sibling-collision-check --plan-id EXAMPLE-PLAN
"""

import argparse

from _cmd_aggregate_confidence import cmd_aggregate_confidence
from _cmd_assert_step_recorded import cmd_assert_step_recorded
from _cmd_change_type_heuristic import cmd_change_type_heuristic
from _cmd_classification_validate import cmd_classification_validate
from _cmd_lifecycle import (
    cmd_archive,
    cmd_create,
    cmd_delete_plan,
    cmd_transition,
    verify_blocks_transition,
)
from _cmd_mark_step import VALID_LOOP_BACK_TARGETS, cmd_mark_step_done
from _cmd_planning_lane import (
    cmd_planning_lane_escalate,
    cmd_planning_lane_route,
)
from _cmd_routing import cmd_get_routing_context, cmd_route, cmd_self_test
from _cmd_sibling_collision import cmd_sibling_collision
from _status_core import TITLE_TOKEN_STATES
from _status_query import (
    cmd_get_context,
    cmd_get_worktree_path,
    cmd_list,
    cmd_list_orphans,
    cmd_metadata,
    cmd_progress,
    cmd_read,
    cmd_set_phase,
    cmd_title_token,
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
            'only status.metadata.use_worktree is persisted at create; the '
            'feature branch (feature/{plan_id}) and the resolved worktree_path '
            'are derived and back-filled at phase-5-execute Step 2.5.'
        ),
    )
    create_parser.set_defaults(func=cmd_create)

    # read (get is an accepted alias for the same operation)
    read_parser = subparsers.add_parser('read', aliases=['get'], help='Read plan status', allow_abbrev=False)
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

    # title-token (set | clear)
    title_token_parser = subparsers.add_parser(
        'title-token',
        help='Set or clear the field-only title_token marker in status.json (no rendering)',
        description=(
            'Write or remove the bare title_token state string in '
            'status.title_token. manage-status performs NO rendering — the '
            'composition (glyph vocabulary + {icon} {body} assembly) lives in '
            'manage-terminal-title. This verb only persists the state so the '
            'per-target renderer can read it.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    title_token_subparsers = title_token_parser.add_subparsers(dest='token_verb', required=True)

    title_token_set_parser = title_token_subparsers.add_parser(
        'set',
        help='Write status.title_token = {state}',
        allow_abbrev=False,
    )
    add_plan_id_arg(title_token_set_parser)
    title_token_set_parser.add_argument(
        '--state',
        required=True,
        choices=sorted(TITLE_TOKEN_STATES),
        help='Title-token state to persist into status.title_token.',
    )
    title_token_set_parser.set_defaults(func=cmd_title_token)

    title_token_clear_parser = title_token_subparsers.add_parser(
        'clear',
        help='Remove the status.title_token field (idempotent)',
        allow_abbrev=False,
    )
    add_plan_id_arg(title_token_clear_parser)
    title_token_clear_parser.set_defaults(func=cmd_title_token)

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

    # assert-step-recorded — read-only post-dispatch guard over phase_steps.
    assert_step_parser = subparsers.add_parser(
        'assert-step-recorded',
        help='Assert a phase step has a terminal record in status.metadata.phase_steps (read-only)',
        description=(
            'Read-only verdict over status.metadata.phase_steps[phase][step]: '
            'reports recorded=true iff a dict entry with a terminal outcome in '
            '{done, skipped, loop_back, failed} exists. The phase-6-finalize '
            'dispatcher calls this after every dispatched-step return to detect '
            'the silent gap where a step returns status: success but skips its '
            'mandated mark-step-done side-effect. With --require-terminal, a '
            'missing terminal record is escalated to status: error, '
            'error: step_record_missing so the dispatcher gets a branchable '
            'verdict. Performs zero writes to status.json.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(assert_step_parser)
    add_phase_arg(assert_step_parser)
    assert_step_parser.add_argument('--step', required=True, help='Step identifier within the phase')
    assert_step_parser.add_argument(
        '--require-terminal',
        dest='require_terminal',
        action='store_true',
        help=(
            'Escalate a missing terminal record to status: error, '
            'error: step_record_missing instead of returning recorded: false.'
        ),
    )
    assert_step_parser.set_defaults(func=cmd_assert_step_recorded)

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

    # planning-lane (route | escalate)
    planning_lane_parser = subparsers.add_parser(
        'planning-lane',
        help='Deterministic planning-lane router (route | escalate)',
        description=(
            "Resolve planning_lane in {light, deep} from cheap field reads + a "
            "request.md regex (zero codebase discovery, zero LLM cognition). "
            "'route' evaluates the DQ1 signal set (S1-S6): default is light; any "
            "deep-precondition signal forces deep; plan.phase-1-init."
            "deep_lane (always|never|auto) short-circuits the signals. 'escalate' "
            "is the one-way light->deep ratchet — it sets planning_lane=deep + "
            "lane_escalated=true and refuses any downgrade to light. Both verbs "
            "emit one decision-log line."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    planning_lane_subparsers = planning_lane_parser.add_subparsers(
        dest='planning_lane_verb', required=True
    )

    planning_lane_route_parser = planning_lane_subparsers.add_parser(
        'route',
        help='Resolve {light|deep} from the DQ1 signal set and persist it',
        allow_abbrev=False,
    )
    add_plan_id_arg(planning_lane_route_parser)
    planning_lane_route_parser.add_argument(
        '--lane-override',
        choices=['deep', 'light'],
        default=None,
        help='Seed the S6 explicit-override signal (CLI-init convenience)',
    )
    planning_lane_route_parser.add_argument(
        '--persist',
        action='store_true',
        help='Write the resolved lane into status.metadata.planning_lane',
    )
    planning_lane_route_parser.set_defaults(func=cmd_planning_lane_route)

    planning_lane_escalate_parser = planning_lane_subparsers.add_parser(
        'escalate',
        help='One-way light->deep ratchet (refuses downgrade)',
        allow_abbrev=False,
    )
    add_plan_id_arg(planning_lane_escalate_parser)
    planning_lane_escalate_parser.add_argument(
        '--trigger',
        choices=['explosion', 'premise', 'cross_cutting'],
        required=True,
        help='The DQ3 escalation trigger that fired',
    )
    planning_lane_escalate_parser.add_argument(
        '--persist',
        action='store_true',
        help='Write the escalation mutation into status.metadata',
    )
    planning_lane_escalate_parser.set_defaults(func=cmd_planning_lane_escalate)

    # classification-validate (deterministic, flag-not-block)
    classification_validate_parser = subparsers.add_parser(
        'classification-validate',
        help='Cross-check change_type/scope_estimate vs cheap request signals (flag-not-block)',
        description=(
            "Deterministic classification-validation gate. Cross-checks the plan's "
            "change_type and scope_estimate against cheap request signals and emits a "
            "phase-1-init Q-Gate finding (recorded against 2-refine) on a mismatch. "
            "Flags two classes — feature-as-bug_fix and non-empty-affected_files with "
            "a null scope_estimate — and NEVER blocks routing. Also runs automatically "
            "as a pre-route pass inside 'planning-lane route'."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(classification_validate_parser)
    classification_validate_parser.set_defaults(func=cmd_classification_validate)

    # sibling-collision-check (deterministic, read-only init-time gate)
    sibling_collision_parser = subparsers.add_parser(
        'sibling-collision-check',
        help='Flag source-origin / file-overlap collisions against active sibling plans (read-only)',
        description=(
            "Init-time semantic sibling-dedup collision gate. Scans every active "
            "(non-archived) sibling plan and flags two collision classes against "
            "the plan under init: (1) source-origin match — the same audit / "
            "lesson / issue source_id backing more than one active plan (a "
            "same-source fan-out), read from each plan's request.md header; and "
            "(2) file-path overlap — concrete file paths named in this plan's "
            "request.md body intersecting a sibling's references.json "
            "affected_files. Deterministic and read-only — no LLM, no writes. "
            "Returns source_origin_matches[] and file_overlap_matches[] plus a "
            "collision_detected boolean; phase-1-init consumes the result and "
            "raises the user gate (proceed / rename / abort) before phase-2."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(sibling_collision_parser)
    sibling_collision_parser.set_defaults(func=cmd_sibling_collision)

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
