envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:36:52Z

component=phase-3-outline
category=anti-pattern
created=2026-07-29

# A plan fixing "end-phase overwrites instead of accumulates" reproduced that exact defect shape during its own run

This plan's whole purpose was fixing phase-boundary end-timestamp writes that REPLACE the prior stamp instead of accumulating onto it (shipped as PR #1059, `fix(manage-metrics): accumulate phase attribution on loop-back`). During its own execution, a 3-outline re-entry — the operator-directed feedback cycle — spent roughly 120k tokens of work AFTER the 3-outline → 4-plan phase boundary had already been stamped once (446k tokens accumulated). Re-stamping the boundary at the end of that re-entry would have OVERWRITTEN the prior 446k-token stamp with only the new 120k, rather than accumulating the two, silently corrupting the very measurement corpus this plan exists to protect — the identical defect shape, recurring inside the plan built to eliminate it.

This is the same recurring archetype already logged repeatedly in project memory: a plan reproducing its own target defect during its own run (see PLAN-86's self-review catching a dropped persist at a call site the plan itself created). It is worth tracking as its own instance because the domain match (accumulate-not-replace, phase-boundary stamping) is exact, not merely structural.

## Impact

Any phase-boundary or checkpoint-stamping write path that is touched by, but not IN SCOPE for, a plan fixing an accumulate-vs-replace defect is a live candidate for the same corruption during that very plan's own execution — the fix and the reproduction can coexist in the same run because the fix lands at finalize while the plan's own mid-flight re-entries happen earlier, before the fix is live.

## Suggested corrective action

When a plan's deliverable is "stop phase X's write path from clobbering prior accumulation," add a self-check late in that plan's own run (self-review or pre-finalize) that inspects whether the plan's OWN phase-boundary stamps (3-outline re-entries, loop-backs, etc.) exhibited the pre-fix replace-not-accumulate behavior during its own execution — not just that the shipped code fixes the general case going forward. Consider whether phase-boundary stamping across the whole plan lifecycle (not just the `manage-metrics` subsystem PR #1059 touched) shares the same underlying write-path pattern and needs the identical fix applied more broadly.
