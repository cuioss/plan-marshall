envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:03:41Z

component=plan-marshall:manage-solution-outline
category=improvement
created=2026-08-31
bundle=plan-marshall
confidence=medium
source_plan=git-artifact-scanning-and-destructive-recovery

# Make per-deliverable declared-vs-realized coverage a read, not a hand count

## Context

This plan closed carrying **two incompatible coverage claims for its largest deliverable**, and neither can be derived from the other.

- The run's own self-report: D7 shipped **7 files against 15 declared**.
- The structured derivation — `manage-solution-outline list-deliverables` write-intent bullets intersected with the 21-path realized footprint resolved by `check-outline-vs-shipped` — gives **11 of 19**.

They disagree in both numerator and denominator. The retrospective can reproduce the second figure from artifacts; it cannot reproduce the first from anything. A deliverable whose completion figure is not re-derivable cannot be audited later — which is precisely the failure mode this epic exists to remove, applied to the plan's own reporting.

The same run also carried a third, separately-computed coverage number for the same surface: `check-artifact-consistency` reported `affected_files_recall` at 70.4% with a `missing[8]` list. That list matches the structured derivation's misses exactly, which is corroboration for the 11/19 figure and further isolates the hand count as the outlier.

## Root cause

Deliverable coverage is computed by hand at report time from two sources the run reads separately, so the count is taken at a moment nothing records and by a method nothing pins. Both inputs already exist as structured data with a single producer each: `manage-solution-outline` owns the declared surface with per-bullet intent, and `manage-references` / the shared footprint resolver owns the realized footprint.

## Proposed action

Add a `manage-solution-outline deliverable-coverage --plan-id {id} [--diff-file PATH]` verb that intersects the two and returns one row per deliverable:

```
deliverables[N]{number,declared_mutation,declared_read,realized,coverage_pct,unrealized_paths}
```

with the same read-not-re-derive discipline `manage-metrics generate` already applies to its denominators — including a sampling point, so a coverage figure is anchored to the instant it was taken. Read-intent bullets stay out of the denominator (a path declared read-only can never appear in a diff, so counting it caps achievable coverage by construction), and the verb reports the read count separately rather than dropping it.

Every consumer that today hand-counts — the finalize summary, the PR body, this retrospective's `request_result_alignment` aspect — then reads one producer's answer instead of computing a third one.

## Evidence

- aspect: request_result_alignment — `coverage_accounting_discrepancy`: run self-report 7/15 vs structured 11/19, status `unreconciled`
- aspect: artifact_consistency — `affected_files_recall` 70.4%, `missing[8]`, reached independently and agreeing with the structured derivation
- aspect: outline_vs_shipped — `touched_but_unassessed: 21/21`, `assessments_store_present: false` (no per-file assessments were recorded at outline, so nothing anchors the declaration either)
