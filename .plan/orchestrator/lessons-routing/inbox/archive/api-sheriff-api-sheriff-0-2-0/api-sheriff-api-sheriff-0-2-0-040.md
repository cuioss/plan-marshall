envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T12:52:16Z

# Candidate lesson: a backgrounded post-merge `ci checks wait` fails with "gh CLI not found" once the plan worktree is removed (plan-marshall:tools-integration-ci / phase-6-finalize branch-cleanup)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-42-validator-auth-oidc-rules (PR cuioss/API-Sheriff#502), source message 006 (landing residue).

RELATED: same root as archived api-sheriff-kidicap-gateway-requirements-012 (a shell pinned to a removed worktree), and as the earlier "Not authenticated" symptom of `ci --plan-id` after worktree removal. Here the failing call was a backgrounded `ci checks wait` started before branch-cleanup.

## What happened

After #502 merged, finalize started a backgrounded post-merge `ci checks wait`, then branch-cleanup removed the plan worktree. The background call's cwd was gone, so it failed with "gh CLI not found". That message names the wrong cause: gh is installed, and the cwd is what was deleted. It did no harm here because the PR had already merged, but the post-merge wait it was meant to do never ran.

## Corrective rule (candidate)

A finalize step that outlives branch-cleanup must not run with the plan worktree as cwd. Run it with the main checkout as cwd (or `--project-dir <main>`), or start it after cleanup. The ci abstraction should check that its cwd exists and report a missing cwd as such, not as a missing gh CLI.
