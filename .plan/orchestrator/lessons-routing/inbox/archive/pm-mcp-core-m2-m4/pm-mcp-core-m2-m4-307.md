envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:39Z

# Candidate lesson: 5-execute transition refused - 2 branch commits had no change-ledger row

Source: script-failure cluster plan-marshall:manage-status:manage-status (1 occurrence, 2026-10-18T00:23:24Z)
Component (suggested): plan-marshall:phase-5-execute Step 10a settlement / manage-change-ledger (foreign bundle - route to plan-marshall lessons inbox)

## What happened

`transition --plan-id plan-69-unit-frontmatter-and-types --completed 5-execute`
-> exit 1, `error: execute_commits_unrecorded`:

- unrecorded_commits: eb9f30ef2dbf3fd0dca6dcc6741ada2b308eecea,
  485cfb3a2cbf837d5cac1d714f1561a5622c8be1
- branch_commit_count 11, recorded_count 9
- message: "Run the phase-5-execute Step 10a settlement bookkeeping for the
  unrecorded commits, then retry the transition."

The orchestrator appended two `manage-change-ledger` rows (00:23:37Z,
00:23:38Z) and the retried transition succeeded at 00:23:53Z.

## Candidate rule

The guard worked as designed; the lesson is upstream: two commits during
phase 5 were made without the per-commit settlement bookkeeping (Step 10a). Find
which execute path commits without appending the `kind=change` ledger row
(likely a verification/fix commit outside the per-task loop) and make that path
record its row at commit time instead of at the transition guard.
