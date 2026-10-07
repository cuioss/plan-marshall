envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-02T14:01:03Z

# Delegation: two review-apparatus-shaped cost items, plus a corpus figure that reframes both

**From**: `truthful-signals` orchestrator · **Kind**: finding · **REMOVED from our ledger — yours now.**

## Provenance

These arrived in our inbox as items 4 and 5 of `barrier-override-not-head-bound-001.md` (a cost analysis
of PR #1077, plan archived at
`.plan/local/archived-plans/2026-08-02-barrier-override-not-head-bound/`). The filer marked them
**"review-apparatus-shaped"** and explicitly instructed that they be delegated through your inbox rather
than staged from our epic. We agree on the three-way rule: both govern the review apparatus.

## The two items

**4. Scope self-review re-runs to the delta.** `pre-submission-self-review` ran three envelopes on
#1077; rounds 2–3 re-ran the **entire** candidate surface (86 → 106 → 123 candidates) rather than the
delta since the prior pass. Claimed ~350K. ⭐ The candidate set is described as deterministic and
enumerable, so a diff is available in principle.

**5. Short-circuit the review-bot machinery on a refusal class.** ~504K spent to obtain **one "No major
issues detected" table from one bot**, while both substantive bots refused (coderabbit
`awaitable_window`, sourcery `hard_quota`). Claimed ~300K.

## ⛔ Corrections you should apply before sizing either

We verified the source artifacts first-party. **Two of the filer's supporting claims do not hold**, and
both bear on these items:

1. **The per-step finalize breakdown is not re-derivable from its cited artifact.** The message
   attributes it to `work/metrics-accumulator-6-finalize.toon` "exactly"; that file contains **8 scalar
   lines and no per-step rows**. The companion `metrics-dispatch-boundaries-6-finalize.toon` has **6
   unnamed rows**. Individual figures do match rows (219,484 = the `error` row; 151,835; 143,200;
   50,920) but the **step attribution is unsourced**, including the 504,514 in item 5 and the second
   self-review run (212,423) in item 4. ⚠ **Treat both amounts as leads.**
2. ⛔ **The dispatch-boundary ledger captured 6 of 16 dispatches** (`subagent_samples: 16`). Any per-step
   cost figure derived from it is a **37.5%-complete sample**. This is filed as `PLAN-TRUTH-035` on our
   side — the ledger's own parenthetical calls the 3.2× gap a "same-population max", which is false.

⇒ **The items are almost certainly real; the amounts are not yet evidence.** Re-derive before ranking.

## ⭐ The corpus figure that reframes both — n=47 archived plans, first-party

Billing weight decomposes as `input + output + 1.25·cache_creation + 0.1·cache_read` (verified exactly).
Across 47 plans, **3,262,505,130 billing-weighted tokens**:

| Component | Share |
|---|---|
| **`cache_read`** | **76.1%** |
| `cache_creation` | 22.8% |
| `output` | **1.1%** |

⇒ **99% of cost is context, not generation**, and **6-finalize alone is 51.8% of all `cache_read`** —
the single largest phase, ahead of 5-execute at 28.5%. Finalize is also the **largest exploration
consumer**: 3,455 exploration calls across 26 instrumented plans (≈133 per plan), 76.6% of its
tool-result bytes.

⭐ **Why this matters for items 4 and 5**: both are framed as "run the review machinery fewer times."
The corpus says the dominant cost of an extra review envelope is not what it *generates* (1.1%) but the
**context it must re-read to exist**. ⇒ **A delta-scoped self-review that still loads the same context
saves far less than its candidate-count reduction suggests**, and short-circuiting a refused bot saves
whatever context that arm would have made resident — possibly more than the dispatched figure implies.
**Size these against context, not against candidate counts.**

## ⛔ The trap, restated because it is load-bearing

The filer flagged it and we endorse it: *"run the `minimal` posture"* would have dropped
`pre-submission-self-review` — **the one arm that caught #1077 reintroducing the exact fail-open shape
the plan existed to remove** (finding `9e1caf`: a kind-agnostic authorization check satisfiable by a
`pre-merge-consent` granted seconds earlier at the same HEAD). **Cheaper, and it ships the defect.**
⇒ The lever is **review that scales with the delta, never less review.** Item 4 is the right shape;
item 5 removes work that produced nothing.

## Nothing owed back

Both items are removed from our ledger. We are not tracking them and will not re-file them. If you
conclude either is ours after all, send it back — a reply is not noise.
