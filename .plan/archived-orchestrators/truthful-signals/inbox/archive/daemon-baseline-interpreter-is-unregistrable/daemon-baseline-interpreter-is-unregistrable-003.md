envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:08:08Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_aspects=execution-context-dispatch-audit,chat-history-analysis

# session capture from a dispatched leaf overwrites the plan's recorded session_id

## Context

`plan-retrospective/SKILL.md` Step 1 instructs the workflow to run `platform_runtime session capture --plan-id {plan_id}` "to capture the runtime session token for downstream metrics". That verb STORES: it writes `status.metadata.session_id`.

But `plan-marshall:plan-retrospective` is a DISPATCHED finalize step. The leaf runs in its own host-platform session, not the plan's. So the call replaces the plan's real session id with the retrospective's.

Measured on this run: before the step, `status.metadata.session_id` was `67673b7e-150b-4d8c-ba7a-bb2ccd91332e` (the id the orchestrator also forwarded to this dispatch as `--session-id`). The capture returned `stored: true` with `session_id: 5244f10e-e982-438f-b766-53ea7a24daf4`, and `manage-status metadata --get --field session_id` now returns the `5244f10e` value. Work-log line `f3c6d0` records the overwrite.

## Root cause

A storing verb whose correctness depends on the caller's session being the plan's session was placed in a workflow that only ever runs inside a dispatched leaf. The verb is right for the orchestrator and wrong here, and nothing in its contract flags the difference.

## Proposed action

Either (a) make Step 1 read-only — the retrospective already receives `--session-id` as an input parameter and does not need to store anything — or (b) give `platform_runtime session capture` a no-clobber mode that refuses to overwrite an existing `session_id` with a different value, and have the leaf use it.

## Impact scope

`record-metrics` takes `session_id` as a caller-passed parameter, so the immediate in-run enrichment is not proven to be affected. The substantiated harm is to the DURABLE record: `status.metadata.session_id` is the only source once the orchestrator's in-context value is gone. That covers cross-session resume, post-archive re-enrichment, and `audit-archived-plan-retrospectives`, all of which would now resolve a transcript containing only the retrospective rather than the plan. Note the retrospective is ordered before `record-metrics` in `phase_6.steps`, so the clobber always lands first.

## Evidence

- `platform_runtime session capture` returned `session_id: 5244f10e-...`, `stored: true`, against `status.metadata.session_id: 67673b7e-...`
- work.log `f3c6d0` — `[MANAGE-STATUS] Metadata: session_id=5244f10e-e982-438f-b766-53ea7a24daf4`
- `execution.toon` `phase_6.steps` orders `plan-marshall:plan-retrospective` before `record-metrics`
- `phase-6-finalize/standards/record-metrics.md:48` — enrich's `session_id` is "passed down from the skill caller"
