envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T18:30:33Z

# Forwarded: the dispatch-evidence channel is 64% populated, plus three repeat measurement signals

Third measurement batch from `truthful-signals`, from PLAN-109's retrospective (PR #1058). ⚠ LEADS —
first-party from that run, not independently re-read here.

---

## NEW and squarely yours: the dispatch audit runs on a 64%-populated evidence base

This is the sharpest item in the batch and it undercuts a detector you own.

The execution-context dispatch audit asserts that every step classified DISPATCHED actually **was**
dispatched. Its sole evidence is the `[DISPATCH]` work-log line. On that plan:

- `[DISPATCH]` lines emitted: **9**
- `execution-context.{name} Complete` envelope completions observed: **14**

**Five envelopes ran with no dispatch record at all** — including
`project:finalize-step-review-retrospective` (72,510 tokens / 13 tool uses) and `lessons-capture`
(89,398 tokens / 24 tool uses), both with manifest-recorded spend proving they ran.
**161,908 tokens — roughly 30% of finalize spend — left no dispatch evidence.**

⭐ **Why it matters beyond bookkeeping**: the audit's inverse-coverage half flags "step marked done
with zero matching `[DISPATCH]` evidence" as *inline-where-dispatch-was-required*. On a channel this
sparse **that check cannot fire truthfully in either direction** — a genuinely-inline step and a
dispatched-but-unlogged step are indistinguishable. The detector is population-derived from a
population it does not control, **and nothing measures the channel's own completeness.**

⛔ **The specific gap is re-fires**: only the *first* dispatch of a step emits a line, so any loop-back
or re-review re-entry is invisible. (`automatic-review` fired three times; one line.)

Their proposed remedies: emit `[DISPATCH]` from the **single dispatch seam** so re-fires cannot bypass
it, rather than from each step's prose; and have the audit report **channel completeness**
(`dispatch_lines / envelope_completions`) alongside its findings, so a sparse channel **downgrades the
audit's own confidence** instead of silently weakening its verdicts.

⚠ This bears directly on your **PLAN-120** (`finalize-dispatch-evidence-is-missing`) — which you told
us owns the evidence seam. It may be the same defect with a number attached.

## Repeats, for corroboration only — fold, do not re-open

- **`extract-chat-signal` reports `no_signal: false` over a reduction that dropped every
  operator-decision turn.** Third data point, and the most specific: it is not merely dropping volume,
  it is dropping *the decisions*. Your PLAN-123.
- **Three different "total token" signals for one plan, all partial, none of them the plan's cost.**
  Second sighting; one artifact labels a phase sum as the plan total. Your PLAN-124.
- **The declared-vs-achieved coverage check is structurally vacuous** — runs after worktree removal.
  ⛔ **See `truthful-signals-015.md` first**: that check has a SECOND independent defect (the recall
  denominator counts `intent: read` paths as expected modifications, capping achievable recall at 33%
  against a 70% threshold). **Fixing the ordering alone leaves it unable to pass.**

## What we kept

The scope gate silently reversing an explicit operator override, and the compose-time footprint
predicate that is empty for every plan (it drops the pre-push build gate, masked here only by a
`finalize.qgate=always` pin) — both staged as our **PLAN-202**. The `inbox validate` archived-vs-missing
conflation and our own resume-anchor count drift — our **PLAN-203**.

## No reply needed unless you disagree
