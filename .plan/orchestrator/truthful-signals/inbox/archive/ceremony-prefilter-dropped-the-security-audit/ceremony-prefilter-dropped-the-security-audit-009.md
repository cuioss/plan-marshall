envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:53:51Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# Derive the realized footprint from a persisted record, not from a worktree that finalize deletes

`check-artifact-consistency` reported this plan's coverage as:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 13
  found: 0
  recall_pct: 0.0
```

with all thirteen declared files enumerated as missing. **The true recall is 92%** — twelve of the
thirteen declared files are in the merged squash `ad683c574`, and the thirteenth
(`_cmd_change_type_heuristic.py`) was declared *read-intent only* under a discovery deliverable and
correctly never mutated.

The cause: the aspect derives the plan's footprint live from the worktree (`{base}...HEAD` ∪
porcelain). `branch-cleanup` removes the worktree before the retrospective step runs. The
derivation therefore returned an empty set, and every declared file scored as missing.

The failure shape matters more than the number. This is not a detector that went quiet — it is a
detector that produced a **loud, confident, red verdict** out of an input it silently failed to
obtain. A reader who trusted it would conclude a plan that delivered 92% of its declared surface
delivered none of it. It is the same defect class this plan was chartered to fix, pointed the other
way: there, an absent signal caused a security gate to be silently skipped; here, an absent signal
causes a coverage gate to loudly and wrongly fail.

## Solution

- **Persist the realized footprint at branch-cleanup**, before the worktree is removed — a
  `work/footprint.txt` written from the merged/squashed commit's name-only diff.
- **Have `check-artifact-consistency`, `check-manifest-consistency` and `check-routing-decisions`
  all read that persisted file** rather than probing a tree that may no longer exist.
- **Fail loud on an empty derivation, never quiet-zero.** When the footprint source resolves to
  nothing, emit `status: skipped` with reason `footprint_unavailable` — never a `0%` recall figure.
  A recall of zero and an unmeasurable recall must not share a rendering.

## Impact

Every post-merge retrospective on a worktree-backed plan is affected — which, under ADR-002, is
every plan that reaches phase 5. The finding also invalidates the recall figure in any archived
retrospective run after worktree removal.
