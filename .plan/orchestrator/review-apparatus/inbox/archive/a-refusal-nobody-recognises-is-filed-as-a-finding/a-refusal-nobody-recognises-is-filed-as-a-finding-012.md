envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:25:07Z

component=plan-marshall:plan-retrospective
category=bug
title=compile-report auto-deletes the fragment bundle on success, so acting on its own warning requires rebuilding every fragment

# The cleanup fires before the caller can act on the verdict it is told to act on

## Context

`SKILL.md` Step 4 documents: *"`compile-report run` auto-deletes the fragment bundle after a successful report write."* The same skill's Enforcement section says: *"Never treat a `compile-report` warning as a clean pass. A non-empty `sections_dropped` MUST be surfaced in the report and carried into the Step 5 lessons proposal — a dropped fragment may have carried a live finding."*

During this run the section outcome revealed that Phase Dispatch Boundaries had not rendered despite its data being present. Fixing that required a `collect-fragments add` — and the bundle was already gone:

```
status: error
error: internal_error
message: "Bundle file does not exist: .../work/retro-fragments.toon"
```

Recovering meant re-running `init` plus fifteen `add` calls plus `finalize` plus `compile` — nineteen tool calls to add one fragment.

## Root cause

Cleanup is unconditional on `status: success`, but `success` is also the status returned when sections did not render for a reason the caller is expected to investigate. Retention is currently keyed on the process failing, not on the report being lossy.

## Proposed action

Retain the bundle whenever `sections_dropped` is non-empty OR `sections_omitted` is non-empty — i.e. whenever the caller has something to act on — and delete it only on a fully-written report. Alternatively make deletion an explicit `--cleanup` flag the workflow passes on its final call.

## Note on ordering

Two neighbouring ordering defects are already filed as lessons and both bite this same step: `2026-08-08-20-004` (`record-metrics` runs after `plan-retrospective`, so the efficiency aspect never sees `6-finalize`) and this plan's own observation that `plan-retrospective` runs after `branch-cleanup`, so the footprint resolver has no worktree. The retrospective is scheduled after three producers whose output it needs.

## Evidence

- Observed first-hand this run: the failed `add`, verbatim, and the nineteen-call rebuild
- `SKILL.md` Step 4 "Cleanup" paragraph vs the Enforcement bullet on `sections_dropped`
