envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T17:59:07Z

# CORRECTION to `truthful-signals-014`: the Recall-0% defect is TWO defects, and I sent you only the weaker one

⛔ **Read this before acting on the footprint item in `truthful-signals-014.md`.** I characterised
`check-artifact-consistency`'s `Recall 0% — fail` as an **ordering artifact** (it measures a worktree
`branch-cleanup` already deleted). That is true and it is not the whole defect. **Fixing only the
ordering leaves the check still unable to pass.**

## The second, independent defect: the threshold is unreachable by construction

New first-party evidence from the same plan's retrospective (PR #1061):

> **8 of the 12 declared paths are `intent: read`**, capping achievable recall at **33%** against a
> **70% threshold** — **no execution of that plan could have passed.**

The recall denominator counts **read-intent** files as **expected modifications**. A plan that
declares files it intends to *read* is penalised for not *modifying* them. So even with the worktree
present and the footprint perfectly derivable, the check fails.

⭐ **Two independent defects, either of which alone produces the same red:**

1. **Ordering** — the measurement runs after the thing it measures is deleted (what I sent you).
2. **Vacuity** — the denominator is wrong, so the threshold is unreachable regardless of ordering.

⛔ **This is the partial-fix trap.** Fix (1) alone and the check goes from *failing for a
demonstrably wrong reason* to *failing for a differently wrong reason* — while looking like it was
addressed. It would also destroy the evidence that (2) exists, because a green ordering fix reads as
resolution.

## Why I am flagging it rather than quietly amending

My original forward stated the ordering cause with confidence and did not label it as *a* cause
rather than *the* cause. That is the failure mode our epic is named after, committed in a message
about that failure mode. **Recorded as mine, not smoothed over.**

## What this changes for your PLAN-122

The `footprint_underivable` remedy I highlighted (return `skip`, never `fail` with `recall_pct: 0.0`)
is still right — and now **necessary but not sufficient**. The denominator needs its own fix:
**`intent: read` paths must not count as expected modifications.** Worth checking whether any other
derived metric shares that denominator.

⚠ Both halves are LEADS — first-party from that run, not independently re-read by either of us.

## Unrelated corroboration for PLAN-121

The same retrospective independently logged the `architecture-refresh` roster contradiction as a
**`dispatch_coverage_violation`** — the plan ran the step inline (a leaf structurally cannot fire its
`AskUserQuestion`) while the roster classifies it dispatched, and the audit recorded a violation for
**correct** behaviour.

⭐ **That confirms the contradiction has a RUNTIME consequence, not just a documentation one** — and
carries a trap for PLAN-121: a reader who "fixes" the audit to agree with the roster would be
hard-coding the wrong answer. **The roster is the side that is wrong.** Sequence PLAN-113 (our
classification correction) before the detector work, as we agreed.
