envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:32:23Z

component=plan-marshall:workflow-integration-git:baseline-reconcile
category=bug
bundle=plan-marshall

# baseline-reconcile anchors on a stale phase-1 SHA, so `no_overlap` and `overlap_no_content_conflict` are both unreliable — and one of them auto-merges

## What was observed

During PLAN-TRUTH-035's finalize (PR #1083), `baseline-reconcile` fired twice and was wrong both times:

- at `sync-baseline` it returned `classification: no_overlap`;
- at `branch-cleanup` it returned `classification: overlap_no_content_conflict` reporting **"2 upstream commits"**.

Ground truth at both moments: the branch was **0 commits behind `origin/main`**. The two answers are not merely different — they are mutually inconsistent, and neither matches reality.

## Root cause (verified by code read, not inferred from the symptom)

`marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_baseline_reconcile.py`

`_resolve_baseline_sha()` (line 119) documents its own preference order as *"`status.metadata.worktree_sha` (captured at phase-1-init) → current worktree HEAD"*. It returns the **phase-1-init SHA**. It never computes a merge-base.

Every downstream range is then anchored on that stale point:

- `_list_upstream_commits()` (line 246) runs `git log {baseline_sha}..origin/{base_branch}`.
- `_list_in_flight_files()` (line 555) runs `git diff --name-only {baseline_sha}..HEAD`.

`{worktree_sha}..origin/main` is **not** "commits I am behind by". It is "commits reachable from `origin/main` but not from the SHA this plan started at". Those are different sets the moment the branch's own history advances past that anchor — which this very script causes, because its focused-reconcile path (line 415) runs `git merge origin/{base_branch} --no-edit`. After that merge, the merged-in upstream commits are in the branch's history yet are still **not** ancestors of `worktree_sha`, so the next call re-reports them as upstream. That is the "2 upstream commits" over-report.

The same stale anchor inflates the in-flight set: `{worktree_sha}..HEAD` after a merge includes the upstream files too, so `upstream_files & in_flight_files` becomes non-empty for files the plan never touched, and `overlap` is spuriously true.

The correct anchor is `git merge-base HEAD origin/{base_branch}`, recomputed per call. A SHA captured once at phase-1-init cannot describe divergence at phase-6.

## The second, independent defect: `no_overlap` is two different zeros wearing one label

The classifier's own comment (lines 388-389) states the label's meaning outright:

```text
#   no_overlap  — upstream commits exist but touch disjoint files OR no commits
```

`no_overlap` therefore collapses **"there is nothing upstream"** and **"there is something upstream and I judged it irrelevant"** into a single value. A caller cannot tell which it received, so it cannot tell a genuine all-clear from a judgement that might be wrong. This is the same defect shape the epic already fixed in `orchestrator inbox list`, where `count: 0` was split by an explicit `inbox_state` discriminator precisely because *a zero meaning "could not look" and a zero meaning "looked, found nothing" do not share a representation.*

Here the payload already carries `upstream_commit_count`, so the information exists — it is simply not reflected in the label the caller branches on.

## Why this matters more than a wrong log line

`overlap_no_content_conflict` is not advisory. It is the **trigger condition for an unattended `git merge origin/main` into the plan's worktree** (line 414-417). A misclassification driven by a stale anchor causes a real, unrequested history mutation. The gate that is supposed to decide *whether to prompt before touching history* is itself deciding on a corrupted input.

## Proposed fix

1. Replace the `status.metadata.worktree_sha` anchor with a per-call `git merge-base HEAD origin/{base_branch}`. Keep `worktree_sha` only as a labelled fallback and report `baseline_sha_source` honestly (`merge_base` / `metadata` / `head`).
2. Split `no_overlap` into two values — `no_upstream_commits` and `upstream_disjoint` — so the caller can distinguish the two zeros. Do not leave the discriminator implicit in `upstream_commit_count`.
3. Add a regression that runs the reconciler twice with a focused reconcile in between and asserts the second call reports zero upstream commits. The current suite does not cover re-entry, which is why a defect this reachable survived.

## Impact

Any plan whose finalize crosses `sync-baseline` and `branch-cleanup`. The over-report is silent — it renders as a confident count with commit subjects attached, which reads as strong evidence rather than as the artefact of a stale anchor. Epic theme fit is exact: a confident signal hiding the caveat that its own anchor moved.
