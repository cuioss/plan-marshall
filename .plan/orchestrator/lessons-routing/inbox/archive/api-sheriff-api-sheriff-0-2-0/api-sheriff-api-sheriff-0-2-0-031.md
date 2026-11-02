envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-18T06:22:30Z

# Candidate lesson: manage-status refused a fabricated head SHA and an execute->finalize transition with unrecorded commits (plan-marshall:manage-status / phase-5-execute change-ledger)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-25-edge-route-decomposition (PR cuioss/API-Sheriff#487), source message 009.

RECURRENCE: the execute_commits_unrecorded half matches api-sheriff-api-sheriff-0-2-0-010 (PLAN-V02-44).


- Source: script-failure cluster, notation plan-marshall:manage-status:manage-status
- Plan: plan-v02-25-edge-route-decomposition (V02-25, edge route decomposition)

### Observation

Two distinct refusals from manage-status in this run:

1. A call carried a fabricated head SHA (not resolved via `git rev-parse HEAD`), and manage-status refused it.
2. The `5-execute -> 6-finalize` transition was refused with `execute_commits_unrecorded`: worktree-branch commits had no `kind=change` change-ledger rows. The transition went through only after the missing change-ledger rows were appended.

### Candidate rule (for orchestrator classification)

- Never type a commit SHA from memory or by pattern. Resolve it with `git -C {worktree} rev-parse HEAD` right before the call that records it.
- Every deliverable commit in phase 5 must be followed by its change-ledger settlement row (Step 10a). Missing rows are found only at the phase transition, when the bookkeeping has to be rebuilt after the fact. The guard did its job, but the gap shows that recording is skipped in practice, either because commits are made outside the task pipeline or because the settlement step is dropped.
