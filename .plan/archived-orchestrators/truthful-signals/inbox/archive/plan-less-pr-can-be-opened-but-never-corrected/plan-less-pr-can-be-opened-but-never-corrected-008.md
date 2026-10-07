envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T13:03:59Z

# affected_files_recall is dead-by-construction: finalize deletes the worktree before the retrospective reads it

- **component**: `plan-marshall:plan-retrospective`
- **category**: bug
- **severity**: error
- **confidence**: high
- **source**: plan-retrospective of `plan-less-pr-can-be-opened-but-never-corrected` (PR #1065)

## What happened

The artifact-consistency aspect reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 76
  found: 0
  recall_pct: 0.0
```

The plan's real recall is roughly **89%** — 68 of the 76 declared files are present in
the 93-file merge commit `468b82279`. The 0% is not a coverage failure. It is a
measurement failure reported in the vocabulary of a coverage failure.

## Root cause — an ordering invariant, not a one-off

`check-artifact-consistency._resolve_footprint` has three tiers:

1. **Live diff** — requires `resolve_live_worktree(plan_id)` to return a directory on disk.
2. **Legacy key** — `references.modified_files`, which was removed with the ledger.
3. **Empty**.

In `execution.toon` `phase_6.steps`, `branch-cleanup` is step **15** and
`plan-marshall:plan-retrospective` is step **16**. `branch-cleanup` removes the worktree.
So for **every plan with `use_worktree: true`**, tier 1 is structurally unreachable by the
time the aspect runs, tier 2 is gone, and tier 3 is the only outcome.

This is not a race and not specific to this plan. The check is dead for the entire
worktree-backed population, and it has been reporting a confident `fail` the whole time.

## Why it stayed invisible

The failure mode is a *plausible* number. `Recall 0%` reads like a real finding about a
sloppy plan, so it gets absorbed as noise rather than escalated as a broken detector.

## Suggested direction

Resolve the footprint from a **commit range** rather than a live directory —
`status.metadata.main_sha`..`worktree_sha` (both already persisted in status.json), or the
merge commit. The data survives worktree removal; the directory does not.

Separately: whatever the resolution, an unresolvable footprint must return
`inconclusive`, never a computed recall percentage. See sibling candidate-lesson cl2.
