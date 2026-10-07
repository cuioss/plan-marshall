envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:44:00Z

component=plan-marshall:phase-6-finalize
category=bug

# branch-cleanup runs before plan-retrospective and manufactures a 0% recall FAIL

The finalize manifest orders `branch-cleanup` at step index 15 and `plan-marshall:plan-retrospective` at index 16. `branch-cleanup` removes the worktree. `check-artifact-consistency` then derives the plan's footprint **live from that worktree** (`{base}...HEAD` ∪ porcelain), finds nothing on disk, and reports:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 12
  found: 0
  recall_pct: 0.0
```

The plan's real footprint is 8 files (merge commit `c259f5c7`), and its write-intent recall is **6/6 = 100%**. The `fail` is manufactured entirely by step ordering — the aspect measured an empty directory, not an empty delivery.

The legacy `references.modified_files` fallback does not rescue it: that key was removed and is retained only for archived plans predating the change, so a *live* post-cleanup plan has no fallback at all.

This is the epic's theme with the polarity inverted. The usual case is a confident green hiding a caveat; here a confident **red** is produced by a measurement taken after the thing being measured was deleted. Both are the same defect class: a predicate evaluated against the wrong population, reported without the caveat that would make it readable.

It is also a recurrence of the PLAN-10 finalize-ordering archetype (a fix cannot be exercised by its own finalize because the step that would exercise it runs earlier). Same structural cause, different pair of steps.

## Solution

Pick one; the first is cheapest and least invasive:

- **Snapshot the footprint before it becomes underivable.** Have `branch-cleanup` (or the push barrier, which is earlier and always runs) persist the realized footprint into the plan directory. Every downstream footprint consumer reads the snapshot instead of re-deriving from a tree that may be gone.
- **Fall back to the merge commit.** When no worktree is on disk, derive the footprint from the merged PR's commit range rather than returning an empty set. The data is still available in git; only the worktree is gone.
- **Refuse to grade rather than grade zero.** If the footprint genuinely cannot be derived, the check MUST return `skip` with an explicit `footprint_underivable` reason — never `fail` with `recall_pct: 0.0`. A zero that means "could not measure" and a zero that means "measured nothing" must not share a representation.

The third bullet is the load-bearing one regardless of which mechanism is chosen: **an unmeasurable quantity must not be reported as a measured zero.**

## Evidence

- aspect: `artifact-consistency` — `affected_files_recall,fail,Recall 0% below 70% threshold`; `found: 0`
- aspect: `manifest-decisions` — `phase_6.steps` index 15 = `branch-cleanup`, index 16 = `plan-marshall:plan-retrospective`
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].display_detail` = `"PR #1061 merged via queue, main pulled, branch + worktree removed"`
- ground truth: `git show --stat c259f5c7` = 8 files changed, 398 insertions, 16 deletions
