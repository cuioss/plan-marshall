envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:19Z

component=plan-marshall:manage-metrics
category=anti-pattern
title=record-dispatch-boundary --termination-cause: a free word such as completed is rejected, map the envelope return to the closed enum by a table
source_lesson=2026-11-19-14-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# record-dispatch-boundary --termination-cause: a free word such as completed is rejected, map the envelope return to the closed enum by a table

# Candidate lesson: `manage-metrics record-dispatch-boundary --termination-cause completed` is not in the closed vocabulary

- Source signal: plan git-core-incore-write-cas (inbox git-core-incore-write-cas-012), script_failure cluster `plan-marshall:manage-metrics:manage-metrics`, argparse rejection, exit code 2.
- Evidence: work-log line 255de8 / script-log line c25591, 2026-11-19T09:31:25Z, in the orchestrator context right after the phase-5-execute envelope returned with all 9 tasks done. The retry three seconds later (script-log 4200fa) succeeded.

## What happened

```
manage-metrics record-dispatch-boundary --plan-id git-core-incore-write-cas --phase 5-execute \
  --termination-cause completed --total-tokens 377854 --tool-uses 195 --duration-ms 1100039
```

`completed` is not a member of the closed `--termination-cause` vocabulary (`voluntary_checkpoint`, `task_complete_returned_verbatim`, `budget_yield`, `harness_cancellation`, `error`, `clean_exit_queue_empty`, `step_complete`, `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned`, `returned_with_findings`, ...). The intended value for an execute envelope whose task queue drained is `clean_exit_queue_empty`; the plan's own signal scan recorded exactly that cause twice.

## Candidate rule

A value paraphrase of a closed enum: the orchestrator step that records a dispatch boundary after an execute envelope writes a free word that reads naturally. The recording step should map the envelope's return to the enum through a table in the workflow prose (queue drained -> `clean_exit_queue_empty`, one step done -> `step_complete`, findings returned -> `returned_with_findings`, ...) and quote the flag value verbatim, instead of leaving the choice to narrative. Same family as the invented verb (`qgate query`), the shortened flag (`--number`) and the rejected flag (`--limit`) lessons: the agent paraphrases a surface it has not read.
