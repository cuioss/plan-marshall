# Landing Analysis: PLAN-81 — Self-review cannot see an unreachable guard

epic: truthful-signals
workstream: WS-01
pr: 1042 — merged as `8e49ed0fa`, 2026-07-29 04:50:10 +0000

> Every claim below was corroborated against first-party ground truth (the merge commit, the PR
> comment stream via the CI abstraction) before recording. The plan report and the inbox landing
> message were treated as leads.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — GATE: unreachability is deterministically detectable | shipped-as-specified | Selected framing (b) predicate-over-parsed-structure; rejected (a) on a **first-party false negative** — #1013's guard had tests, so a `test_present` signal would have found nothing |
| D2 — `scan_derived_keys` detector → Rule 18 / key N19 | shipped-as-specified | `_self_review_detectors.py`, `_self_review_patterns.py`, `unreachable-guard-detection.md` in the CodeRabbit file list |
| D3 — clean verdict split into two non-prefix forms | shipped-as-specified | `pre-submission-self-review.md`; `nothing-to-check` now distinct from `no-check-matched` |
| D4 — #1013 pre-fix/post-fix regression pins | shipped-as-specified | `test_self_review_reachability_regression.py` |

⭐ **D1's discriminator is the durable output**: the surfacer sees a defect when **both halves of the
contradiction are co-present tokens in the change surface**; it misses when the contradiction needs a
fact outside the diff. **Volume was refuted directly** — caught at 38 candidates (#1038), missed at
50 and 75. That closes the volume-read-as-coverage question for this detector.

## Metrics and Anomalies

- Tokens **4,502,700**; worked **3h14m**; wall **11h32m**.
- ⚠ **`6-finalize` alone: 1h28m worked / 9h19m wall / 2,333,375 tokens** — 52% of the plan's tokens
  and 81% of its wall-clock in the final phase.
- ⛔ **The retrospective again reported `recall=0%` on an empty footprint** (real footprint: 11
  files), because `plan-retrospective` runs after `branch-cleanup` removes the worktree. **This is
  the third independent observation** of the archetype (PLAN-10, #1040, here) and is exactly what
  **PLAN-106** was staged to fix. Recurrence recorded there, not re-filed.

## Routing and Merge Behavior

- **The plan reproduced its own target defect twice, and neither was caught in-house:**
  1. CodeRabbit found `_key_consumed_as_identity` scanning the **full post-image** against its own
     docstring's *"invisible outside the diff"* invariant — a mis-scoped guard **inside the
     guard-detector**.
  2. The TASK-008 registry fix left a **fifth hand-maintained mirror**, permitting exactly the drift
     it existed to close. Caught only by an explicit adversarial re-read of the fix's own diff,
     which happened because the dispatch prompt demanded it.
  3. A shipped test guard was **conditionally vacuous on terminal width** — argparse hyphen-wrapping
     broke two registry labels; it would have passed at 120 columns.
- ⚠ Meanwhile `pre-submission-self-review` reported *"clean: 101 candidates examined, no check
  matched"* — the **new D3 wording, honest about its own scope** — over a diff carrying all three.
- **Sourcery hard-refused** (weekly 500 000 diff-character quota) — **fifth consecutive PR** with an
  unrecognized-or-unrecoverable refusal (#1024, #1032, #1034, #1040, #1042).
- **Merge:** squash `8e49ed0fa` via merge queue. Operator approved the 4-file registry refactor
  (TASK-008) and the pre-merge rebase over 3 upstream commits.

### ⛔ Post-merge PR revisit — THE RULE FIRED, n=2 → n=3

**This is the first landing where the mandatory revisit caught a live finding.**

| Event | Time |
|---|---|
| Operator posts `@coderabbitai review` | 04:47:51Z |
| CodeRabbit **acknowledges** (`Review finished`, an ack — not a review) | 04:47:59Z |
| **PR merged** as `8e49ed0fa` | **04:50:10Z** |
| CodeRabbit posts the **actual review**: *"Actionable comments posted: 1"* | **05:01:17Z** |
| CodeRabbit posts the **inline finding** | **05:01:16Z** |

⇒ **The plan merged on an acknowledgement, and the real review arrived ~11 minutes AFTER the merge.**
The plan's own report was honest about this — it recorded `head_sha_verified: false` and explicitly
declined to read the ack as a clean review. **The gap is structural, not a reporting failure.**

**The live finding, now untriaged in merged main** — `_self_review_detectors.py:1454`,
🟠 Minor / Functional Correctness: `_DEF_OR_CLASS_HEADER` accepts indented functions but `_DEF_NAME`
matches only `def`, so **a nested closure is treated as an unnamed header and closes the outer
block**, splitting the outer function's remaining body and its scan-loop shape.

⭐ **Note where it landed: in the block-parsing helper of the unreachable-guard detector this very
plan shipped.** A defect in the detector built to catch defects — the archetype, again, at n≥5.

**Sibling scan:** #1041 (merged 21:11:23Z, latest comment 21:09:50Z) — clean. No other PR merged in
the window.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1042; `landing`; `plan_marshall_plan_id` — all four stamped
- [x] epic.md queue reconciled
- [x] post-merge finding recorded as a live Open Defect (owner: PLAN-102's sweep)
- [x] late-arrival recurrence advanced **n=2 → n=3**
- [x] retrospective empty-footprint recurrence folded onto PLAN-106
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- ⛔ **The `#1042:1454` nested-`def` finding is LIVE and untriaged in main.** PLAN-102 owns the
  general untriaged-in-main sweep; this is now its **second** confirmed population member alongside
  the five #1036 findings.
- The plan flagged that `pre-submission-self-review` is **not in `HEAD_DEPENDENT_STEPS`**, so it did
  not re-fire over the loop-back diff that introduced all three defects. Filed by the plan as an
  inbox candidate-lesson; dispositioned in the drain.
