envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:09Z

component=plan-marshall:phase-5-execute
category=improvement

# Route the whole-tree pre-commit and exit verify to the orchestrator tier

Source: plan-retrospective of plan-70-plan-instance-alignment (aspects logging-gap-analysis, log-analysis, chat-history-analysis).

## Context

All three `voluntary_checkpoint` boundary rows of 5-execute were forced the same way: the leaf started the whole-tree `verify -Ppre-commit` (envelope 5, fix envelope) or the execute-exit `verify -pl pm-workflow -am` (Step 11c) on its own `per_task` tier with a 300-330 s bound, the build daemon returned `status: running`, and the leaf handed the job id back. The orchestrator then re-attached each time. One full test run also hit the 300 s build timeout and was re-run with `--timeout 900` (about 112 s on retry).

## Root cause

The live tier resolution classifies these sweeps as `per_task` although on this repository they regularly run longer than the leaf's build bound, so the hand-back is the normal path rather than the exception.

## Proposed action

Classify the end-of-execute whole-tree quality gate and the execute-exit verify as `execution_tier: orchestrator` when the recorded duration of the same canonical command exceeds the leaf bound (or always for whole-tree sweeps), so the orchestrator runs them once with the correct timeout instead of a leaf starting them and handing back a running job.

## Evidence

- logging-gap-analysis: 3 of 3 voluntary_checkpoint rows in 5-execute were build hand-backs
- log-analysis: build-maven cumulative 11,448,610 ms over 85 calls, max 355,790 ms
- chat-history-analysis: hand-backs with job ids 7547e4e9, 43127c2c, 892f7018
