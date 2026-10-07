envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:08:39Z

component=plan-marshall:phase-6-finalize
category=bug
disposition=new
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369

# create-pr's stamped pr_number survives a close-and-reopen, so the structured fact names a closed PR while the plan lands on another

## Observed

This plan created PR **#1367**, and `status.metadata.phase_steps["6-finalize"]["create-pr"]`
recorded:

```
create-pr:
  outcome: done
  display_detail: "#1367"
  facts:
    pr_number: "1367"
```

The operator then directed (2026-08-30T10:05:19Z) that #1367 be **closed unmerged** and a fresh PR
opened on the same branch and HEAD, to give CodeRabbit a clean review context. The plan landed as
**#1369**, merged via the queue as `09f92b5e8` (decision.log, 13:36:42Z).

`create-pr.facts.pr_number` is **still `1367`** after the merge. Any consumer reading that
structured fact addresses a closed, unmerged PR.

## Why the stale value is not obviously stale

Three channels disagree, and the structured one is the wrong one:

| Channel | Says | Correct? |
|---|---|---|
| `status.metadata…create-pr.facts.pr_number` | 1367 | **no** |
| `logs/work.log` | last mentions #1367; never mentions #1369 at all | **incomplete** |
| `logs/decision.log` | close #1367, merge #1369 as 09f92b5e | yes |

`branch-cleanup` recorded `"merged via queue as 09f92b5e, worktree removed, branch pruned"` — the
merge commit, not the PR number — so the one step that *knew* the landing happened stamped no PR
identity to correct the stale one. The `pr-comment` findings carry `pr_number: 1369` correctly,
because they were filed from PR state; the step fact does not, because it was stamped once at
creation and never re-read.

## The generalisable rule

**A PR identity must be stamped from PR state at the moment it is used, never carried forward from
the creation event.** A PR is not immutable for the duration of a finalize run: it can be closed,
superseded, or re-opened, and a fact recorded at creation silently stops describing the plan's
actual landing. This is the same recurrence signature as the known rule "stamp PR ids from PR
state, never from the landing message".

## Remedy (for the epic to scope)

1. Have `branch-cleanup` (or the merge-verification step) **re-stamp** `create-pr.facts.pr_number`
   from the PR it actually merged, rather than leaving the creation-time value in place.
2. When a PR is closed and superseded mid-finalize, record the supersession explicitly
   (`superseded_by`) rather than leaving a bare stale id — a reader can then tell "wrong number"
   from "number of a PR that was deliberately abandoned".
3. Emit the PR-identity change to `work.log` as well as `decision.log`. The narrative channel
   currently ends at #1367, so a work-log-only reader has no way to learn the plan landed elsewhere.
