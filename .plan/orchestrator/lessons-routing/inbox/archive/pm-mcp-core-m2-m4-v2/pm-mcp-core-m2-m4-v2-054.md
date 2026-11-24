envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T16:19:56Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-11-21
bundle=plan-marshall
title=Stop execute leaves from starting builds the host will background after 180 s

# Stop execute leaves from starting builds the host will background after 180 s


## Context

In plan-v2-25 the execute phase took five dispatches that each ended `verification_handback`. The leaves reported that "the harness moved every build that ran longer than 180 s (queue time included) into the background", although each Bash call carried a 600000 ms timeout and the live resolve said `per_task`. A backgrounded build cannot be collected by a leaf, so each envelope returned with a `running` daemon job and the orchestrator re-entered phase 5 four times. 5-execute shows 1h2m idle of 2h10m wall; maven calls own 77.7% of script time (76 calls).

## Root cause

The `per_task` tier is chosen from `bash_timeout_seconds` against the 600 s ceiling, but the effective leaf limit is the host's 180 s auto-background threshold plus the build-server queue wait, so builds resolved as runnable inside the leaf are not.

## Proposed action

Resolve the execution tier against the host's real auto-background threshold (including expected queue time) so builds longer than that go to the orchestrator tier up front, or have the leaf submit to the build server and return the job id immediately instead of a blocking call that is then backgrounded.

## Evidence

- aspect: chat_history_analysis — four phase-5 hand-backs citing background moves and `status: running` jobs
- aspect: log_analysis dispatch_boundaries — 5 `verification_handback` rows in 5-execute; script_cost_rollup maven 11562 s cumulative
- aspect: plan_efficiency — 5-execute idle 1h2m; worked_seconds_per_task 1196
