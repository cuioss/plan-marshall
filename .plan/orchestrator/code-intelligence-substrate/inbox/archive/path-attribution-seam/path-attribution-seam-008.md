envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T20:48:22Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# plan-retrospective is scheduled where two of its own inputs do not exist — the worktree is already deleted before it, and the metrics are not closed until after it

## What happened

On PLAN-CIS-023 the retrospective's **artifact-consistency** aspect returned:

```text
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 27
  found: 0
  recall_pct: 0.0
```

Zero files found. The plan's actual coverage was **exact**: 21 declared write-intent files, 21 realized files in the squash-merge commit, 0 unexpected, 0 missing, and the two declared read-intent files correctly untouched. A perfect footprint scored 0%.

The cause is step ordering in the standard-posture finalize manifest, not aspect logic:

| Step | Name | Effect on the retrospective's inputs |
|-----:|------|--------------------------------------|
| 16 | `branch-cleanup` | merges the PR, then **removes the worktree** |
| 17 | `plan-marshall:plan-retrospective` | derives the footprint **from the worktree** (`{base}...HEAD` ∪ porcelain) |
| 20 | `record-metrics` | closes the `6-finalize` metrics row |

The aspect reads a worktree that step 16 deleted one step earlier, and reports on a metrics file that step 20 has not yet closed. `metrics.md` at retrospective time therefore reads:

```text
> Partial: unrecorded phases — 6-finalize
| **Total** | **3h2m (n=4/6)** | ... | **2,126,732 (n=4/6)** |
```

— under-counting the plan by the 1,709,455 tokens that `6-finalize` actually spent, which is the single most expensive phase of the run (44.6% of the ~3.84M plan total).

## Why this matters more than one bad number

Both failures are **structural for every plan on the standard posture**, not incidental to this one. `branch-cleanup` precedes `plan-retrospective` and `record-metrics` follows it in the composed manifest, so:

- the declared-vs-achieved coverage check — the deterministic half of the scope × thoroughness dial — is **vacuous on every run**, and
- every plan-efficiency reading the retrospective produces is **structurally missing its most expensive phase**.

A check that cannot pass is worse than an absent one: it emits a `fail` with a confident percentage, and a reader has no way to tell a genuinely-uncovered plan from one whose evidence was deleted. This is the vacuous-guard archetype in its measurement form — the predicate fires every time, so it discriminates nothing.

## The rules

**Do X — when an aspect reads a resource another step owns, assert the resource's lifetime against that step's position in the manifest, not against its existence at authoring time.** The worktree exists for steps 1–16 and not for 17+. That is a manifest fact available to the composer.

**Do X — give the footprint derivation an ordered fallback chain.** Worktree diff (when a worktree is on disk) → the PR's squash-merge commit resolved from `status.metadata` (the recovery this retrospective performed by hand as `git show --name-only --pretty=format: <merge_sha>`) → the legacy `references.modified_files` key. Only the last rung should be reachable for archived plans.

**Do X — either move `plan-retrospective` before `branch-cleanup`, or make the two inputs it needs survive the step that removes them.** The ordering has a second victim in `record-metrics`; a single reposition fixes both, but a reposition must not reintroduce the ordering defect recorded on PLAN-10 (a plan that fixes a finalize-time component cannot have that fix exercised by its own finalize).

**Not Y — do not read a `0%` recall from this aspect as evidence of poor coverage.** On the current ordering it is evidence of a deleted worktree and nothing else.

## Detection

Mechanical and cheap: `affected_files_recall.found == 0` with `declared > 0` on a plan whose `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].outcome == "done"` is the exact signature. The aspect can distinguish "no footprint evidence available" from "footprint evidence available and empty" and must report the first as a **skip with a reason token**, never as a scored `fail` — the same absence-vs-empty discipline this epic already enforces for `attributor_count: 0` vs `attributor_count: N, claims: []`.

## Recurrence context

This is the epic's own `resolver_count: 0` vs `resolver_count: N, edges: []` distinction, turned on the retrospective itself. PLAN-CIS-023 shipped that distinction into `which-module` in the same run in which its own retrospective violated it.
