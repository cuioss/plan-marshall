envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=review-apparatus
kind=landing
created=2026-08-03T21:03:36Z

plan=merge-queue-enqueue-does-not-take
plan_spec=PLAN-PR-009-merge-queue-enqueue-does-not-take.md
pr=1087
merge_commit=ca7cf9bd4
merge_strategy=squash
merged_via=platform merge queue
branch_commits=10
files_changed=21
tests_added_or_modified=14
outcome=landed

# PLAN-PR-009 landed as PR #1087 (squash ca7cf9bd4)

## Landing facts

- PR **#1087**, merged as squash **ca7cf9bd4** on `main` via the platform merge queue.
- The merge was corroborated **three independent ways** before the destructive tail (branch prune, mutex
  release) ran: PR state `merged`; `origin/main` advanced `9b689d65b -> ca7cf9bd4`; and `ca7cf9bd4` is the
  squash commit for #1087. The PR id above is stamped from **PR state**, not from any landing claim.
- 10 commits on the branch, 21 files, 14 new/modified tests.

## What the plan established — and this is the part the epic most needs

The D1 diagnostic gate settled a **third cause** and **refuted both hypotheses carried in the request spec**.

- `use_merge_queue: true` was correctly plumbed and present in the step-params payload. Nothing was
  mis-configured and nothing was dropped in transport.
- The verb actually dispatched was **`ci pr merge`** — a verb that `branch-cleanup`'s merge routing names
  on **neither** branch. This was an **off-routing dispatch**, and it landed on the one merge-shaped verb
  with **no preflight, no readiness poll, and no post-merge check**.
- That is the mechanism by which **#1081** reported `merged: true` on a PR that closed **unmerged**.

### Refuted

- **Hypothesis (i), "fallback to direct merge"** — REFUTED. No enqueue was ever issued, so nothing fell
  back from anything.
- **"The enqueue does not take"** — REFUTED. The same run recovered via `ci pr merge-queue` and **#1082**
  landed through the queue normally.

**The plan's own title inverts symptom and cause.** "merge-queue-enqueue-does-not-take" names a symptom
that does not exist; the defect is an off-routing dispatch that never reached the queue. The epic should
**retire that framing** rather than carry it forward into sibling plan specs.

## What was NOT established — stated plainly

**WHY the executor left the routing is unknown.** No artifact recorded the decision. The shipped work is
therefore **containment plus observability**, not a root cause:

- containment — the verb now refuses the off-routing dispatch **itself**, at the callee;
- observability — instrumentation at all four `use_merge_queue` sites, so a future departure is recorded
  rather than inferred.

A recurrence of the *same* departure would now be refused and logged, but the reason for the departure
remains an open question the epic still owns.

## What shipped

- **Strategy-aware corroboration on every merge-shaped verb.** A squash merge is corroborated by PR state
  / `mergedAt`, **never** by `merge-base --is-ancestor` (which cannot see a squash).
- **`merged` decoupled from `--delete-branch`**, and the branch is not deleted until the merge is
  corroborated.
- **`cmd_pr_merge` gains the base-branch queue preflight.**
- **Population DERIVED from each provider's dispatch registry** rather than hand-listed: GitHub 37 /
  GitLab 35 handlers, 8 merge-shaped, 7 fixed, 1 reference shape.
- **`ci pr view` gains `--pr-number`** — a landing poll must key on the PR number, because the platform
  auto-deletes the head branch as it merges, so a branch-keyed poll dissolves exactly when it is needed.
- **The one-stop enumeration now names all 9 declared params.**
- **A bounded queue-landing gate** holds the prune and the mutex release until the merge is corroborated.
- **A population-derived regression guard.**

## Self-exercise caveat — read this before treating the fix as proven

The fix **was** exercised live by this plan's own merge: routing dispatched `ci pr merge-queue`, the
enqueue returned corroboration, the landing gate observed the merge, and the prune ran only after.

That is **not** the real test. This plan read `branch-cleanup.md` **from its own worktree**, so it
exercised its own in-flight copy. **The first plan to finalize AFTER this merge is the real test** — that
run is the first to read the merged doc from `main`. The epic should treat the next sibling finalize as
the confirming observation and not close this line of work before it.

## Signals at finalize

- `signal_qgate_pending_count`: 15
- `signal_automated_review_count`: 1
- `signal_script_failure_clusters_count`: 0

## Already routed — do not re-route

The plan-retrospective already routed **7 candidate-lessons and 1 finding** into the `review-apparatus`
and `truthful-signals` inboxes (`merge-queue-enqueue-does-not-take-001..004` in each). This landing does
not restate them. Two further lesson-shaped residues ride as separate `candidate-lesson` messages
alongside this one.
