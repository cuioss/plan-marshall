envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:53Z

# Argparse rejections: `--plan-id` on manage-change-ledger query, flag drift on manage-findings qgate and get-deliverable

**Component:** plan-marshall:manage-change-ledger (`query`), plan-marshall:manage-findings (`qgate`), plan-marshall:manage-solution-outline (`get-deliverable`)
**Category:** anti-pattern
**Source plan:** plan-14-operator-and-question-stores, from plan-retrospective (script-failure-analysis)

## Observation

The plan's script log shows 8 non-zero exits from 4 distinct causes:
- `manage-change-ledger query` was called twice with `--plan-id` ("unrecognized arguments"). The script takes no plan id.
- `manage-findings qgate` was rejected by argparse 3 times, and `manage-solution-outline get-deliverable` once.
- `manage-status transition` exited 1 twice. That is the `execute_commits_unrecorded` refusal already covered by candidate lesson 002, so it is not repeated here.

A leaf also self-reported one `manage-findings list --limit` (undeclared flag). Every failure was recovered, but each cost a retry.

## Suggested corrective action

- For `manage-change-ledger query`: either accept `--plan-id` as a no-op filter that is consistent with the other `manage-*` scripts, or add the verb to the plugin-doctor `ARGUMENT_NAMING_*` guard and show its canonical invocation where workflows call it.
- Have the argparse error for `manage-findings qgate` name the accepted sub-verbs and flags, so the retry needs no guesswork.
