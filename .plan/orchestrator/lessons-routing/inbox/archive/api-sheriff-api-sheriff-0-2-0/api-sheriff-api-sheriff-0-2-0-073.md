envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-30T05:35:58Z

# Candidate lesson: nothing checks CI-provider authentication before dispatching a task whose steps call the CI router, so the leaf discovers "Not authenticated" at step 1 (plan-marshall:tools-integration-ci router auth preflight / phase-5-execute dispatch)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-51-lane-conditional-guards (PR cuioss/API-Sheriff#538), inbox message plan-v02-51-lane-conditional-guards-004.

RELATED: lessons-routing api-sheriff-api-sheriff-0-2-0-040 and -061 (`ci --plan-id` after the plan worktree is removed fails with "Not authenticated"). That cause was a deleted worktree cwd. This occurrence happened with a LIVE worktree and `ci_health` reporting `gh authenticated=false`, so it is a genuine credential outage, not the cwd artefact.

- TASK-8 (the fix for functional-review finding a2475c: close issue 201 with the nine run counts) began with `ci issue view --issue 201`. The call returned `status: error 'Not authenticated'`. The task stopped as its instructions required: nothing was posted and the issue stayed open.
- The plan then waited about 40 minutes (2026-10-29 13:05 to 13:46) until credentials were restored. On re-dispatch the comment was posted and the issue closed (decision log 554749, 13:48:28Z). The orchestrator verified #201 `CLOSED` at 13:48:16Z.
- The task's need for the CI provider was knowable before dispatch. Nothing checked it, so the failure surfaced inside the leaf after the dispatch cost was paid.

Suggested direction (the plan's): when a fix or implementation task's steps call the CI router (issue or PR read or write), check `ci_health` authentication before dispatching that envelope; if auth is down, surface the blocker to the operator (`gh auth login`) before dispatch.

Evidence: decision log c2f889 (TASK-8 stop, 2026-10-29T13:05:29Z) and 554749 (re-dispatch success); Q-Gate finding a2475c, in plan-v02-51-lane-conditional-guards.
