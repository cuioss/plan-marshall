envelope_version=1
sender_type=plan
sender_id=plan-v02-04-adr-corpus-cleanup
epic=lessons-routing
kind=candidate-lesson
created=2026-10-26T09:56:05Z

# Candidate lesson: a dispatched leaf cannot finish branch-cleanup after integrate_into_main, because its cwd stays pinned to the removed worktree (plan-marshall:phase-6-finalize branch-cleanup)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-04-adr-corpus-cleanup (PR cuioss/API-Sheriff#521, merge f5826465), lessons-capture step.

## Observation

branch-cleanup ran inside a dispatched leaf whose cwd was pinned to the plan worktree. After `integrate_into_main` moved the plan directory back to the main checkout and the worktree was removed, every later script call from the leaf resolved against the deleted worktree path, so the plan no longer resolved. The leaf could not record the remaining cleanup work. The orchestrator had to finish it from the main checkout: worktree removal, branch prune, and the `mark-step-done` with `merge_state=merged`, `cleanup_owed=false`.

## Why it matters

The step's last actions depend on a cwd that the step's own earlier actions remove. Any dispatched driver of branch-cleanup will hit this, and the half-finished state (plan moved, step not recorded) is a resume hazard.

## Suggested direction

- Split branch-cleanup at the move-back point: the leaf returns a "move-back done, finish from main" signal, and the orchestrator runs the tail from the main checkout; or
- have the post-move-back calls resolve the plan main-anchored (git common dir) rather than cwd-relatively, so a leaf with a stale cwd still finds the plan.
