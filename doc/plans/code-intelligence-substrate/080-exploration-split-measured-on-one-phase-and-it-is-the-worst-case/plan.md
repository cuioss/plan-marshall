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

# Get the exploration split on the phases that decide the epic's value case

**Epic:** code-intelligence-substrate
**Branch prefix:** chore

## Problem

This epic rests on a premise: that exploration of the **codebase** is the addressable cost, and a
code-intelligence substrate can remove most of it. The instrumentation built to check that premise
separates **index-answerable** exploration (which a substrate could plausibly remove) from
**doc-residency** (documents a step must read to execute at all) and an **unattributed** remainder.

⛔⛔ **The measurement says the epic may be aimed at the smaller half.** On the first record covering
all six phases, the index-answerable share was a small minority of exploration bytes while
doc-residency was the clear majority — roughly a 1:4 ratio — and exploration is about three quarters
of all tool-result bytes. If that generalises, the substrate's addressable share is an order of
magnitude below the roadmap premise.

⛔ **And the framing this plan was staged with has itself been half-refuted, which is why it must not
be carried forward.** The original reasoning was that the one instrumented phase was the *worst case*
for doc-residency (a workflow-document-driven phase where every step reads its own standard), and
that the phases where a substrate would help most had no data. The six-phase record contradicts that:
the **refine** phase is the worst case, not finalize — refine is a **documentation-reading** phase,
not the codebase-orientation phase the framing assumed. The confirmed half is that the **execute**
phase is the best case for a substrate, as predicted.

⇒ **The honest state: the value case is neither confirmed nor refuted, and it is now measurable on a
population rather than on one plan.** Treating either the small figure or the original large one as
the answer would be the same error twice.

## Goal

The per-phase exploration split exists over a **declared population** of instrumented plans, each
figure carrying its phase and its population size; the unattributed remainder is classified far
enough that the addressable share is a real estimate rather than a lower bound; and the epic's own
value case is restated against what the measurement says, in whichever direction it points.

## Deliverables

1. **D0 — GATE: is an instrumented population reachable in this clone at all?**
   The records this plan measures are archived run artifacts under a **machine-local, git-ignored**
   path. ⛔ **That path is not present in this clone and must not be searched for.**
   *Done when:* the run has established from git-reachable evidence either (a) a population it can
   measure, or (b) that none is reachable here.
   ⛔ **On (b): HALT and report the plan blocked on corpus availability.** Do **not** substitute a
   hand-assembled corpus, and do **not** proceed on a single record — a measurement plan that runs on
   n=1 reproduces the exact defect it exists to correct.
2. **D1 — collect the split across all six phases. Mutates nothing.**
   Report the per-phase index-answerable / doc-residency / unattributed split **with the population
   size**, and state how many plans contributed to **each phase** (they will differ).
   ⛔ **Do not pool phases into one headline** — the whole point is that the phases differ sharply.
   ⛔ **Report the per-phase RANGE for the exploration share, never a single band.** A previously
   published band was already found false at one phase; generalising a phase-specific figure is this
   plan's founding concern and it must not commit it.
   ⛔ **Do not carry the worst-case framing into the scoping** — it is refuted; see Problem.
   *Done when:* every reported figure carries its phase and its contributing-plan count.
3. **D2 — classify the unattributed remainder, byte half only.**
   The remainder is large enough to flip the conclusion by itself. ⛔ **Until it is classified, the
   addressable share is a LOWER BOUND and must be reported as such**, never as the figure.
   ⛔ **Scope: the *byte* remainder only.** A different quantity — the unattributed share of cached
   reads — is a **different population with a different denominator**, is far larger, and is owned by
   a sibling plan. **Say so explicitly; do not silently widen this deliverable to cover it.**
   *Done when:* the remainder is either classified into the existing buckets or reported with a named
   reason it cannot be.
4. **D3 — state the epic's value case against the measurement, in either direction.**
   If the addressable share is small on the phases that matter, **say so and re-scope the epic.**
   ⭐ **A measurement programme that cannot return an unwelcome answer is not one.**
   ⚠ A sibling plan was staged to own the doc-residency bucket; **reconcile with it rather than
   re-deriving it.**
   *Done when:* the epic's written value case matches D1's evidence, and an independent cold reader
   (see Verification) reports it read the epic as aimed where the measurement points.
5. **D4 — every figure names its population, its phase, and its sampling point.**
   *Done when:* no figure in the output stands without those three.

Five deliverables with D0 a gate — under the split guard.

### Two schema obligations D1 inherits, both breaking

1. **The partiality keys were RENAMED with no dual-key shim.** Archived records still carry the old
   keys. ⇒ **Implement a three-state read** (`current` / `old-schema` / `pre-migration`) and **report
   `old-schema` explicitly**. ⛔ *Defaulting an old-schema record is how a bare rename manufactures a
   clean verdict out of an absent key* — this project's own archetype.
2. **The per-dispatch context-load columns no longer default to zero** when their flag is omitted; an
   unmeasured column carries a literal `unmeasured`. ⇒ **three-way cell read** (measured /
   unmeasured / unrecognised). A measured zero is still zero.

⭐ **Use the published value-scope fields** (whether a row is a single close or blends cumulative and
last-close values, and which fields fall in each) rather than hand-deriving which figures a
re-entered row mixes. A re-entered phase row is arithmetically unsafe to quote as a rate; **check it
per contributing phase and exclude or label.**

## Out of scope

- **Re-running or re-instrumenting old plans.** Excluded because only plans composed after the
  instrumentation landed emit all six phases; a re-run of the old corpus cannot produce the missing
  fields, and pretending otherwise would fabricate coverage.
- **The unattributed *cached-read* population.** Excluded — different quantity, different
  denominator, owned by a sibling plan. D2 covers the byte half only.
- **Reviving the per-phase cost *ranking*.** Excluded because it is retired on independent grounds
  (several mechanisms disagree on the direction of its error). This plan reports **shares of
  exploration**, which is a different question, and must not be read as rehabilitating the ranking.
- **Acting on the conclusion.** Excluded because D3 *states* the value case; re-scoping the work
  itself belongs to the epic and to the plans that own each bucket.

## Expected surface

- Archived run metrics records — the read-only corpus. ⛔ **Machine-local; see D0.**
- `.claude/skills/audit-archived-plan-retrospectives/` — its billing-composition check, the natural
  host for a corpus-wide split report. **HYPOTHESIS**, verify at outline.
- The epic's own value-case document, for D3.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The index-answerable share is a small minority and doc-residency the large majority | **OBSERVED on n=1** | ⛔ **n=1 is the whole problem.** D1 is the verification. The originating record is machine-local and **not reachable from this clone** — do not look for it. |
| The refine phase is the doc-residency worst case, and finalize is not | **OBSERVED on n=1, and it REFUTES this plan's original framing** | Recorded so the refuted framing is not carried forward. D1 re-derives it on a population. |
| The execute phase is the best case for a substrate | **OBSERVED on n=1 — the confirmed half of the original prediction** | D1 re-derives. |
| The attributed cached-read figures reconcile to the phase total exactly on one phase, and the other phases carry no such field at all (absent, not zero) | **OBSERVED** | ⚠ **Absent is not zero.** A check that reads an absent field as zero concludes `0 == 0` and reports success — that error was already made once inside the verification of the plan that shipped this instrument. **Distinguish absent from zero before summing.** |
| Only plans composed after the instrumentation landed carry all six phases | **OBSERVED, and it is expected rather than a defect** | The recorder runs late in the run — after the merge and the cache sync — so only the finalize bucket was written by newly-landed code. This is the non-self-exercisability rule landing on the instrument itself. |
| The composition claim (context is ~99% of billing weight) | **OBSERVED, confirmed independently more than once, formula verified against a published total** | ⚠ **Composition only.** The per-phase ranking stays retired; do not read this row as reviving it. |
| Every figure quoted in this plan | **LEAD, not a fact** | Re-derive at the moment of the claim; the population moves as plans land. |

An asserted **absence** ("no population exists yet") is verified exactly as an asserted presence —
and here it is D0's entire job. ⚠ A previous statement that the instrumented population was still at
most one was **stale within days**; do not trust any stated count, including this warning.

## Verification

- **D0's halt is a real outcome.** A run that halts with a clear statement of what was unreachable
  has succeeded at D0. A run that proceeds on one record has failed, whatever else it produces.
- **D1's population reporting is verified by a reader test, not by inspection**: hand the output to
  the pre-PR verification sub-agent and confirm it can state, for any figure, which plans and which
  phase produced it. If it cannot, D4 is not met.
- **The three-state and three-way reads are each verified with a record in every state**, including a
  deliberately old-schema record asserted to be **reported as old-schema** rather than defaulted.
- **D3 carries a cold read.** Its value is entirely what a later reader concludes about where the
  epic is aimed. The sub-agent reads it cold and reports which reading it took.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **This plan exists because the epic's own instrument produced a number that challenges the epic.**
  That is the point of it. The deliverable permitted to conclude the substrate is worth less than
  assumed is D3, and it should be written as willingly as one confirming the opposite.
- **Serialization.** Shares the metrics/retrospective surface class with several sibling plans — do
  not run concurrently with them.
