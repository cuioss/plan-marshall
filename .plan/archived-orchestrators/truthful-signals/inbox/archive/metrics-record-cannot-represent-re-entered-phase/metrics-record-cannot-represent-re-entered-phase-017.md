envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=finding
created=2026-08-09T21:30:36Z

# Finding: `plan-retrospective` runs at finalize step 17 and `branch-cleanup` removes the worktree at step 13 — the coverage aspect's footprint source is structurally gone on EVERY plan

**Kind**: finding (structural ordering gap; requires orchestrator scheduling)
**Source**: PLAN-TRUTH-055 post-landing retrospective
**Surface**: `plan-retrospective/scripts/check-artifact-consistency.py`; `phase-6-finalize` step order

## The finding

`check-artifact-consistency` is the **deterministic half of the scope × thoroughness coverage dial** —
the declared-in-scope file list compared against the plan's actual footprint. It resolves that footprint
from the **live worktree** (`{base}...HEAD` ∪ porcelain), falling back only to the legacy
`references.modified_files` key that has since been removed.

This plan's `execution.toon` phase_6 order:

```text
index 13: branch-cleanup                         (facts: "worktree removed")
...
index 17: plan-marshall:plan-retrospective
```

By the time the aspect runs, both of its sources are gone. It reported:

```text
affected_files_recall,inconclusive,"Plan footprint could not be resolved
  (no live worktree diff and no modified_files key) — recall is unmeasurable, not 0%"
affected_files_exact_match,inconclusive,...
details: footprint_resolved: false
```

**The aspect's own behaviour is correct and is not the finding.** It graded `inconclusive` with the
reason named, rather than reporting 0% recall — declining to manufacture a verdict from an absent
input. That is exactly the honest-signal design this epic exists to install, working.

The finding is that this is **structural, not occasional**: under the current step order the aspect can
*never* resolve a footprint, on any plan. The coverage dial's deterministic half is permanently dark,
and the report shows two `inconclusive` rows every time — which reads as a per-plan data hiccup rather
than as a capability that has been switched off.

## The footprint is trivially recoverable

This retrospective recovered it in **one git call** against the merged squash commit:

| Quantity | Value |
|----------|-------|
| Declared (`references.affected_files`) | 34 |
| Achieved (merged squash `2586ef00c`) | 25 |
| In both | 23 |
| Recall (achieved ∩ declared / achieved) | **92%** (23/25) |
| Precision (∩ / declared) | **68%** (23/34) |

Everything needed is already on the record before step 17: `status.metadata` carries the PR number,
`branch-cleanup` records `merge_mechanism: merge_queue` and its own completion, and the landing commit
is reachable on `main`.

## Proposed remedy

Add the **merged landing commit** as a third footprint-resolution source, after the live worktree diff
and before giving up. Ordering:

1. live worktree diff (unchanged — correct when a worktree exists)
2. merged landing commit (new)
3. legacy `references.modified_files` (archived plans only)
4. `inconclusive` (unchanged — still the right answer when none resolves)

## Explicitly NOT a re-ordering request

`PLAN-TRUTH-050` owns the finalize ORDERING that makes the retrospective read state early. **Cite, do
not merge** — this gap is fixable without moving a single step, by giving the aspect a source that
survives step 13. Re-ordering would fix it too, but it is the larger, riskier change and this does not
depend on it.

## Secondary observation

The two `inconclusive` rows are the *only* signal that the comparison did not happen. There is no
report-level statement distinguishing "this plan's coverage was not measurable" from "coverage is not
measurable on any plan under the current configuration" — the second is a capability report and belongs
somewhere a reader will see it once, rather than as a per-plan row they learn to skip.
