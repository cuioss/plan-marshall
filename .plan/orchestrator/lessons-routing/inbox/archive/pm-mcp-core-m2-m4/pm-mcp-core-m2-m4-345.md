envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:49Z

# Commits without an immediate ledger row make 5-execute completion refuse (execute_commits_unrecorded)

**Component (foreign):** plan-marshall:manage-status (transition gate) / plan-marshall:manage-change-ledger / plan-marshall:phase-5-execute
**Category:** anti-pattern
**Source plan:** plan-14-operator-and-question-stores

## Observation

During execute, commits were made without an immediately following change-ledger append. `manage-status transition --completed 5-execute` then refused three times with `execute_commits_unrecorded`, each time requiring a manual catch-up append before the phase could close.

## Suggested corrective action

- Make the commit path of phase-5-execute (the task commit step) append the ledger row in the same step as the commit, so a commit can never exist without its row.
- Or have the refusal payload carry the exact list of unrecorded shas plus the ready-to-run append invocation for each, so recovery is one pass rather than trial and error.
