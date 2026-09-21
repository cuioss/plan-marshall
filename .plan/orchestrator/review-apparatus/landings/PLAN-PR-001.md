# Landing — PLAN-PR-001 `wait-for-comments-counts-rows`

epic: review-apparatus · analysed 2026-08-01 · **PR #1071 MERGED** `7da89fa9` at `2026-08-01T17:22:59Z`
(verified via `gh api repos/cuioss/plan-marshall/pulls/1071`, not taken from the paste)
· plan id `wait-for-comments-counts-rows` · 2/2 deliverables, 22/22 finalize steps

## What landed

The `cmd_pr_wait_for_comments` completion predicate is now **two-armed**: count-growth retained for
append-per-review bots (`participation_requires_update: false` — CodeRabbit, Sourcery), plus
**timestamp movement** (`max(updated_at, created_at) > wait_start`) for edit-in-place bots
(`participation_requires_update: true` — PR-Agent). Adds `detector_answerable` /
`unanswerable_reason` / `movement_matched_bots[]`, so an await that could *never* have answered is
distinguished from a genuine timeout.

⭐ The widening is a **PORT** of the pattern already in `github_re_review.py`, not an invention — the
framing the spec asked for, honoured.

## Scope growth — twice, both correct

1. ⭐ **The spec's OBSERVED claim about `github_ops.py` was FALSE, and Q-Gate caught it.** The spec
   said no edit was needed because it "already returns `updated_at` on all three record kinds".
   `REVIEW_THREADS_QUERY` in fact selected `updatedAt` only on the issue-level node, so inline and
   `review_body` records emitted `''` unconditionally. Widening the query closed a latent hole where
   the movement arm would have been **silently vacuous** for any future bot with those evidence shapes.
   ⚠ Note what this was: a claim the orchestrator labelled OBSERVED in the spec that was **not**
   observed. The verify-first contract worked — the consuming phase checked it against the implementing
   source and refuted it. That is the contract succeeding, not failing.
2. Self-review found the CI-abstraction docs — the mandated caller path — still describing count-only
   behaviour. Converged at pass 3, each round finding smaller defects.

## Coordination honoured

The population-derivation step **named sibling-owned sites and handed them over rather than absorbing
them** — notably PLAN-PR-005's `cmd_fetch_findings` "Pre-filter 5". `github_re_review.py` and
`bot_registry.py` stayed read-only references. ⭐ This is exactly what trap (e) and the emit-time
disjointness check were protecting, and it held under execution.

## ⛔ Reconciliation — the operator CORRECTS the plan's own retrospective, and both are partly right

The plan's candidate-lesson `-008` asserts **both** barrier predicates were unevaluated at merge. The
operator corrects that as an overstatement. Reconciled, verified against what each source can actually
attest:

| Predicate | Verdict | Basis |
|---|---|---|
| **1 — zero pending `pr-comment` findings** | ✅ **EVALUATED** | Operator re-ran immediately with correct `--required-bots`/`--optional-bots`, got `status: success`, pending query returned 0 — before the merge |
| **2 — required-bot participation vs this HEAD** | ⛔ **NEVER RAN** | Not disputed by the correction: the stale cached doc the step executed has **no Predicate 2 section at all** |

⇒ The plan's artifact **overstates**; the operator's correction is accepted. ⚠ But the corrected
version is still serious and must not be read as an all-clear: **a required-bot participation predicate
was structurally absent at merge time.** The merge was gated on strictly less than the barrier
advertises.

## ⭐⭐ Root cause — the stale plugin cache, now with hard numbers

Every skill in the session loaded from plugin cache **`0.1.1240`** while the installed version was
**`0.1.1275`** — 30 version directories present, **299 changed files** in the `plan-marshall` bundle
alone (49 new-only, 177 pin-only), plus 78 in `pm-plugin-development`.

`--enabled-bots` was removed from the codebase on **2026-07-28 by `facb0df44` (#1041)** — four days
before this run. So the mid-run "`--enabled-bots` doc drift" the executor flagged was **not drift in
main at all**: it was a four-day-old cached doc being read as current.

⛔ **`marshall-steward preflight` reported `fresh`, and was RIGHT about the executor while blind to the
skill cache.** That is the previously-recorded pin/orphan-GC inversion signature recurring in a new
form. The sweep this morning already carried this as a Watch with softer numbers
(cache `0.1.1240` vs executor `0.1.1271`); this landing **hardens it and traces concrete damage to a
merge gate**. `sync-plugin-cache` has since pulled the cache to `0.1.1277`, so the *instance* is
repaired — the **signal gap is not**.

## ⚠ The self-referential trap, correctly flagged by the plan

This plan fixed the await predicate, and its own finalize `automatic-review` await then timed out at
192s with `new_count: 0` — the exact symptom it fixed. **The fixed code never ran**: finalize executes
the installed plugin-cache copy, which was pre-fix. ⛔ Neither polarity may be read as evidence — a red
does not refute the fix, and a green would not have proven it.

## Inbox residue — 14 messages, all valid, all drained this session

1 landing · 4 findings · 9 candidate-lessons. Routing verdicts in
[`decisions-archive.md`](../decisions-archive.md) and the epic's § Open Defects; the five retained
here are review-domain, the nine delegated ones are not.

## Feeds

- **PLAN-PR-005** — its `cmd_fetch_findings` "Pre-filter 5" site was named and left untouched, as
  designed. Unblocked and unchanged.
- **PLAN-PR-008** — candidate-lessons `-008` and `-010` land squarely on the pre-merge barrier it owns.
- **PLAN-PR-014** — `-008` is the same archetype it just fixed (a producer call dies, the step records
  `done`), one door over. Its shipped `nargs='?'` + UNKNOWN-verdict pattern is the model to copy.
- **`truthful-signals`** — 8 candidate-lessons + 1 finding delegated; the plugin-cache staleness signal
  is the root cause of this epic's `-008` and is **owned there**, not here.
