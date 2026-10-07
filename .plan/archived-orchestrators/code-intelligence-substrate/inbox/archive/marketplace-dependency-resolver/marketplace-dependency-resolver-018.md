envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:19:07Z

component=plan-marshall:manage-metrics
category=bug
title=Give the per-dispatch context-load columns a producer or an absent sentinel

# Give the per-dispatch context-load columns a producer or an absent sentinel

## Context

Across three phases and 14 recorded dispatch boundaries, every row reads:

```
input_tokens=0, output_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=0
```

- `4-plan` — 1 row, all four zero
- `5-execute` — 5 rows, all four zero
- `6-finalize` — 8 rows, all four zero

The four flags are declared `default 0` in argparse. A row where the caller
passed nothing is therefore **byte-identical** to a row where the caller measured
genuine zeroes. Not one call site populated them, and the schema makes that
absence unobservable.

Two related accounting problems surfaced in the same data:

1. **Producer disagreement.** `6-finalize` has 8 dispatch-boundary rows but the
   accumulator for the same phase recorded `samples: 12`. Two producers of the
   same per-dispatch fact disagree by 4 within one phase.
2. **Truncated phase.** The accumulator's last write is 20:06:13Z; the phase ran
   to 22:47:46Z. The final 2h41m — loop-back verification, merge-lock waits,
   rebase conflict resolution, the merge itself, branch cleanup — contributed
   zero recorded tokens. Every `6-finalize` figure is a floor, and the report
   must say so.

## Root cause

The columns were added to the schema and to the argparse surface, with a
zero-default, but no dispatch site was updated to pass them. A zero-default on a
never-populated column is the worst of both worlds: the data looks complete and
reads as a legitimate measurement.

The accumulator/boundary divergence and the truncated tail have a common shape —
recording is attached to individual call sites rather than to the phase
boundary, so any path that ends the phase without passing through those sites
silently drops its accounting.

## Proposed action

1. Either populate the four columns at every `record-dispatch-boundary` call
   site, or change their default from `0` to an explicit absent sentinel so a
   consumer can distinguish not-measured from measured-zero.
2. Add a consistency assertion between `metrics-accumulator-{phase}.toon`
   `samples` and the row count of `metrics-dispatch-boundaries-{phase}.toon`;
   a divergence is a recording defect, not a benign difference.
3. Fold the accumulator at phase close rather than at call sites, so a phase that
   ends via loop-back / merge / cleanup still lands its tail.
4. Documentation: `manage-metrics` SKILL.md documents a 6-value
   `--termination-cause` enum in both its Operations section and its Canonical
   invocations block, while the implemented enum has 11 values (adds
   `step_complete`, `blocked_user_review`, `blocked_session_restart`,
   `task_batch_complete`, `agent_returned`). This run legitimately used two of
   the five undocumented values, so a reader auditing the rows against the doc
   would wrongly conclude the data is corrupt. Reconcile the doc to the
   implementation.

## Evidence

- aspect: log_analysis — the `dispatch_boundaries` block, all 14 rows, four
  trailing zero columns.
- `work/metrics-accumulator-6-finalize.toon` — `samples: 12`,
  `updated: 2026-08-01T20:06:13Z`.
- status.json — `branch-cleanup` completes at 22:47:47Z, 2h41m after the last
  accumulator write.
- `manage-metrics record-dispatch-boundary --help` — the 11-value enum, versus
  the 6-value list in SKILL.md.
