envelope_version=1
sender_type=plan
sender_id=lb-28-java-consumer-repos
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T23:28:15Z

component=plan-marshall:execute-task
category=bug
bundle=plan-marshall

# Re-resolve the verification timeout live before a leaf runs a long build

## Context

In plan lb-28-java-consumer-repos, a phase-5 leaf started TASK-2's `verify plan-marshall` because the task's stamped limit (370s) looked short enough to run in-leaf. The run was killed at 341s without a result; re-resolving afterwards reported ~777s and orchestrator tier. Later the TASK-9 leaf's independent module-tests re-check also died at 333s. Each kill cost a dispatch handback (4 of the 7 phase-5 dispatches ended `voluntary_checkpoint`) and wall-clock time.

## Root cause

The leaf decided in-leaf versus hand-back from a plan-time `bash_timeout_seconds` snapshot rather than the live adaptive estimate, which had grown well past the leaf's ceiling by execute time.

## Proposed action

Before running any verification command whose duration could exceed the leaf ceiling, execute-task re-resolves the command through `architecture resolve` and uses the live `execution_tier` / `bash_timeout_seconds`; when the live tier is `orchestrator`, hand back without starting the run. Treat the task's stamped value as advisory only, as the manifest's step_execution_tier stamping already declares.

## Evidence

- aspect: chat_history_analysis — "cut off at 341s without a result. Re-checking now says it needs ~777s"; TASK-9 re-run "timed out after 333s with no pass or fail result"
- aspect: logging_gap_analysis — 5-execute voluntary_checkpoint 4/7 (57%), all orchestrator-tier verification handbacks
- aspect: plan_efficiency — 5-execute 1h56m idle of 3h47m wall
