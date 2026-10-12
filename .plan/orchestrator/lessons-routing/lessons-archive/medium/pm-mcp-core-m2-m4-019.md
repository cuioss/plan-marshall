envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:06Z

# Candidate lesson: per-module build commands could not run inside a task until first measured, costing two extra hand-offs

- Component: plan-marshall:phase-5-execute
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-08-003 (created 2026-10-10), epic pm-mcp-core-m2-m4

Source: run observation, not a finding record. Verified against the logs.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.

## Evidence

- Decision log `8e37b0` (2026-10-09T22:05:58Z): "voluntary_checkpoint: TASK-1 steps 1-4 done, step 5 edited but not finalized; per-task quality-gate for pm-core resolved live to execution_tier=orchestrator (unmeasured) — not in the leaf's runnable slice, yielding to the orchestrator".
- Work log `714242` (22:18:03Z): "per-task verify for pm-core resolves live to orchestrator tier (unmeasured) — yielding it to the orchestrator: maven run --plan-id workspace-confinement --command-args \"verify -pl pm-core -am\"".
- Work log `aadd52` (2026-10-10T06:26:31Z): "TASK-8 quality gate (verify -Ppre-commit), live tier per_task" — after measurement the same kind of command ran inside the task.
- Decision log `a42adf`: at plan time the snapshot stamped `verify:quality-gate=orchestrator`, `verify:module-tests=per_task`.

## What happened

A build command with no recorded duration is treated as too long to run inside a task. In this repository that applied to the quality gate for `pm-core` and then to the plain verify for `pm-core`, one after the other. Each time the task stopped, the main session ran the build, and the execute phase was handed off again (dispatches at 22:08Z and 22:20Z). The measured durations in the log were between about 30 seconds and 3.5 minutes.

## Why it may be a lesson

Each distinct module-scoped command pays this cost once, separately. A project with several modules and several command shapes (compile, test, verify, verify with the pre-commit profile, each per module) repeats it for every first use. Later plans of this repository benefit only for the exact commands this run measured.

Classification is left to the pickup.
