# PLAN-PR-009 — landed as PR #1087 (squash `ca7cf9bd4`), 2026-08-03

**Verified by the correct oracle**: `manage-status list` returned only `NO_PLAN` — the plan left the list.
PR state re-derived independently as `merged`. **PR id stamped from PR state**, and the landing message
agreed (`pr=1087`) — the first landing in this epic where those two sources did not need reconciling.

10 commits · 21 files · 14 tests · 22/22 finalize steps · 2/2 deliverables.

## ⛔⛔ Both of my hypotheses were refuted, and so was the plan's title

The spec offered two explanations and instructed the plan not to assume between them. **The D1 gate
refuted both, and refuted the premise underneath them.**

| Carried in the spec | Verdict |
|---|---|
| (i) the enqueue failed and control **fell through** to immediate merge | ⛔ **REFUTED** — no enqueue was ever issued, so nothing fell back from anything |
| (ii) the routing branch was not taken despite the param resolving `true` | ⛔ **REFUTED** — `use_merge_queue: true` was correctly plumbed and present in the step-params payload |
| "the enqueue does not take" (the **title**) | ⛔ **REFUTED** — the same run recovered via `ci pr merge-queue` and #1082 landed through the queue normally |

**The actual cause is a third thing: an off-routing dispatch.** The verb dispatched was `ci pr merge` —
a verb `branch-cleanup`'s merge routing names on **neither** branch. It did not take the wrong branch; it
**left the routing entirely** and landed on the one merge-shaped verb with no preflight, no readiness
poll, and no post-merge check.

⇒ That is the mechanism behind #1081 reporting `merged: true` on a PR that closed unmerged.

## ⭐ How this relates to my source read — I was right about the shape and wrong about the frame

My drain-time read of `cmd_pr_merge` was accurate and shipped as deliverable 0: `merged` derived from an
exit code, `merged` coupled to `--delete-branch`, the assertion preceding the destructive delete. **All
three are fixed.**

⛔ **But I framed that verb's weakness as the defect. It was the *consequence*.** The verb being weak
mattered only because a dispatch reached it that never should have. ⭐ The plan states the asymmetry
precisely: *the off-routing target was not merely un-preflighted, it was the only merge-shaped verb with
no post-merge check — the departure and the false green are the same event only because containment was
absent at exactly the point the routing did not cover.*

⚠ **My leading causal hypothesis (that the branch delete dequeues the PR) is neither confirmed nor
refuted** — it is moot at the level the plan settled things, because no enqueue existed to be dequeued.
**It remains unsettled for the case where an enqueue HAS occurred.** Not carried forward as live.

## ⛔ What was NOT established, shipped as such

**Why the executor left the routing is unknown.** No artifact recorded the decision, and the plan
explicitly declined to claim one. What shipped is **containment plus observability**, not a root cause:

- **containment** — the verb now refuses the off-routing dispatch **itself**, at the callee;
- **observability** — instrumentation at all four `use_merge_queue` sites, so a future departure is
  recorded rather than inferred.

⭐ **The epic still owns the open question.** A recurrence would now be refused and logged; it would not
be explained.

## What shipped

- **Strategy-aware corroboration on every merge-shaped verb.** ⭐ A squash merge is corroborated by PR
  state / `mergedAt`, **never** by `merge-base --is-ancestor` — which cannot see a squash. ⛔ **This
  corrects the corroboration recipe I wrote into the spec**, which named `--is-ancestor` unconditionally.
- **`merged` decoupled from `--delete-branch`**; the branch is not deleted until the merge is corroborated.
- **`cmd_pr_merge` gains the base-branch queue preflight.**
- **Population DERIVED from each provider's dispatch registry** — GitHub 37 / GitLab 35 handlers,
  **8 merge-shaped, 7 fixed, 1 reference shape.** ⭐ The spec demanded derivation over my hand-list of
  two sites, and the derivation found four more.
- **`ci pr view` gains `--pr-number`** — ⭐ because the platform **auto-deletes the head branch as it
  merges**, so a branch-keyed landing poll dissolves exactly when it is needed. This retires the standing
  `--pr-number does not exist, use --head` workaround this epic has carried for days.
- A bounded queue-landing gate holding prune + mutex release until corroboration; a population-derived
  regression guard; the one-stop enumeration now naming all 9 declared params.

## ⚠ Self-exercise caveat — the fix is NOT yet proven

The fix was exercised by this plan's own merge (routed to `ci pr merge-queue`, enqueue corroborated,
prune held behind the landing gate). ⛔ **That is not the real test**: the plan read `branch-cleanup.md`
**from its own worktree**, so it exercised its own in-flight copy.

⇒ ⭐⭐ **The first plan to finalize AFTER this merge is the confirming observation** — the first to read
the merged doc from `main`. **Do not close this line of work before it.**

## Two corrections the plan volunteered

1. **"Sourcery refused on both passes" — withdrawn.** The review-retrospective found it was **never
   re-invited** on the second pass. One refusal record, not two. ⚠ Directly relevant to PLAN-PR-006's
   per-reviewer measurement: *not-invited* is a third state alongside *refused* and *absent*.
2. ⭐⭐ **A self-review round-4 residual-zero claim was false.** The regex `alternative to .--pr-number`
   required a character between `to` and the flag, so it matched only the backticked form. Three
   survivors remain at `test_ci_base.py:548,561,569`. **The plan committed the exact error it spent five
   rounds fixing — searching for a phrasing instead of a claim.** Mitigating: pre-existing (#184) and
   semantically true for the verbs they describe, so nothing regressed; **the false thing was the claim.**

## Cost — flagged by the plan, and it should be

**7.2M tokens against a `single_module` + `bug_fix` anchor of ~1.3M** — 5.5×. `pre-submission-self-review`
alone was **1.19M across 5 iterations**. ⚠ The 15 defects it found were real, and 5 of CodeRabbit's 10
suggestions targeted this plan's own guard code. ⇒ **Direct input to PLAN-PR-018 (lever L5)**: this is the
best-evidenced instance yet of self-review cost, *with* the yield data that stops it being read as waste.

## Review coverage — the regime holds at five consecutive PRs

The **required** bot (pr-agent) reported *"No major issues detected"* on **both** passes of a diff where an
**optional** bot found 10 issues, **7 genuine**. Sourcery contributed zero (diff over its limit).
⇒ **The quorum proved participation and explicitly not review quality** — PLAN-PR-006's thesis, stated by
the plan itself.
