envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-24T19:59:40Z

# Recurrence: `ci --plan-id` after the plan worktree is removed fails with "Not authenticated" (plan-marshall:tools-integration-ci)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-15-bff-compose-sample (PR cuioss/API-Sheriff#516), inbox message plan-v02-15-bff-compose-sample-001 (landing residue).

Recurrence of the "Not authenticated" symptom of `ci --plan-id` after worktree removal, and of lessons-routing message api-sheriff-api-sheriff-0-2-0-040 (same root: a call whose cwd is the removed worktree). Here it hit the issue-comment step after branch-cleanup. `--project-dir <main checkout>` works. The message names the wrong cause: the session is authenticated, and the cwd is what was deleted.

Suggested direction: as in -040, the ci abstraction should check that its cwd exists and report a missing cwd as such; finalize steps that run after branch-cleanup should run with the main checkout as cwd.
