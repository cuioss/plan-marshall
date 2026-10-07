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

# The merge-currency treadmill — every re-stale is paid for in full, and the ledgers cannot see it

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

Finalize re-runs its head-dependent steps **every time HEAD advances**. Because settle-band fix commits
**and** an unconditional pre-merge rebase both advance HEAD, one finalize can re-run the same gates many
times, **mostly re-confirming identical verdicts** — and this now **dominates the cost of a landing**.

Observed across two plans in one 24-hour window:

- In **one** finalize: a housekeeping step ran **5×**, the structural lint **7×**, the self-review **7×**.
- One plan's landing cost **109M billing-weighted for a 10-file fix — with finalize at 70% of it.**
- The other cost **134.4M billing-weighted**, tripping both budget anchors ⚠ **on a figure its own report
  labels a FLOOR** — so **the overrun direction is known and the magnitude is not.**
- The named mechanism: *"an unconditional pre-merge rebase re-stales every recorded verdict."*
- ⭐ **An operator already routed around it**, enqueueing without the unconditional rebase on the grounds
  that **the merge queue re-tests anyway.**

## ⛔⛔ THE OBVIOUS FIX ALREADY LANDED AND DID NOT HELP

A change scoping the self-review and pre-push gate re-runs **to the delta** merged **before both** of
those runs. **The re-fires still happened, 5× / 7× / 7×.**

⇒ ⭐⭐ **Delta-scoping bounds the cost of EACH re-run; it does not reduce the NUMBER of re-runs.** **Those
are two different levers and only the first is owned.**

⛔ **This is the single most important framing in the plan.** A reader who sees a landed performance fix
on this surface **will assume the problem is handled. It is not — the re-stale TRIGGER is unowned.**

## ⭐ And the cost is invisible to both ledgers

The re-fires **emit no step bracket**, so **neither the step ledger nor the dispatch-boundary ledger
counts them.**

⇒ **The most expensive thing a finalize does is the thing its own instrumentation cannot see.** ⛔ **Any
measurement of finalize cost taken from those ledgers understates it — and understates it MORE the worse
the treadmill gets.**

## Goal

A HEAD advance that cannot invalidate a verdict does not re-run the gates that produced it; the
unconditional pre-merge rebase has a recorded ruling; and the re-fire count is visible enough for the
saving to be proven rather than asserted.

## Deliverables

1. **D0 — GATE: enumerate what actually re-stales, and what each re-stale costs.** Mutates nothing. Which
   steps are head-dependent, what marks them stale, and how many re-fires occurred in the observed runs.
   *Done when:* the trigger set is enumerated with its population published.
   ⛔ **Do not scope a fix before the trigger set is enumerated.** ⭐ **The landed performance fix
   optimised the wrong half precisely because the trigger set was never written down.**
2. **D1 — Distinguish a HEAD advance that INVALIDATES a verdict from one that does not.** A settle-band
   documentation commit does not invalidate a test verdict; a source commit does.
   *Done when:* the classification exists and is applied at the re-stale decision.
   ⭐ **This is the whole lever**: today **every** advance is treated as invalidating — **safe, and
   maximally expensive.**
   ⛔ **Fail TOWARD re-running when the classification is uncertain.** An unnecessary re-run costs tokens;
   **a skipped necessary one costs correctness.**
3. **D2 — Settle the unconditional pre-merge rebase.** An operator skipped it on the grounds that the
   merge queue re-tests anyway.
   *Done when:* **the verdict is recorded either way.**
   ⛔ **Either that reasoning is right and the unconditional rebase should go, or it is wrong and the
   deviation was unsafe — the record cannot have it both ways.** ⭐ **A deviation taken twice without a
   ruling becomes an unwritten policy.**
4. **D3 — Make the re-fires visible.** ⛔ **Coordinate with the sibling plan that owns the step and
   dispatch emitters rather than duplicating it.**
   *Done when:* the re-fire count is obtainable.
   ⭐ **This plan needs the count to prove its own effect, and cannot measure itself with an instrument
   that under-counts the thing it is reducing.**
5. **D4 — A before/after measurement on a real finalize**, publishing **the re-fire count per step and
   its billing-weighted cost**.
   *Done when:* both numbers are published with their population.
   ⛔ **A savings claim with no denominator is exactly what this epic files against others.**

Five deliverables, one component.

## Out of scope

- ⛔ **The step and dispatch emitters themselves.** A sibling plan owns them; **D3 consumes that work, it
  does not redo it.**
- **Further delta-scoping of individual gates.** ⛔ **That lever is already pulled and did not move the
  number.** Pulling it harder is the predictable wrong move here.
- **Changing what any gate checks.** This plan changes **how often** gates run, never **what they
  verify** — a saving bought by weakening a gate is not a saving.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` — the head-dependent step declarations
  and the re-stale trigger.
- The settle-band definition — which steps may commit, and what their commits invalidate.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/**` — the unconditional pre-merge
  rebase, for D2.
- Tests.

⛔ **NOT the step/dispatch emitters** — that is the sibling plan's surface.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The delta-scoping change is an ancestor of both observed runs | OBSERVED | **git history — first-party, and NOT second-hand.** ⭐ **This is the load-bearing fact for the whole "the obvious fix did not help" framing, and it is verifiable from this clone in one command** |
| A single finalize re-ran three steps 5× / 7× / 7× | HYPOTHESIS | ⛔ **reported by those runs, under `.plan/`, NOT re-derived.** ⚠ **Re-derive before pinning any target to them** |
| Landing costs of 109M and 134.4M billing-weighted, with finalize at 70% | HYPOTHESIS | same caveat. ⚠ **One report labels its own figure a FLOOR** — so the direction is known and the magnitude is not. ⛔ **Do not quote either as a measured total** |
| An unconditional pre-merge rebase re-stales every recorded verdict | HYPOTHESIS | the rebase site and the re-stale trigger — **by symbol. Checkable here** |
| The re-fires emit no step bracket | HYPOTHESIS | the emitter — ⭐ **and it is why every ledger-derived cost figure for finalize is a floor** |
| A HEAD advance can be classified invalidating-or-not with acceptable accuracy | HYPOTHESIS | ⛔ **GENUINELY OPEN, and D1 depends on it.** Confirm against the settle-band step definitions and their declared inputs |
| Any re-fire ever produced a DIFFERENT verdict from its predecessor | HYPOTHESIS | ⛔ **NOT ESTABLISHED.** ⭐ *"Mostly re-confirming identical verdicts"* was the wording — **"mostly" is not "always", and the exceptions are exactly what D1 must not break** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D1's uncertain case must be verified to re-run, not to skip.** The fail-toward direction is the
  whole safety property, and it is the one a performance-motivated change is most likely to get backwards.
- ⛔ **D4 must publish a denominator.** ⭐ If this plan reports a saving without one, it has committed the
  defect the epic exists to close, in the plan whose subject is cost truthfulness.
- ⚠ **If the sibling instrumentation plan has NOT landed, D4 must state plainly that its measurement
  carries the known downward bias** — rather than reporting a clean number from a broken instrument.
- **D2's ruling belongs in the report whichever way it goes.** An unrecorded deviation repeated twice is
  already an unwritten policy; a third time makes it a convention nobody chose.
- Python, documentation, and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔⛔ **Sequencing: run AFTER the sibling plan that owns the step and dispatch instrumentation, or accept
  that D4 cannot measure itself.** ⭐ **Running that one first is strongly preferred.**
- ⚠ This touches the finalize surface that at least two other plans in this epic also touch. **Serialize;
  check live file lists before starting.**
- ⛔ **Do not go looking for the orchestrator spec, the run reports, the inbox messages, or any landing
  record.** They live under `.plan/`, which is git-ignored and absent from this clone. ⭐ **The one fact
  that carries the plan's framing — that the performance fix predates both runs — is verifiable from git
  right here.**
