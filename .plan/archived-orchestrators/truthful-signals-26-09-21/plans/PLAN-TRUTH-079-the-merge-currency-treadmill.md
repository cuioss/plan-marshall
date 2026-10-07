# PLAN-TRUTH-079: the merge-currency treadmill — every re-stale is paid for in full, and the ledgers cannot see it

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from `metrics-011` (#1129) and `hook-002` (#1131), plus this orchestrator's own
> first-party check of when the obvious fix landed.

## Objective

Finalize re-runs `head_dependent` steps every time HEAD advances. Because settle-band fix commits and an
unconditional pre-merge rebase both advance HEAD, a finalize can re-run the same gates many times,
**mostly re-confirming identical verdicts** — and this now dominates the cost of a landing.

## OBSERVED — two plans, one 24-hour window, with figures

| Source | Observation |
|---|---|
| `hook-002` (#1131) | HEAD-advance step re-fires **under-report executions 5×** and emit **no `[STEP]` bracket** |
| #1131's own report | in ONE finalize: `lessons-housekeeping` **5×**, `plugin-doctor` **7×**, self-review **7×** — *"mostly re-confirming identical verdicts"* |
| #1131 cost | **109M billing-weighted for a 10-file fix; finalize was 70% of it** |
| #1129 cost | **134.4M billing-weighted**, both budget anchors tripped `error` — ⚠ on a figure the report labels a **floor** |
| `metrics-011` (#1129) | names the mechanism: *"the merge-currency treadmill — an unconditional pre-merge rebase re-stales every recorded verdict"* |
| #1129 deviation | the run **enqueued without the unconditional pre-merge rebase** (operator call; the merge queue re-tests anyway) — **an operator already routed around this defect** |

### ⛔⛔ THE OBVIOUS FIX ALREADY LANDED AND DID NOT HELP — verified first-party

**#1126 — *"perf(finalize): scope self-review and pre-push-gate re-runs to delta"* — merged as
`72982d3d4`, which is an ANCESTOR of both #1131 and #1129.** The re-fires still happened, 5×/7×/7×.

⇒ ⭐⭐ **Delta-scoping bounds the cost of EACH re-run; it does not reduce the NUMBER of re-runs.** Those
are two different levers and only the first is owned. ⛔ **This is the single most important framing in
the spec**: a reader who sees a landed perf fix on this surface will assume the problem is handled. **It
is not — the re-stale TRIGGER is unowned.**

### ⭐ And the cost is invisible to both ledgers

The re-fires **emit no `[STEP]` bracket**, so neither the step ledger nor the dispatch-boundary ledger
counts them (see `PLAN-TRUTH-045`, which owns that half). ⇒ **The most expensive thing a finalize does
is the thing its own instrumentation cannot see.** Any measurement of finalize cost taken from those
ledgers understates it, and understates it *more* the worse the treadmill gets.

## Deliverables

1. **D0 — GATE: enumerate what actually re-stales, and what each re-stale costs.** Which steps are
   `head_dependent`, what marks them stale, and how many re-fires occurred in #1131 and #1129. ⛔ **Do
   not scope a fix before the trigger set is enumerated** — #1126 optimised the wrong half precisely
   because the trigger set was never written down. ⚠ Publish the population.
2. **D1 — distinguish a HEAD advance that INVALIDATES a verdict from one that does not.** A settle-band
   docs commit does not invalidate a test verdict; a source commit does. ⭐ **This is the whole lever**:
   today every advance is treated as invalidating, which is safe and maximally expensive.
   ⛔ Fail toward re-running when the classification is uncertain — an unnecessary re-run costs tokens, a
   skipped necessary one costs correctness.
3. **D2 — settle the unconditional pre-merge rebase.** #1129's operator skipped it on the grounds that
   **the merge queue re-tests anyway**. ⛔ **Either that reasoning is right and the unconditional rebase
   should go, or it is wrong and the deviation was unsafe — the ledger cannot have it both ways.**
   Record the verdict either way; a deviation taken twice without a ruling becomes an unwritten policy.
4. **D3 — make the re-fires visible.** Coordinate with `PLAN-TRUTH-045`'s `[STEP]`/`[DISPATCH]` work
   rather than duplicating it: this plan needs the count to *prove its own effect*, and cannot measure
   itself with an instrument that under-counts the thing it is reducing.
5. **D4 — a before/after measurement on a real finalize**, publishing the re-fire count per step and its
   billing-weighted cost. ⛔ **A savings claim with no denominator is exactly what this epic files
   against others.**

**Five deliverables, one component (`phase-6-finalize` plus the settle-band machinery).**

## Claim Labels

- **OBSERVED (this orchestrator, first-party)**: that #1126 (`72982d3d4`) is an ancestor of both #1131
  (`6053382ab`) and #1129 (`2586ef00c`) — established from `git log origin/main`. **This is the load-
  bearing fact for the "the obvious fix did not help" framing and it is not second-hand.**
- **REPORTED (the two plans, first-party to them, NOT re-derived here)**: the 5×/7×/7× counts; 109M and
  134.4M billing-weighted; the 70% finalize share. ⚠ **Re-derive before pinning any target to them** —
  and note #1129's own report labels its figure a **floor**, so the overrun direction is known and the
  magnitude is not.
- **HYPOTHESIS**: that a HEAD advance can be classified as invalidating-or-not with acceptable accuracy.
  ⛔ **Genuinely open, and D1 depends on it.** Confirm/refute against the settle-band step definitions
  and their declared inputs — **verify-at-outline**.
- ⛔ **NOT ESTABLISHED**: that any re-fire ever produced a *different* verdict from its predecessor.
  *"Mostly re-confirming identical verdicts"* is the reporting plan's wording — **"mostly" is not
  "always", and the exceptions are exactly what D1 must not break.**

## Expected Surface

- **HYPOTHESIS**: `phase-6-finalize` — the `head_dependent` step declarations and the re-stale trigger
- **HYPOTHESIS**: the settle-band definition (which steps may commit, and what their commits invalidate)
- **HYPOTHESIS**: `workflow-integration-git` — the unconditional pre-merge rebase, for D2
- ⛔ **NOT** the `[STEP]`/`[DISPATCH]` emitters — that is `PLAN-TRUTH-045`'s surface; D3 consumes it.

## Dependencies and Sequencing

- ⛔⛔ **SERIALIZE AFTER `PLAN-TRUTH-045`, or accept that D4 cannot measure itself.** `-045` owns the
  instrumentation that under-counts re-fires; without it, this plan's before/after is taken with the
  broken instrument. ⭐ **Running `-045` first is strongly preferred** — and if this plan runs first, D4
  must state plainly that its measurement carries the known downward bias rather than reporting a clean
  number.
- ⚠ Touches `phase-6-finalize`, which `PLAN-TRUTH-064` and `PLAN-TRUTH-050` also touch. **Serialize;
  check live file lists at emit.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-079-the-merge-currency-treadmill.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
