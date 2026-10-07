envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:46:12Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=medium
source_plan=plan-truth-148
source_aspects=execution_context_dispatch_audit,script_failure_analysis

# Forward --iteration and a non-empty WORKTREE when dispatching plan-retrospective

## Context

The `plan-marshall:plan-retrospective` dispatch on plan-truth-148 arrived with two prompt-body defects:

- **No `iteration` field.** `plan-retrospective/SKILL.md` states the mode-detection heuristic
  explicitly: "when `--iteration` is present alongside `--plan-id`, treat as finalize-step mode;
  otherwise user-invocable live mode". User-invocable live mode skips the `mark-step-done` handshake.
  Had the heuristic been applied as written, the step would have completed without its handshake and
  left the `phase_steps_complete` invariant unsatisfied — for a step the manifest lists at position 17
  of 23 in `phase_6.steps`.
- **`WORKTREE` empty.** The execution-context contract defines the field as a repo-relative path, with
  the literal `.` denoting the main checkout. An empty string is not a member of that value set. The
  plan's `use_worktree` is `false`, so `.` was the intended value.

Mode was recovered by reading `manifest.phase_6.steps` membership and confirming steps 1-16 were
already complete — evidence the heuristic does not consult.

## Root cause

The dispatcher composes this step's prompt body without the two fields, and nothing fails when it
does. Both are silent: an absent `iteration` degrades into a different mode rather than an error, and
an empty `WORKTREE` passes the dispatcher's presence check because the field is present.

## Proposed action

1. Forward `iteration` on the `plan-marshall:plan-retrospective` dispatch, as the step's own input
   contract declares.
2. Resolve `WORKTREE` to `.` when `use_worktree` is `false`, rather than to the empty string.
3. Consider making mode resolution consult manifest membership rather than flag presence — a step
   listed in `manifest.phase_6.steps` and dispatched by the finalize dispatcher is in finalize-step
   mode regardless of which optional flags survived composition.

## Evidence

- this dispatch's own prompt body: `plan_id=plan-truth-148`, `session_id` present, no `iteration`,
  `WORKTREE=` empty
- `manage-execution-manifest read` — `plan-marshall:plan-retrospective` at position 17 of
  `phase_6.steps[23]`, with steps 1-16 all recorded `done` in `status.metadata.phase_steps`
- `plan-retrospective/SKILL.md` § Mode resolution — the heuristic that would have selected the wrong
  mode
