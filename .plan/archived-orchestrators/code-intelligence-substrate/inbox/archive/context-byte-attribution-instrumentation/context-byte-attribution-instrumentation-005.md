envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:42:16Z

# Stop plan-retrospective clobbering the plan's execution session_id

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_plan: context-byte-attribution-instrumentation
source_pr: 1086

## Context

`plan-retrospective/SKILL.md` Step 1 instructs the workflow to run:

```
platform_runtime session capture --plan-id {plan_id}
```

`session capture` reads the **current** session and stores it to `status.metadata.session_id`. When
the retrospective runs, the current session is the *retrospective's* session — not the session the
plan actually executed in.

Observed directly on this run: `status.metadata.session_id` was `9c9328ba` (stamped mid-phase-5 at
08:51:57, the real execution session). Step 1's `session capture` returned and stored
`2bd1b4d5` — the retrospective's own session. `work.log` line 380 records the overwrite at 16:28:44,
one line before the retrospective's own start marker.

## Root cause

`session capture` is a write, not a read, and it is unconditional. Step 1 wants the session token
"for downstream metrics", but the operation it invokes has the side effect of *replacing* the very
value downstream metrics need. The retrospective is the last consumer to run, so it destroys the
provenance immediately before the consumer that needs it (`record-metrics` runs after
`plan-retrospective` in the manifest).

The damage is silent: nothing errors, and the resulting `metrics.toon` would attribute the plan's
phases against a transcript that contains only the retrospective.

## Proposed action

Step 1 should **read** the stored session, not capture a new one — or `session capture` should append
to a `session_ids` list rather than overwrite the scalar (see the companion proposal on multi-session
enrichment; the two fixes compose).

Minimum fix: make the retrospective's Step 1 call read-only when a session id is already stored, and
capture only when the field is empty.

## Evidence

- aspect: execution_context_dispatch_audit — `session capture` at retrospective Step 1 returned `2bd1b4d5`, overwriting the stored `9c9328ba`
- `work.log` line 380: `[MANAGE-STATUS] Metadata: session_id=2bd1b4d5-...` at 16:28:44, immediately before the retrospective's own `[STATUS] Starting retrospective` line at 16:28:57
- The orchestrator's dispatch prompt carried `session_id: 9c9328ba`, so the correct value was known and available at dispatch time
