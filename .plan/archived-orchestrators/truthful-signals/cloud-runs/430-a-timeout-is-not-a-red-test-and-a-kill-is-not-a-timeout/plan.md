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

# A timeout is not a red test, and a harness kill is not a timeout

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

A build that does not finish produces **three distinguishable conditions** — a **harness kill**, a
**daemon adaptive-budget timeout**, and a **genuinely failing test** — and the consuming gates collapse
them. **Each collapse degrades a gate in a different direction.**

Reported across two plans:

- *"A build-daemon adaptive-budget **timeout is not a red test** — reading it as one **manufactures a
  failure**."* One run substituted **scoped tests for the whole-tree run** after the budget timed out
  **twice**, and correctly recorded **a timeout status, not a red test**.
- *"Separate a harness-killed background build from a real budget timeout before degrading a gate."*

### ⭐⭐ A self-correction narrows the defect, and the narrowed version is the interesting one

The second report, **as first written**, implied the discriminator was **absent**. **Its own filer then
corrected it**: the discriminator **was present and consulted** — the daemon logs were read, and both
runs reported a timeout status at around 642 s and 618 s.

⇒ **The defect is NOT "we cannot tell a kill from a timeout." It is that knowing the difference did not
change what the gate did.**

⭐ **A discriminator that is read and then not acted on is worth LESS than an absent one, because it makes
the gate LOOK discriminating.**

⛔ **Scope accordingly: this plan must NOT re-add a discriminator that already exists.**

### ⛔ The subset/superset inversion is the sharpest single fact

The scoped test command **times out at ~642 s** while the full verify — **which contains it** —
completes in **215–537 s**.

⇒ **A learned per-command budget that can time out on a strict SUBSET of a command that succeeds is not
measuring what it claims to.** ⭐ **This is falsifiable and cheap to re-check**, and it is the fact most
likely to identify the real mechanism — a mis-keyed budget lookup, a cold-versus-warm cache asymmetry, or
a budget learned from a different command shape.

## Goal

Every consuming gate can tell a harness kill from a budget timeout from a red test, and acts differently
on each — and the budget that produced the subset/superset inversion is understood rather than merely
raised.

## Deliverables

1. **D0 — GATE: enumerate what the daemon and the harness ALREADY emit for each of the three
   conditions**, and **which consumer reads which field**. Mutates nothing.
   *Done when:* the emitted vocabulary and the per-consumer reads are both enumerated, with the
   population published — **how many consuming gates, and how many read the status field.**
   ⛔ **At least one discriminator EXISTS and IS CONSULTED. Building a second one is the failure mode this
   gate exists to prevent.**
2. **D1 — Make the three conditions distinguishable AT EVERY CONSUMING GATE**, not just in the log.
   *Done when:* **a timeout cannot be presented as a test failure, and a harness kill cannot be presented
   as a timeout.**
   ⭐ Per the standing rule, **an unresolvable case is `indeterminate`, never folded into either
   neighbour.**
3. **D2 — Settle the subset/superset inversion.** Why does the scoped command exceed its learned budget
   while the superset does not?
   *Done when:* the mechanism is named.
   ⛔ **DIAGNOSE BEFORE ADJUSTING.** ⭐ **Raising the budget would hide the mechanism** — and this epic's
   standing rule is that **a correction applied to an error whose sign is unknown launders a suspect
   figure into a "corrected" one.**
4. **D3 — Regression tests with matched controls, each verified RED pre-fix.**
   - A **genuine red test** must **still fail** the gate.
   - A **timeout** must **not**.
   - A **harness kill** must **not**.
   *Done when:* all three hold.
   ⛔ **The red-test control is the one that stops this fix from making every non-finish benign** — which
   would be a far worse gate than the one being fixed.

Four deliverables, one component family.

## Out of scope

- ⛔ **Re-adding a discriminator that already exists.** See D0. The correction above is the reason this
  boundary is stated.
- ⛔ **The test suite under measurement.** This plan changes how a non-finish is **classified**, never
  what the build runs.
- **Raising the learned budget as the fix.** ⛔ Explicitly rejected in D2 — it would close the symptom and
  bury the mechanism, and the mechanism is the falsifiable part.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-build-server/**` — the daemon's result and status
  construction. **D0 names the symbol.**
- `marketplace/bundles/plan-marshall/skills/build-pyproject/**` — the learned-budget lookup, for D2.
- The consuming finalize gates that degrade on a non-green build.
- Tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Two runs reported a daemon timeout status at ~642 s and ~618 s | HYPOTHESIS | ⛔ **run logs under `.plan/`, NOT reachable from this clone and NOT re-derived.** ⚠ **A learned budget is by definition a MOVING VALUE — re-verify the timings rather than pinning to them** |
| The scoped command times out while the superset completes in less time | HYPOTHESIS | ⭐ **falsifiable and cheap to re-check by running both.** **The single most useful check in this plan** |
| One run substituted scoped tests after two timeouts, recording a timeout rather than a red test | HYPOTHESIS | same provenance caveat — ⭐ **its significance is that the run got it RIGHT**, which is what localises the defect to the gates |
| The discriminator was present and consulted | HYPOTHESIS | ⛔⛔ **LOAD-BEARING FOR SCOPE.** ⭐ **The uncorrected version of the original report is NOT evidence for this plan and must not be cited as such** — the correction is part of the evidence, not a caveat on it |
| The three conditions are collapsed at a CONSUMING GATE rather than at the daemon | HYPOTHESIS | the daemon's result construction and each gate's read — **D0 is exactly this** |
| Any gate ever produced a WRONG MERGE DECISION from the collapse | HYPOTHESIS | ⛔ **NOT ESTABLISHED.** The observed substitution was an operator-visible deviation, **correctly recorded**. **Do not claim damage taken** |
| Every consuming gate is identified | HYPOTHESIS | ⛔ asserted **completeness** — the absence-shaped half. **Derive the consumer set; a list produced by looking is a sample** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D3's red-test control is the safety test.** Every other test here confirms the gate stops failing
  on non-failures; **only that one confirms it still fails on failures.**
- ⛔ **D2's diagnosis must be a named mechanism, not an adjustment.** "We raised it and it stopped" is
  the outcome this deliverable forbids.
- **D0's population must be published**: gates counted, gates reading the status field. ⭐ A gate that
  reads no status field is a gate D1 must reach, and it will not appear in any list built from the ones
  that do.
- **D1 must be verified per gate, not once.** The defect is distributed across consumers; a fix verified
  at one gate says nothing about the others.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⭐⭐ **The self-correction is worth carrying as a method, not just as a fact.** A filer re-read their own
  report, found it implied an absence that was not there, and corrected it — which **narrowed the defect
  from "no discriminator" to "the discriminator changes nothing."** ⭐ **The narrowed version is both truer
  and more actionable**, and the plan would have been scoped wrongly without it.
- ⚠ **Sequencing: adjacent to a sibling plan in the same bundle, on a different surface.** ⛔ That one was
  **withheld pending an operator repair**; if it is released first, **serialize.**
- ⛔ **Do not go looking for the orchestrator spec, the run logs, the inbox messages, or any landing
  record.** They live under `.plan/`, which is git-ignored and absent from this clone. ⭐ **The
  subset/superset check is reproducible here from scratch** — that is why it leads the evidence.
