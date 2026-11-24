envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:53Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-12-documentation-review-consolidation-007.md`, sender plan `plan-12-documentation-review-consolidation`, created 2026-11-23T20:28:58Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.
>
> Orchestrator note (verified, not only reported): in plugin 0.1.2184 `phase-5-execute/SKILL.md:830` prescribes `--changed-paths-file {worktree_path}/.plan/temp/{plan_id}-changed-paths.nul`, and `manage-change-ledger append --help` declares `--changed-paths` and no `--changed-paths-file`. A second plan of the same epic hit the same drift independently (see the message from plan-15-plan-12-residual-fixes, `-005`, record 3, filed beside this one).

# Candidate lesson: phase-5-execute documents a change-ledger flag the installed executor does not accept

Source signal: script-failure cluster `plan-marshall:phase-5-execute` (signal-scan: one B7 no-progress
reclassification, voluntary_checkpoint -> error), plus five related `[ERROR] (plan-marshall:phase-5-execute)` lines
in the work log.

## Observation

After the per-deliverable commits for TASK-3, TASK-4, TASK-6, TASK-8 and TASK-12, the
`manage-change-ledger append` call failed with exit_code=2. The flag `--changed-paths-file` is not declared by the
installed/worktree executor surface, which accepts only `--changed-paths`. The log entries say so directly:
"SKILL Step 10a documents it; executor surface accepts --changed-paths only" (entries 77c7a6, 39b17e, 6c8509,
81e500, 5e1721). The same drift recurred in every execute dispatch. One of those dispatches also ended in a
no-progress reclassification (voluntary_checkpoint reclassified to error).

## Candidate rule

phase-5-execute SKILL Step 10a and the installed `manage-change-ledger append` argparse surface must agree. Either
ship `--changed-paths-file` in the installed bundle, or change Step 10a to `--changed-paths`. A plugin-doctor
canonical-invocation check over phase-5-execute's Step 10a would catch this drift at edit time.

Component hint: plan-marshall:phase-5-execute and plan-marshall:manage-change-ledger (installed version 0.1.2184).
