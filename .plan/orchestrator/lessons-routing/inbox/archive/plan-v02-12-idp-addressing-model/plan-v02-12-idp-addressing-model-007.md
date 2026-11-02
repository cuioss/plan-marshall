envelope_version=1
sender_type=plan
sender_id=plan-v02-12-idp-addressing-model
epic=lessons-routing
kind=finding
created=2026-10-20T20:30:00Z

# Recurrence: stale worktree executor (0.1.1924) lacked the git-workflow commit verb (plan-marshall:marshall-steward executor staleness / worktree executor provisioning)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492), lessons-capture step.

Recurrence of pending message api-sheriff-api-sheriff-0-2-0-023 ("Executor version skew: workflows call verbs the generated executor does not have").

## Evidence

The `.plan/execute-script.py` in the plan's worktree was generated at 0.1.1924 and did not carry the `commit` verb that the current finalize workflow calls, so the commit step failed until the executor was refreshed. The workflow docs and the executor shipped in the worktree were at different versions, and no staleness probe stopped the run before the first missing-verb call.

## Suggested direction

Probe the worktree executor version against the loaded workflow version at worktree creation (or at phase entry) and regenerate or refuse up front, rather than discovering the skew at the first call to a verb the old executor lacks.
