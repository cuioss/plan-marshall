envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T14:06:31Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# The retrospective is ordered wrong from both sides — it measures a footprint that branch-cleanup already deleted

## What happened

`plan-marshall:plan-retrospective` runs at finalize order **995**. `branch-cleanup` runs before it and
removes the plan's worktree. `check-artifact-consistency` derives the plan footprint **live from the
worktree** (`{base}...HEAD` ∪ porcelain).

So on this plan the coverage aspect reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
declared: 12
found: 0
missing[10]: ...
```

The real recall is **12/12 = 100%**. Reconstructing the footprint from the squash commit on main
(`git show --name-only 972dc0487`) returns 14 files, and **all 12 declared files are present**.

The measurement did not degrade gracefully. It returned a confident, specific, maximally-bad number —
"recall 0%, 10 files missing" — for a plan that declared its scope correctly.

## The same finalize has the inverse defect

`project:finalize-step-lessons-housekeeping` logged this at 07:46:39:

> quality-verification-report.md unavailable (retrospective runs at order 995, after this settle-band
> step) and references field modified_files absent — proceeded on request.md plus the branch diff

One step needs the retrospective's **output** and runs before it. The retrospective needs the worktree
and runs after it is destroyed. The retrospective is sandwiched incorrectly from both directions.

## Root cause

The footprint is *derived* at read time from a mutable substrate (the worktree) rather than *captured*
at the moment it was still true. Any consumer ordered after the substrate's destruction reads zero, and
zero is indistinguishable from "measured and found nothing".

This is the recurring **vacuous-measurement** archetype, and it lands with particular irony here: this
plan exists to stop a *correct* PR review from scoring as *maximally wrong*, and its own retrospective
scored a *correct* plan as *maximally wrong*, by the same mechanism — an absent measurement rendered as
a bad measurement rather than as no measurement.

## Proposed action

1. **Capture, don't derive.** Have `branch-cleanup` (or `push`) persist the realized footprint —
   `git show --name-only` of the merge/squash commit, or the pre-removal `{base}...HEAD` list — into
   `references.json` (`realized_files`) or `work/footprint.toon`, as a deterministic side-effect.
2. **Prefer the captured list.** `check-artifact-consistency` should read the persisted footprint first
   and derive live only as a fallback.
3. **Fail loud, not zero.** When neither source is available, the check MUST return
   `status: skipped, reason: footprint_unavailable` — never `recall 0%`. An absent measurement and a
   failed measurement must not share a representation. (This is the same rule as candidate-lesson
   `cl-004`, applied to coverage instead of review participation.)
4. **Fix the ordering.** Either move `plan-retrospective` ahead of `branch-cleanup`, or move
   `finalize-step-lessons-housekeeping` after it. Both cannot be satisfied at the current orders.

## Evidence

- aspect: artifact-consistency — `affected_files_recall,fail,Recall 0% below 70% threshold`, `found: 0`
- verification — `git show --name-only 972dc0487` returns 14 files containing all 12 declared
- `git worktree list` — the plan's worktree is absent (removed by branch-cleanup)
- aspect: log-analysis — lessons-housekeeping's own 07:46:39 log line naming the order-995 problem
- Related prior: the PLAN-10 finalize-ordering defect (a plan that fixes a finalize-time component
  cannot have that fix exercised by its own finalize) — same ordering class, different component.
