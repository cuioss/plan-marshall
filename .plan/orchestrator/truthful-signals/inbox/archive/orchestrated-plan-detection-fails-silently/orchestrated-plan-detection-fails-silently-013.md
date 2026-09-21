envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:18:04Z

component=plan-marshall:plan-retrospective
category=improvement
bundle=plan-marshall

# The execution-context dispatch audit emits zero-valued category counts for categories it never evaluated

## What happened

Aspect 11's declared output schema is:

```
counts:
  by_category:
    shape_violation: N
    envelope_violation: N
    generic_subagent_violation: N
    dispatch_coverage_violation: N
```

On PLAN-114, run inside a dispatched `execution-context` envelope, **two of those four numbers cannot honestly be zero**:

**`dispatch_coverage_violation` — not evaluable in this envelope.** The check requires Surface D, the dispatched/inline roster in `phase-6-finalize/SKILL.md` § "Dispatched workflows vs inline steps". The retrospective envelope was not granted the `Grep` tool, and Bash `grep`/`find` is blocked by the project's file-operation hard rule, so the section could not be located inside a multi-thousand-line SKILL.md. Eight finalize steps reached `outcome=done` with no `[DISPATCH]` evidence; most are plainly inline by construction, but `project:finalize-step-era-stamp-fill` is a project SKILL.md-bodied step of the same shape as three steps that *were* dispatched, and remains unresolved.

**`shape_violation` — vacuous on this plan.** The check pairs `decision.log` `effort resolve-target` entries against `work.log` `[DISPATCH]` lines. This plan's `decision.log` contains **zero** `effort resolve-target` entries. With an empty left side, the pairing cannot fail. A reported `shape_violation: 0` here means "there were no resolve records to orphan", not "every resolve was paired" — the always-passes pole of the vacuous-guard family this project already tracks.

Meanwhile the two checks that *were* genuinely evaluable both passed cleanly: 15 of 15 dispatches rode canonical `execution-context-{level}` envelopes, and no `Task: general-purpose` text appears anywhere.

## Root cause

The schema has one representation — an integer — for three distinct states: *checked, none found*; *checked, but the predicate had nothing to range over*; and *not checked*. Emitting `0` for all three is the defect.

## Corrective rule

1. **Add a `not_assessed` / `not_applicable` state to `by_category`**, and require the aspect to use it when a required input surface is unavailable. An aspect that cannot run a check must say so in the same structure the check's result would occupy.
2. **Report the pairing population.** `shape_violation` must emit the count of `effort resolve-target` records it ranged over. A zero-population pass is reported as `vacuous`, not as `0`.
3. **Give the audit a tool-independent path to Surface D.** The roster is a fixed section of a fixed file; expose it via a small deterministic script (`dispatch-roster list`) rather than requiring the LLM to content-search a large markdown body. This also removes the aspect's dependence on which tools the harness happened to grant the envelope.

## Corroborating observation

The same aspect's primary evidence stream is itself slightly unreliable on this run: the `[DISPATCH]` line for `pre-submission-self-review` was emitted **twice** (14:59:12 and 15:01:29) with an identical message hash, straddling the 15:01:20 candidate-count gate decision. Fifteen lines, fourteen distinct events. A duplicated emission inflates the count; the same weakness would equally mask a missing one.

## Why it matters for truthful signals

A reader seeing four zeros concludes dispatch discipline was fully audited and fully clean. Two of the four were never meaningfully tested. **A count of zero must never be the way an aspect says "I did not look."**

## Evidence

- 15 `[DISPATCH]` lines in `work.log`, all `execution-context-level-3` / `-level-4`
- `decision.log` — zero `effort resolve-target` entries across 61 decision records
- `work.log` lines 141-142 — duplicate `[DISPATCH]`, identical hash `9929e8`
- `status.metadata.phase_steps["6-finalize"]` — 8 steps `outcome=done` with no matching `[DISPATCH]`
