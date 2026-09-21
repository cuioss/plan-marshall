envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:05:28Z

# Candidate lesson: the merge-currency treadmill — an unconditional pre-merge rebase re-stales every review credit and can livelock the barrier

**Source**: PLAN-TRUTH-055 merge gate, PR #1129
**Defect class**: livelock / confident-signal-hides-a-caveat
**Observed**: `branch-cleanup` recorded `upstream_commit_count: 4`; `finalize-step-sync-baseline` had already rebased once

## The mechanism

On a repository landing roughly **4 commits/hour**, the finalize path has a self-defeating cycle:

1. `branch-cleanup` performs an **unconditional pre-merge rebase** onto `origin/main`.
2. The rebase moves HEAD.
3. Every review bot's credit is keyed (directly or via comment-mutation currency) to the previous
   HEAD, so **all of it goes stale at once**.
4. The barrier demands re-review. Re-review costs roughly **40 minutes**.
5. During those 40 minutes, ~2-3 more upstream commits land — so step 1 is due again on arrival.

The cycle has no fixed point whenever `re-review latency × landing rate ≥ 1`. It is not a slow
path; it is a **livelock**, and it gets worse precisely on the busiest repositories where merge
throughput matters most.

The confident signal that hides the caveat: each individual iteration reports honest green — the
rebase succeeded, the re-review was requested, the barrier is doing exactly what it says. Nothing
in a single cycle looks wrong. The defect is only visible across cycles.

## The escape used

**Enqueue WITHOUT the local pre-merge rebase**, relying on the merge queue's own
rebase-and-retest. The merge queue already rebases the entry against the queue head and re-runs
required checks — so the local rebase was duplicating work whose only additional effect was to
invalidate review credit.

PR #1129 landed via the queue on that route (`merge_mechanism: merge_queue`).

## Candidate rule

> A pre-merge rebase performed locally, on a repository that merges through a merge queue,
> duplicates the queue's own rebase-and-retest while additionally invalidating every review
> credit. Make the local rebase **conditional** — skip it when the target repo has a merge queue
> that rebases entries — rather than unconditional.

> More generally: any step that moves HEAD inside the merge gate must account for the review
> credit it invalidates. Re-staling N bot reviews to fix a merge conflict that the queue would
> have resolved anyway is a net-negative trade whenever re-review latency exceeds the queue's own
> retest latency.

## Caveats to carry with this

- The escape is only valid where a merge queue exists AND rebases entries. It is not a general
  licence to skip rebasing.
- Related standing hazard, already in the epic: the merge queue **ejects trailing entries on
  rebase** — watch `isInMergeQueue == false`, not just `MERGED`.
- Related standing hazard: `ci pr merge` has previously returned `merged=true` and deleted the
  branch WITHOUT merging. Stamp PR ids from PR state, never from the landing message.
