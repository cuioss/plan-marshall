envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T10:53:05Z

# FORWARDED — late-phase marginal cost is dominated by CONTEXT SIZE, not step complexity

**Forwarded from `truthful-signals` 2026-07-29** under the inbound routing rule (cost measurement of
our own runs). ⚠ Leads, not facts — but the figures below are **read directly from the archived
plan's `metrics.md` and `logs/work.log`**, not message-supplied.

## Source

PLAN-111 / PR #1047, archived at
`.plan/local/archived-plans/2026-07-29-self-ingested-reply-non-terminating-barrier-loop/`.

## The question that produced this

The orchestrator claimed re-review retries were "a measurable cost centre". The operator challenged
it: **retries are mechanical, so why would they be expensive?** The challenge was correct and the
original claim mis-attributed the cause.

## What the numbers actually show

| Phase | Dispatched tokens | **Inline main-context tokens** | Tool uses | cache_read |
|---|---:|---:|---:|---:|
| 2-refine | 226,121 | 584,194 | 71 | 21.5 M |
| 3-outline | 405,177 | 944,382 | 122 | 35.0 M |
| 4-plan | 351,392 | 910,954 | 86 | 22.3 M |
| 5-execute | 533,998 | 713,698 | 138 | 57.1 M |
| **6-finalize** | **1,648,020** | **4,960,712** | **429** | **246.3 M** |

Three findings:

1. **The headline understates the run.** `3,205,944` is the **dispatched accumulator only**. Inline
   main-context cost is tracked separately (*"surfaced alongside the dispatched total, never
   replacing it"*) and sums to **~8.1 M across phases**, 4.96 M of it in finalize. ⚠ **Any
   anchor comparison using the headline is comparing against a partial figure** — and the
   orchestrator's own "2.5× over anchor" claim was computed on it. ⚠ **Unknown, and it matters:
   whether the 1.3 M anchor is itself dispatched-only or all-in. Establish before quoting a ratio.**
2. **Marginal cost scales with WHERE a step runs, not WHAT it does.** Finalize shows **246 M
   cache_read across 429 tool uses** — on the order of **~0.5 M tokens re-read per tool call**. Late
   in a long phase, *every* additional step pays the full accumulated-context toll. **A mechanical
   step late in finalize costs far more than the same step early**, and nothing in a per-call view
   reveals that.
3. **A loop-back is not a poll.** From `work.log`, each iteration re-dispatched real LLM envelopes —
   `automatic-review`, `wait-region-unified-triage`, `verification-feedback` (level-3) — and
   **iteration 2 transitioned `6-finalize → 5-execute`** with a level-4 dispatch. Iterations at
   08:26, 08:31, 09:37; finalize spanned 07:36→10:22. ⭐ **The bounded guard worked** — it stopped at
   3/3 and reported *"required bot coderabbit still refused_awaitable, pr-agent absent for HEAD
   3a4d11282"* rather than looping on.

## Why this belongs to this epic

**PLAN-77 `aggregate-cost-invisible-to-per-call-ceiling` is exactly this defect, and this is direct
evidence for it.** A per-call ceiling cannot see that the same call costs ~0.5 M tokens at tool-use
#400 and a fraction of that at tool-use #40. ⇒ **PLAN-77's D1 should treat context position as a
first-class cost dimension**, not only call size.

⚠ **It also bounds PLAN-99's shipped exploration-share instrument**: finalize carried **1.88 MB of
exploration result bytes** — the largest of any phase, larger than outline's 534 KB — in a phase that
is supposedly mechanical. Exploration share alone will not surface this; the *interaction* between
exploration volume and context position is what drives the cost.

## The remedy this evidence argues FOR, and against

- ⛔ **Against "retry refusing bots less"** — that trades review coverage for cost and treats the
  occasion as the cause.
- ✅ **For**: run retry/verification cycles in a **fresh envelope** rather than the accumulated main
  context; keep bounded loop-backs (**demonstrably working here**); and reduce finalize's own
  exploration volume, which is what inflates the context every later step must re-read.
