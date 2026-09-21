envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:17:49Z

# Finalize dispatcher does not forward --iteration to plan-retrospective

component: plan-marshall:phase-6-finalize
category: bug
confidence: high

## Context

`plan-retrospective/SKILL.md` resolves its execution mode with this heuristic:

> Mode detection heuristic: when `--iteration` is present alongside `--plan-id`, treat as finalize-step
> mode; otherwise user-invocable live mode.

Mode selection is load-bearing: **only** finalize-step mode emits the `mark-step-done` tail, and
user-invocable mode is explicitly forbidden from emitting it.

The actual finalize dispatch (work.log:351) was:

```
[DISPATCH] (plan-marshall:phase-6-finalize) target=execution-context-level-5 level=level-5
role=post-run-review workflow=plan-marshall:plan-retrospective/SKILL.md plan_id=barrier-override-not-head-bound
```

and the prompt body carried `name`, `plan_id`, `skills[]`, `workflow`, `WORKTREE`, `session_id`,
`orchestrated`, `epic` — and no `iteration`. Following the documented heuristic literally selects
**user-invocable live mode**, which skips `mark-step-done`, which leaves
`phase_steps["6-finalize"]["plan-marshall:plan-retrospective"]` unwritten and breaks the
`phase_steps_complete` invariant at `archive-plan`.

This run recovered only by ignoring the heuristic and reading `execution.toon`, finding
`plan-marshall:plan-retrospective` declared at `phase_6.steps[16]` with no `phase_steps` record.

## Root cause

Two components disagree about the mode signal. `phase-6-finalize` does not forward `--iteration`;
`plan-retrospective` treats its absence as proof of a different caller. The heuristic infers the caller
from an optional field rather than from an authoritative one.

## Proposed action

Preferred: stop inferring. Resolve mode from the execution manifest — if `plan-marshall:plan-retrospective`
appears in `phase_6.steps` and has no terminal `phase_steps` record, this is the finalize-step dispatch.
That signal is authoritative and cannot be dropped by a caller.

Minimum: have `phase-6-finalize` forward `--iteration` on the plan-retrospective dispatch, and have
`plan-retrospective` treat a missing `--iteration` as an error rather than as a silent mode switch.

## Evidence

- work.log:351 — the finalize `[DISPATCH]` line, carrying no iteration
- The dispatch prompt body for this envelope — no `iteration` field
- plan-retrospective/SKILL.md § Input Contract "Mode resolution" and § Step 6 "Mode-Specific Termination"
- execution.toon `phase_6.steps[16]` — the authoritative signal that was used instead
