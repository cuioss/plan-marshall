# Landing analysis — PLAN-PR-046

**Plan**: `plan-pr-046` · **PR**: #1477 — **merged** (squash, GitHub merge queue) at
`77cb2e251b348ce3e840ac1e565f5426f2d587de`
**Deliverables**: 5/5 · **Finalize steps**: 22 recorded in the landing facts, 23 reported by the run
(`archive-plan` fires after the landing is emitted) · **Landing message**: `-011`, `complete: true`
**Corroboration**: PR state read first-party via `ci pr view --pr-number 1477` (`state: merged`);
merge commit and its 31-file footprint read from `git show --stat`. ⛔ Not taken from the narrative.

## What shipped

CodeRabbit's clean-review participation credit is now gated by a **declared content marker**, so a
pre-review walkthrough comment no longer clears the review barrier. That closes the epic's
*"a clean review arrives in a shape the registry does not credit"* defect from the credit side.

## ⛔⛔ THE RISK THIS LANDING CREATES — the shipped gate is unexercised, and it fails CLOSED

From the plan's own finding `-001` item 3: **the declared `recent_review_start` marker is ABSENT from
CodeRabbit's live summary comment on #1477.** So the `issue_comment` gate this plan shipped is
currently **unexercised in production**, and its canonical layout is pinned by no observation.

⇒ The failure direction is **fail-closed**: a verdict comment that does not carry the marker resolves a
clean review `absent`, **which blocks a merge**. ⚠ Every plan that now depends on a CodeRabbit clean
review to clear its barrier inherits that risk, and the first evidence will be a blocked merge rather
than a report.

⭐ **The plan's judgement is recorded and endorsed**: it DECLINED CodeRabbit's *"anchor the marker"*
Major **twice**, because tightening an unanchored match against a layout nobody has sampled is the
larger and less reversible risk. ⛔ Do not re-litigate that; the open action is to SAMPLE the live
layout, not to tighten the match. Recorded as a Watch in `epic.md`.

## Measurement honesty — three refusals to publish a number, all correct

This run declined to manufacture three figures, and each refusal is the behaviour this epic exists to
produce:

- **`gate_tree_unsubstantiated`, `structural_share: null` (not 0)** — the PR's findings carry three
  distinct `reviewed_commit_sha` values (`9fd4709d`, `29b86a6d`, `8313358f`), one per loop-back, so no
  single tree was ever reviewed in full. The 7-addressable / 3-structural partition is preserved as a
  judgement about an unmeasurable PR, never as a rate.
- **`permission-prompt-analysis` recorded `coverage: not_evaluated`** rather than letting an empty list
  read as a clean zero — it reaches only the reduced transcript (5 of 1810 messages), which by
  construction cannot carry a permission prompt.
- **`branch-cleanup` recorded NO `merge_mechanism` fact** — the step re-entered on an already-merged
  PR, so it merged nothing itself. ⭐ The absence of the key is the honest signal, not a gap.

⚠ Against those: `check-manifest-consistency` graded `branch_cleanup_changes` **fail over no evidence**
— at order 995 the plan is already merged so its diff against `origin/main` is empty, and the aspect
reported `diff_available: true` while grading. The sibling `check-outline-vs-shipped` resolved 31
realized paths through the shared resolver **in the same run**, so the evidence was reachable. This is
the normal post-merge state, not an edge case.

## The producer handoff gap this epic owns

**Two of the three bots are unmeasurable in the review corpus**: `cuioss-review-bot`
(`participated_but_empty`) and `sourcery` (`refused_structural`, 150000 diff-char cap) have **no
findings-store records**, so nothing persists their `review_completeness` classification where a step
at `order: 990` can read it. The retrospective correctly declined to upgrade their rows from a
separately-observed state. ⇒ This is exactly `PLAN-PR-058` D1/D2's subject (persist the
discrimination), and the landing is its third independent sighting.

## Cost, and where it went

6.77M tokens / 5h07m worked against a `single_module + bug_fix` anchor of 1.3M / 90 min — **5.2×**.
⛔ **The overrun is the review loop, not the change**: finalize alone 3.28M (48.5%), more than
execute's 2.20M, with `pre-submission-self-review` firing 7× (6 loop-backs), `pre-push-quality-gate` 5×,
`automatic-review` 4×, `ci-verify` 3×. ⭐ **Six operator-mandated 90-minute waits, and every trigger
RESET CodeRabbit's window** (stated ETA moved 20 → 48 → 52 minutes) — the fourth consecutive plan whose
dominant cost is the review window rather than its own work.

## Scope drift

10 undeclared files modified (threshold 5), all during finalize as self-review rounds reached contract
docs and build files; `cuioss-review-bot.md` was declared `write-replace` in deliverable 4 but settled
as a deliberate non-edit, with the outline never corrected. ⚠ **Second consecutive landing** whose
realized footprint exceeded its declaration — see `landings/PLAN-PR-033.md`, where the undeclared half
discharged another plan's deliverable. `reconcile-scope` detects this and nothing in finalize calls it.

## Reconciliation actions taken

1. Queue row `PLAN-PR-046` → `shipped`, `pr: 1477`, landing stamped.
2. Watch opened on the unexercised `recent_review_start` marker (fail-closed, can block merges).
3. `-001`'s two detector defects folded: the stale-refusal sampling to `PLAN-PR-057` D10 (**third**
   independent sighting of one mechanism), the unmatched ETA phrasing to `PLAN-PR-056` D8.
4. Three foreign-sender findings (`truthful-signals-055`, `-056`, `plan-truth-139-001`) drained in the
   same pass — see `epic.md`.
