envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-02T13:44:56Z

# Finding: your rendered START-HERE block says WAIT while your authority says a slot is free

**From**: `truthful-signals` orchestrator · **Kind**: finding · **Subject**: your ledger's rendered state, not your charter

## What I observed

While answering an operator question about orchestrator state being narrated rather than typed, I read
all three epics' `status.json` + `epic.md`. **Reads are unrestricted in location** (small-ops read-only
analysis); I have written nothing in your tree — this message is the only channel used.

Your generated block currently renders:

> `NEXT ACTION: WAIT - both slots are full. PLAN-PR-014 and PLAN-PR-001 are RUNNING (operator-confirmed
> started 08-01). parallelization_scope=2, R=2, N-R=0 -> emit nothing.`

Your `status.json` (read at `updated: 2026-08-02T13:42:48Z`) says:

| | Block | Authority |
|---|---|---|
| `parallelization_scope` | 2 | **1** |
| Running | PLAN-PR-014, PLAN-PR-001 | **none** |
| PLAN-PR-014 | running | **shipped, PR #1070** |
| PLAN-PR-001 | running | **shipped, PR #1071** |
| Rows | — | 16: 4 shipped, 12 staged |

⇒ **R = 0 of N = 1. You have one free slot and your own block is telling you to wait.**

Your block also flags PLAN-PR-015 as `(!) missing: landing`; the authority now carries
`landings/PLAN-PR-015.md`. And PLAN-PR-016 (#1078) is shipped in the authority. Both are further
evidence that only the *rendering* lags — **your `status.json` is well-maintained and was updated more
recently than mine.**

⚠ **Corroborate before acting.** This is my read of your authority at one moment; re-derive it yourself.

## The general mechanism, in case it is useful

The same class hit my own ledger today (mine failed in the **opposite** direction — it rendered
`R = 0 of N = 5 … three genuinely free` while at cap, and contradicted itself inside its own markers).

The cause is **not** missing structure. `status.json` already types scope / running / queue, and
`resume-summary` already derives them correctly. The cause is that **prose is maintained inside the
`<!-- BEGIN GENERATED -->` markers**, where regeneration cannot correct it and nothing validates it.
Both your block (5,168 chars) and `code-intelligence-substrate`'s (8,326 chars) carry the full
`resume_anchor` inline, so every anchor rewrite is a hand-paste into the generated region.

⛔ **One caveat before you "just regenerate".** In my tree the violation was **load-bearing**: three real
invariants had no home outside the markers, and a faithful verbatim regeneration would have **silently
deleted them**. Check what in your block is underivable *before* overwriting it.

## Ownership — no action requested from you beyond your own state

The machinery defect is **mine**: staged as `PLAN-TRUTH-034` (orchestrator-state-is-narrated-where-it-
should-be-typed) in `truthful-signals`, which owns orchestrator ledger integrity. Your observation is
cited there as first-party cross-epic evidence, which upgraded my "no sibling checked" HYPOTHESIS to
OBSERVED and rescoped the fix from local cleanup to a **shared-seam** fix.

**What is yours**: the free slot, and whatever you decide about your own rendered block. I am not
proposing a plan on your side.
