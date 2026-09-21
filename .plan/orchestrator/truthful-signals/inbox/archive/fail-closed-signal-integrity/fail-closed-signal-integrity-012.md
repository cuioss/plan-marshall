envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T22:07:18Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Retrospective inputs report confidently wrong values after worktree teardown and phase close

The retrospective runs at finalize order 17 — **after** `branch-cleanup` has removed the worktree
and **before** `record-metrics` has closed the 6-finalize phase row. Two of its deterministic
inputs read that torn-down state as data rather than as absence, and publish a confident wrong
number.

## Instance 1 — declared-vs-achieved coverage reports 0% recall; the truth is 100%

`check-artifact-consistency` emitted:

```
affected_files_recall, fail, "Recall 0% below 70% threshold"
details.affected_files_recall: declared 18, found 0, recall_pct 0.0
```

and listed all 18 declared files as `missing`.

Every one of those 18 files is in the merge commit `b713fe4b9`. Real recall is **100%**. The
aspect derives the footprint live from the plan's worktree; the worktree was removed by
`branch-cleanup` two steps earlier, so the derivation returned an empty set — and an empty
footprint was rendered as a **graded failure** rather than as an unavailable measurement.

This is the exact inversion of a false green and it is just as bad: the coverage aspect that
grades thoroughness to the floor put a `fail` on the report against a plan that achieved full
declared coverage. A reader acting on it would chase a coverage gap that does not exist.

## Instance 2 — `metrics.md` under-states the plan by 49%

`metrics.md` reports `total_tokens 2,782,409` with `> Partial: unrecorded phases — 6-finalize`
and a blank 6-finalize row. `work/metrics-accumulator-6-finalize.toon` — present on disk, written
by the same subsystem — already holds `total_tokens: 2686561, samples: 16, tool_uses: 612`.

The plan's real spend is ≈ **5,468,970 tokens**. The published artifact shows 51% of it. The
partiality marker is honest about the mechanism but the headline number is the one that gets
quoted, and 6-finalize is not a rounding error here — it is the single largest phase, larger than
5-execute by 2.2:1.

## Shared root cause

Both are the same shape: an input that is *absent because of where in the finalize order the
reader sits* is consumed as though it were a measured value. Neither reader asks "is this state
readable right now?" before grading it.

## Solution

1. **`check-artifact-consistency`**: when no worktree is on disk, fall back to the merged commit
   range (`references.pr_url` / the squash commit already recorded in the branch-cleanup step
   detail). If neither is resolvable, emit `status: indeterminate` for the recall check — never a
   `0%` grade derived from an empty set.
2. **`manage-metrics generate`**: when a phase row lacks `end_time` but a
   `metrics-accumulator-{phase}.toon` exists, fold the accumulator in as a **provisional** figure
   with an explicit marker, instead of rendering the phase blank. A provisional 2.69M is far
   closer to the truth than a blank, and the marker keeps it honest.
3. Consider whether the retrospective should simply run before `branch-cleanup`. Its two broken
   inputs are both worktree- and phase-state-dependent, and everything it produces is read-only.
