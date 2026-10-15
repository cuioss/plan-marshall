envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:57Z

# Candidate lesson: worktree-remove from a shell pinned to the worktree fails after integrate_into_main move-back (workflow-integration-git)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 024 (orchestrator-observed; the branch-cleanup worktree-remove at 2026-10-15T11:44:45Z itself succeeded).

## Observation

After the integrate_into_main move-back put the plan directory back on the main checkout, a later `git-workflow worktree-remove` from a shell still pinned to the removed or emptied worktree returned `plan_resolution_failed`. This is the same cwd class as the known `ci --plan-id` "Not authenticated" after worktree removal.

## Candidate rule

Every cleanup after move-back (worktree-remove, ci with --plan-id, status reads) runs from the main checkout or passes `--project-dir <main checkout>`. Better: resolve the plan main-anchored, so a stale cwd stops being a failure mode.
