envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T09:51:34Z
lifecycle=superseded
superseded_by=dual-homed-hook-install-renders-identically-013.md

component=plan-marshall:plan-marshall
category=bug
confidence=medium
source_plan=dual-homed-hook-install-renders-identically
source_aspects=chat_history_analysis,logging_gap_analysis

# Orchestrator halted mid-finalize with no logged reason under finalize_without_asking

## Context

The session transcript for this plan carries 1,523 raw turns and exactly 4 operator-authored ones. One of those four is:

```
why did you stop? Continue to the end
```

The run was configured `execute_without_asking=true` and `finalize_without_asking=true`, and decision.log records both as auto-continue decisions. The orchestrator nonetheless stopped with finalize work outstanding and needed an operator to restart it.

The stop is invisible to the plan's own record. There is no `[BLOCKED]` line, no `escalate_ask` return, no `[STATUS]` entry, and no dispatch-boundary row marking a halt. The cause is unrecoverable from the artifacts — which is why this is filed at `medium` rather than `high`: the *event* is certain, the *mechanism* is not.

## Root cause

Unknown from the record, and that is itself the finding. The orchestrator's stop conditions that ARE logged (`escalate_ask`, `[BLOCKED]`, `voluntary_checkpoint`, `budget_yield`) all leave a trace; this one left none, so it is either an unlogged stop condition or a harness-level halt the orchestrator never observed.

## Proposed action

Give the orchestrator a terminal marker it writes before returning control mid-phase, carrying the reason and the next intended step, so any halt that is not one of the four logged conditions is distinguishable from those that are. A halt with no marker should then itself be detectable at retrospective time by comparing the last logged step against the manifest's remaining steps.

## Evidence

- Session transcript (reduced), operator turn: "why did you stop? Continue to the end"
- decision.log 2026-09-02T16:19:33Z — `Config: execute_without_asking=true`
- decision.log 2026-09-02T17:20:40Z — `Config: finalize_without_asking=true — auto-continuing to finalize`
- work.log: 493 entries, no `[BLOCKED]` line in `6-finalize` and no `escalate_ask` return other than the `automatic-review` re-review one at 06:17:29Z, which the orchestrator resolved without stopping
- aspect: chat_history_analysis — `operator_turn_count: 4` of `raw_turn_count: 1523`
