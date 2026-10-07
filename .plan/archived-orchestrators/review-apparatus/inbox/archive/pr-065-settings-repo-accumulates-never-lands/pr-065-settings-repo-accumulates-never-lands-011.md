envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:04Z

component=plan-marshall:manage-metrics
category=anti-pattern
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR 255de8 (2026-09-14T16:32:12Z)

# `manage-metrics record-dispatch-boundary` rejected at the loop-back re-entry point

`plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary` was
rejected with `exit_code=2 failure_kind=argparse_rejection`. The echoed usage
shows a verb with four required flags, one of them a wide closed enum:

```text
record-dispatch-boundary --plan-id --phase {1-init..6-finalize}
  --termination-cause {voluntary_checkpoint, task_complete_returned_verbatim,
  budget_yield, harness_cancellation, error, clean_exit_queue_empty,
  step_complete, blocked_user_review, blocked_session_restart,
  task_batch_complete, agent_returned, returned_with_findings, baseline_d...}
```

The rejection landed immediately after the execute-phase re-entry from
loop-back iteration 1 — the exact moment a `--termination-cause` has to be chosen
from a 13+ value enum by an agent describing what just happened in prose.

## Candidate rule

A wide closed enum chosen by an agent from a narrative description is a
high-rejection surface, and the run's own record of *why* an envelope ended is
the thing being lost when the call fails. Worth checking whether the
termination-cause vocabulary can be narrowed, or whether the enum's members can
be named at the call sites that emit each one, so the choice is a lookup rather
than a classification.
