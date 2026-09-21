envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:57:58Z

component=plan-marshall:plan-retrospective
category=bug
title=Script-failure cluster 6/6 — collect-fragments failed on a missing bundle file and the retrospective completed anyway
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=script-failure cluster, notation plan-marshall:plan-retrospective:collect-fragments

# Script-failure cluster 6/6 — collect-fragments failed on a missing bundle file and the retrospective completed anyway

## Observation

```text
2026-08-08T18:34:52Z ERROR [ERROR] (plan-marshall:execute-script:1) script_failure
  notation=plan-marshall:plan-retrospective:collect-fragments
  exit_code=1 failure_kind=script_internal_failure
  detail=Bundle file does not exist:
    .plan/local/plans/a-rule-that-is-green-because-it-examined-nothing/work/retro-fragments.toon
```

Eight minutes later the same dispatch reported `[STATUS] (plan-marshall:execution-context.plan-retrospective) Complete`, and the step recorded `outcome: done` with `display_detail: 8 candidate-lesson(s) -> epic truthful-signals`.

## Root cause

The fragment-collection seam failed with a missing input, and the retrospective's terminal record carries no trace of it. `phase_steps` stores one outcome per step, so a step that errored on an internal call and then completed by another route reports the same `done` as a step that had no error at all.

Two separable problems:

1. **The input contract.** `collect-fragments` requires `work/retro-fragments.toon` to pre-exist; nothing in the run had created it. Whether that is a missing producer or a missing "create-on-first-use" branch, the consumer's failure is the first and only place it surfaces.
2. **The outcome contract.** An errored internal call inside a step that otherwise completes leaves no residue in the step record. The error is recoverable only by reading `work.log` and correlating timestamps against the dispatch window — which is exactly the correlation a `done` record discourages anyone from doing.

## Why this belongs to `truthful-signals`

Canonical instance of the epic's theme at the step boundary: **`outcome: done` with a real internal failure inside the window.** The step's own display detail (`8 candidate-lesson(s)`) is accurate and reassuring, and neither it nor the outcome carries the fact that a collection seam returned exit 1.

A sibling candidate already in this epic's inbox (message `…-007`, *"phase_steps is last-write-wins and erases errored attempts a sibling store recorded"*) names the storage half of this. This message adds the consumer-side instance: the erased attempt here was a script failure, not a re-fired step.

## Proposed action

- Fix the input contract so `collect-fragments` either creates its bundle file or reports a distinguishable `no_fragments` status rather than a generic exit-1 `script_internal_failure`. "The file I read does not exist" and "there were no fragments" are different answers.
- Carry an `errors_seen` / `internal_failures` count on the step record so a `done` outcome that contained a failed call is distinguishable from a clean one, without requiring log correlation.

## Evidence

- Work log entry `e34938`, 2026-08-08T18:34:52Z; retrospective completion `f4d02d` at 18:42:34; step completion `b8e62a` at 18:43:38.
- `status.metadata.phase_steps['6-finalize']['plan-marshall:plan-retrospective'] = {outcome: done, display_detail: "8 candidate-lesson(s) -> epic truthful-signals"}` — no failure residue.
