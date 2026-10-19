envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:50Z

# Merge-queue squash takes the PR body as commit message; body must be trimmed before enqueue

**Component (foreign):** plan-marshall:phase-6-finalize (PR creation / merge enqueue step), plan-marshall:tools-integration-ci
**Category:** improvement
**Source plan:** plan-14-operator-and-question-stores (PR #93, squash 3323ce7)

## Observation

With the repository's squash default (PR_TITLE + PR_BODY), the merge-queue squash takes the full PR body as the landed commit message. To keep the landed commit clean, the PR body had to be reduced to the Summary plus the project trailer right before the enqueue, with the full description preserved as a PR comment. This was a manual step.

## Suggested corrective action

- Before enqueueing, read the repository's squash commit message setting; when it is PR_BODY, automatically move the full description to a PR comment and reduce the body to Summary + the configured trailer (e.g. `Co-Authored-By`), or set the merge commit message explicitly where the provider allows it.
- Document the behaviour in the finalize merge step so it is not rediscovered per plan.
