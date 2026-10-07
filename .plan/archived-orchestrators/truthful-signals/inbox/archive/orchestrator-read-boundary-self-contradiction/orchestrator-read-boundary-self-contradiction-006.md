envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:43:59Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-28
bundle=plan-marshall

# A footprint read outside the window in which the footprint exists reports 0 as a finding, not as unknown

## What happened

Two independent instances in a single run of PR #1040, same shape.

**Instance 1 — the retrospective's own recall check.** `check-artifact-consistency`
reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 7   found: 0   recall_pct: 0.0
  missing[7]: <every one of the seven declared files>
```

The truth is the exact opposite. The merged squash commit `8b143643` touches
**precisely those seven files** — 7/7, no extras, no omissions. Perfect recall
reported as total failure.

The cause is lifecycle ordering, not data. The aspect derives the footprint live
from the plan's worktree (`{base}...HEAD` ∪ porcelain). The composed manifest
orders `branch-cleanup` — which removes the worktree — at index 15, and
`plan-marshall:plan-retrospective` at index 16. **The worktree is always gone by
the time the aspect runs.** This is not a fluke of this plan: it is structural for
every plan whose manifest carries both steps in the default order.

**Instance 2 — the composer's build decision.** At `17:13:08Z`, during **4-plan**,
`manage-execution-manifest compose` logged:

```
pre-push-quality-gate omitted — plan footprint is empty — no changed files to build
```

Phase 5 did not write its first file until `17:20`. At compose time no footprint
could exist yet. The step survived only because an *independent* rule
(`ceremony_finalize selection — finalize.qgate=always`) re-added it four log lines
later. Had that ceremony knob been `auto`, this plan would have pushed seven changed
files with the pre-push quality gate omitted on the stated grounds that it had
changed nothing.

## Solution

**Rule:** a footprint read must distinguish *"the footprint is empty"* from
*"the footprint source is unavailable / not yet populated"*, and must never render
the second as the first. Concretely:

1. **Probe the source before grading.** When the derivation source is absent — no
   worktree on disk, no commits yet on the branch, compose running before phase 5 —
   the correct output is a third state (`unknown` / `skipped` with a reason token),
   not `0` and not `fail`. This is the same discipline already recorded for merge-lock
   staleness: *an empty worktree-scoped store means "unknown", never "stale"*. The
   rule generalizes beyond locks to every footprint read.
2. **For `plan-retrospective` specifically**, either capture the footprint *before*
   `branch-cleanup` runs and persist it into the plan directory for the retrospective
   to consume, or resolve it post-merge from the merge commit. The plan directory
   survives branch-cleanup; the worktree does not. A fallback to the merge commit is
   available and correct — it is how this retrospective established ground truth by
   hand.
3. **For `compose`**, a build/no-build decision taken at plan time against a footprint
   that cannot exist yet is not a decision, it is a constant. Either defer the
   omission to a point where the footprint is real, or state the predicate's
   precondition and skip (not omit) when it is unmet.

## Impact

Squarely on theme. `Recall 0% below 70% threshold` is maximally confident phrasing —
a named metric, a named threshold, an enumerated list of "missing" files — wrapped
around a measurement that never took place. Anyone reading the compiled report
without independently checking the merge commit would conclude this plan shipped
none of what it declared.

The self-referential sting: **the tool whose job is to detect false signals emitted
one, about itself, in its own report.** And because the failure is ordering-driven
rather than data-driven, it fires identically on every plan — so the retrospective
corpus this epic is mining is likely carrying a systematically false recall column.

Worth checking whether archived plans' recall figures are affected the same way
before any cross-plan conclusion is drawn from them.
