envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:54Z

# Candidate lesson: a throwaway branch had no deletion owner on early-return paths (phase-4-plan)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 018 (Q-Gate 5b9cc9).

## Observation

The outline gave deletion of diag/plan-32-main to D4, but on TASK-2's blocked/STOP returns D4 never runs. The fix was patched into the dispatch prompt: keep the branch on every return, report its name and head SHA, and the orchestrator deletes it if D4 never runs.

## Candidate rule

A task that creates a throwaway branch, worktree or CI run states its disposition on every return path, early ones included, and reports name and head SHA in its return payload. "A later deliverable deletes it" holds only if that deliverable is guaranteed to run.
