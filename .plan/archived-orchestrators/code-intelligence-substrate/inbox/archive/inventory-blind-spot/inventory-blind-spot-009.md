envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:37:08Z

component=plan-marshall:manage-execution-manifest
category=anti-pattern
bundle=plan-marshall
source_plan=inventory-blind-spot

# Manifest compose tests the plan's footprint at plan time, when the footprint is necessarily empty

## Observation — this run

`decision.log` at phase-4-plan, two consecutive lines, one second apart:

```
[c409ae] (manage-execution-manifest:compose) pre-push-quality-gate omitted --
         plan footprint is empty -- no changed files to build
[660085] (manage-execution-manifest:compose) ceremony_finalize selection --
         finalize.qgate=always, added pre-push-quality-gate to phase_6.steps
```

The predicate fired, omitted the step, and was immediately overridden. The plan went on to change **19 files** and `pre-push-quality-gate` ran and was needed.

## Root cause

`compose` runs in phase 4. Phase 5 is where files change. At compose time the plan's footprint is *always* empty — not "empty in this case", but structurally empty for every plan that has ever been composed. The predicate `plan footprint is empty -> omit the build step` therefore evaluates identically for every plan and carries zero information.

It is only harmless here because `finalize.qgate=always` re-adds the step unconditionally one line later. With `finalize.qgate` set to anything conditional, this predicate would omit the pre-push build gate from **every** plan.

## Solution

Either:

- Remove the footprint test from compose entirely — it cannot be meaningful at that phase; or
- Defer it to a step that runs after phase 5, where a real footprint exists, and have compose stamp the step as *conditional* rather than resolving the condition itself.

If the intent was to read a *predicted* footprint (e.g. the union of deliverable `affected_files`), then say so and read that — but then the log line must not claim "plan footprint is empty", because the outline declared 10 affected files at that moment.

## Generalisation

**A guard whose input is not yet populated is a vacuous guard.** The recurrence signature: a predicate over runtime state evaluated during a planning phase. It always takes the same branch, so it is invisible in testing (it never *fails*, it just never *fires meaningfully*), and it is discovered only when a downstream unconditional override is removed.

This is the fourth recorded instance of the vacuous-guard archetype in this repository. The distinguishing question for review: *at the moment this predicate runs, can its input ever be non-empty?* If no, it is not a guard.

## Impact

`manage-execution-manifest:compose`. Any other compose-time predicate reading execution-phase state has the same defect — the log line at `c409ae` is a template for finding them.
