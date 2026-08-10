> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The dominant script cost is invisible to a per-call ceiling

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

Two hot paths — a session/terminal-title seam and a pre-tool-use hook — are invoked on the order of
**a hundred thousand times** across the corpus and together account for the **majority of all
recorded script wall-clock**. At a fraction of a second per call, **neither ever trips the slow-call
ceiling**, and neither is visible in any per-plan view because the cost is spread across every plan.

⭐ **The instrument is honest and the question is unanswerable with it.** A per-call ceiling answers
*"is any single call pathological?"* It is **structurally incapable** of answering *"what dominates
total time?"* A cost that is a fraction of a percent of the ceiling, repeated a hundred thousand
times, is **invisible by design, not by oversight**.

⛔⛔ **READ THE DENOMINATOR BEFORE TREATING THIS AS A TOKEN LEVER — this is binding.** The share above
is **wall-clock over script invocations**. This epic's standing, first-party-verified result is that
**the overwhelming majority of billing weight is CONTEXT, not generation and not wall-clock.**
⇒ **The two are measured in different currencies and this figure does NOT convert into a
token-reduction lever on its own.** Re-quoting a wall-clock share as a cost share is precisely the
partition-quoted-as-a-whole archetype this epic exists to catch.
⭐ **If the restatement shows the seam is cheap in tokens and expensive in seconds, that is still a
real and reportable finding** — it is an operator-latency finding, not a billing one. **Say which.**

## ⭐ And there is a second cost dimension a per-call view cannot see

Evidence from an archived run: a late phase showed on the order of **half a million cached-read
tokens per tool call**, an order of magnitude above earlier phases. ⇒ **Marginal cost scales with
WHERE a step runs, not only with WHAT it does.** A mechanical step late in a long phase costs far
more than the identical step early, and **nothing in a per-call view reveals it.**

⇒ **Context position is a first-class cost dimension**, not a refinement of call size.

## Goal

Aggregate cost is reportable — a dominant-but-fast script is visible beside the slow-call ceiling —
the wall-clock finding is restated in the currency that actually drives cost, and whichever lever
turns out to be genuinely reducible is reduced without regressing the contracts that seam carries.

## Deliverables

1. **D1 — GATE: verify the numbers first-party, and restate them in the billing currency. Mutates
   nothing.**
   Re-derive the call counts, cumulative durations and share-of-total from the execution-log corpus.
   ⛔ **Do not scope from a summary** — the whole point of this plan is that unverified aggregate
   numbers are what hid the cost in the first place.
   ⛔ **Then restate against billing weight**, per the denominator warning above, and state plainly
   whether this is a latency finding or a cost finding.
   Then settle two separable questions: **(a) observability** — what aggregate view must exist so this
   class is visible next time; **(b) reduction** — which path is actually reducible and by what
   mechanism (caching, debouncing, short-circuiting a no-op, firing on fewer events).
   ⚠ **Do not assume both are reducible**: a hook that must run on every tool use may be irreducible in
   count and only reducible in per-call cost.
   *Done when:* the figures are first-party, the currency is stated, and (a) and (b) are decided.
   ⚠ **Corpus reachability**: the execution logs live under a **machine-local, git-ignored** path that
   is **not present in this clone** ⛔ **— do not search for it.** If unreachable, **ship D2 (which is
   a code change) and report D1's re-derivation and D3 blocked on corpus availability.** ⛔ Do not
   optimise a path whose cost this run could not measure.
2. **D2 — aggregate cost is reportable.** Add a roll-up: cumulative wall-clock and call count per
   script, ranked by share of total, so a dominant-but-fast script is visible.
   ⛔ **The per-call ceiling stays — this is an addition, not a replacement**, and the deliverable must
   state how the two are read together.
   ⭐ **Include context position** as a reportable dimension per the second finding above.
   *Done when:* the roll-up ranks a many-fast-calls script above a few-slow-calls script.
3. **D3 — reduce the largest verified lever**, for whichever path D1 found reducible.
   ⛔ **Hard invariant: no behavioural regression in the terminal-title / session-binding contract.**
   Prior work fixed title delivery onto the delivering channel and shipped a wait-mechanism stamp;
   **neither may regress.** ⚠ **If the only available reduction risks either contract, prefer
   observability alone and record why.**
   *Done when:* the reduction lands with the contract asserted, or the run records why it was not
   attempted.
4. **D4 — tests.**
   (a) the roll-up ranks many-fast above few-slow — **the assertion that fails against today's
   reporting**;
   (b) the reduction preserves the title/session contract — **assert delivery, not merely absence of
   error**;
   (c) a regression pin on whichever quantity D1 made the target.

Four deliverables with D1 a gate — under the split guard.

## Out of scope

- **Reconciling the several disagreeing token totals.** ⛔ Excluded — a sibling plan owns the ledger
  disagreement, and **reconciliation without truncation markers just produces a fourth number.** What
  belongs here is the *cost-visibility* consequence.
- **Closing the late-phase metrics row.** Excluded — another plan owns that call-site omission.
  ⛔ **Do not ship two fixes for one omission**; if that lands first, **re-measure before scoping**,
  because the magnitude this plan reasons about may already have changed.
- **The phase-window re-opening on loop-back.** Excluded for the same reason — a sibling owns the
  window lifecycle; this plan owns the visibility consequence.
- **Treating the wall-clock share as a token lever.** ⛔ Excluded until D1's restatement says
  otherwise. This is the plan's single largest interpretive risk.

## Expected surface

- The session-seam implementation and its hook-invocation site. **HYPOTHESIS** — the exact files
  depend on D1's reduction choice; verify at outline.
- The pre-tool-use hook registration and implementation. **HYPOTHESIS**, verify at outline.
- The execution-logging or reporting surface that hosts the roll-up — likely the logging skill or the
  audit reporting layer. **HYPOTHESIS**; D1 decides which owns it.

⚠ **This surface is HYPOTHESIS-heavy by design** — D1's verification determines it. **That makes the
plan a poor candidate for a light planning route; escalate the routing deliberately.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The two hot paths dominate recorded script wall-clock at roughly a hundred thousand invocations | **CLAIMED by an audit roll-up — NOT first-party** | ⛔ **D1 re-derives it.** Every number here is a **LEAD**. |
| A per-call ceiling is structurally incapable of surfacing this class | **OBSERVED (structural reasoning)** | Read the ceiling's predicate. This claim needs no corpus: it follows from what the detector computes. |
| The seam is a material share of **billed** cost | **HYPOTHESIS — and it is the claim that would matter** | ⛔ **Unverified.** Confirm against per-invocation **context** cost, **not** against the wall-clock ledger — that ledger is the source of the currency mismatch. |
| Marginal cost scales with context position, not only call size | **OBSERVED on one archived run** | Machine-local record ⛔ **not reachable here — do not look for it.** The *dimension* is the deliverable; D2 makes it reportable rather than asserting a figure. |
| A headline token figure can be a partial accumulator while a separate inline cost is tracked elsewhere | **OBSERVED** | ⛔ **Establish whether any budget anchor being compared against is itself partial or all-in BEFORE quoting any ratio.** |
| Budget anchors cannot distinguish honest, gate-driven scope growth from waste | **HYPOTHESIS** | ⭐ Worth stating plainly: an overrun caused by a gate correctly finding more sites than the request named is **the plan working as designed.** ⛔ **An anchor that flags both is not a cost signal, it is a noise source** — and it trains readers to dismiss overruns, which is exactly when a real one goes unexamined. |

## Verification

- **D1's currency restatement is the deliverable's integrity check.** A run report that quotes the
  wall-clock share without saying which currency it is in has failed this deliverable regardless of
  what else shipped.
- **D4(a) must fail against today's reporting.** Record the pre-fix failure.
- **D4(b) asserts delivery**, not the absence of an exception — a title contract can regress silently
  while nothing raises.
- **If D3 is skipped, the reason is recorded.** ⭐ The observability half is the durable deliverable and
  **must not be dropped if the reduction half shrinks or empties.**
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why the reason it went unnoticed matters more than the number.** This is the clearest example in
  the epic that a **truthful** instrument can still leave the dominant fact unreported.
- **Disjointness.** Presumed to touch the runtime and hook layer — ⚠ **re-check against the shipped
  session-binding surface before running anything alongside it.**
