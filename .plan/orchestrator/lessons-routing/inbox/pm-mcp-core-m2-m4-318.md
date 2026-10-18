envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:32Z

component=plan-marshall:manage-tasks
category=bug
source=script-failure cluster, work log a94f02 + a6c82b (2026-10-17T16:59:50Z, TASK-14) and a94f02 + dcf136 (2026-10-18T06:44:44Z, TASK-29)

# `finalize-step --verification-owed` is not declared but recurs across phase-5 dispatches

## Observation

Two separate phase-5-execute dispatches, about 14 hours apart, called `manage-tasks finalize-step --task-number N --step S --outcome done --verification-owed`. Both were rejected because `--verification-owed` is not declared. The declared flags are outcome, outcome-caller, outcome-step-count, outcome-task-title, plan-id, reason, step and task-number. In both cases the agent then completed the task some other way.

## Hypothesis

Two dispatches emitting the same undeclared flag points to a source document (execute-task / phase-5-execute workflow) prescribing it, not agent invention. That fits a newer workflow running against a stale executor-mapped script, or a doc that leads the script. Check the workflow text against the live argparse. If the flag is meant to exist, the executor in this repository is stale (see the stale-executor candidate).
