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

# Scope derived from narrative intent instead of the authoritative write-set

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The outline and planning phases repeatedly consume a field **summarised from intent** — a
deliverable's declared file-type bucket, its change type, its module — or from a point-in-time sweep,
rather than deriving it mechanically from the authoritative affected-files write-set. The result is a
dropped finalize step, a skipped build, an un-assessed late-scoped file, or an inherited foreign
commit.

⛔ **This plan MUST SPLIT, and that is already decided — the gate records the cut, it does not
re-litigate whether to.** The reason is not the instance count: the originating spec carried five
deliverables, fifteen carried lessons and **ten evidence folds**. **Ten folds against five deliverables
is the tell** — the folds had been doing the work of deliverables without ever being counted against
the split guard.

**The cut, along the axis the failures actually differ on:**

| Arm | What fails | Failure signature |
|---|---|---|
| **A — the derived SET is incomplete** (the sweep did not see everything) | coverage of a derived set | **silent omission** |
| **B — the derived BUCKET or classification is wrong** | classification of an already-derived set | **wrong routing** — a dropped profile, a skipped build, a mis-bucketed footprint |

⭐ The axis is real rather than convenient: the two arms have **different tests and different failure
signatures**. ⚠ **Whichever arm takes the request-classification material must say so explicitly** —
it was already flagged as split-liable and **must not fall between the two arms.**

## ⭐ The sub-classes that make this more than "be more careful"

**An asserted closure that also SUPPRESSES the check that would have caught it.** One outline declared
a "closed consumer set" that was not closed, **and on the strength of that closure claim told the next
phase not to re-check**. A merely-incomplete sweep is recoverable downstream; an incomplete sweep
carrying the authority to disable re-verification is not. ⇒ **The fix is not only *derive the set* but
*deny the claim the power to skip re-checking* — a closure assertion should be a hint, never a
licence.**

**A declared-but-unrun sweep freezes the write-set.** A deliverable declared a survey scope wider than
the files it then listed. **Nobody ran the declared sweep**, and a real hit outside the listed set was
found later — a path that appeared in no write-set, so the downstream recall check could never see it.
⛔ **Never leave the pair `{declared scope wide, write-set narrow}` unreconciled — that pair is the
signature, and it is machine-comparable** (a declared glob against an enumerated file list).

**Two independent vacuity axes, not one.** This **extends** the standing "every set-guarding detector
must be population-derived" rule rather than restating it:

| Axis | Question | Guard |
|---|---|---|
| **Predicate** | Does the detector flag the bad content? | a negative fixture carrying the pre-fix text verbatim |
| **Population** | Does the scanned set contain the at-risk documents? | a **positive-population** assertion: the slice is non-empty **and** contains the known hit |

⛔ **Population-derived is not enough if the source set you derive from is the wrong, narrower one.**
The population axis is the one routinely missed, because a passing fixture test *feels* like
sufficient proof of non-vacuity. ⭐ **A glob that matches nothing looks identical to a glob that
matches everything.**

**Verification checks a spec's CITATIONS but not its ASSERTIONS.** A premise can survive verification
with every citation valid while its **behaviour claim is false** — verification aimed at the wrong
object. ⚠ **An assertion that survives because its citations are valid is *worse* than an unverified
one, because it now carries a verification stamp.**

**A reported defect LOCATION is a sample, not the defect.** Whoever reports a defect reports **where
they observed it** — a symptom site. The defect lives where the bad value is *produced*, and the
impact set is **every consumer of that value**. In one case the named function did not exhibit the
behaviour at all; the real site was its caller, and the blast radius was several times the reported
one.

**Under-enumeration in a characterization corpus is an ACTIVE ENDORSEMENT of the bug.** A
characterization test's job is to pin *current* behaviour — so an under-enumerated corpus **faithfully
pins the defect as expected behaviour**, converting a latent bug into a green test that certifies it.
⇒ Unlike a missed call site, this fails **silently and permanently**.

⛔ **And prose warnings are NOT a control.** One plan identified this exact enumeration risk in its own
overview **and then committed it three times in the same run.** A plan that identifies an enumeration
risk must discharge it with a **concrete enumeration step in a deliverable.**

## Goal

Consumed scope fields are **derived, not asserted**; completeness checks are **closure-based, not
existence-based**; and a claim of closure cannot license skipping the verification that would test it.

## Deliverables

1. **D0 — GATE: confirm each defect at HEAD, then RECORD THE SPLIT. Mutates nothing.**
   Group the confirmed defects into arm A (incomplete derived set) and arm B (wrong classification),
   and **state which arm takes the request-classification material.**
   ⛔ **The split is decided; D0 records the cut and drops whatever is already closed.**
   ⚠ **Expect closed items**: a prior reconciliation found this spec carrying a deliverable for work
   that had already shipped — **the exact inverse of the defect this plan exists to fix.**
   *Done when:* each defect carries a confirmed/refuted verdict and the two arms are enumerated.
2. **D1 — derive the bucket, module and change type from the write-set**, never from narrative intent.
   A read-only reference file must not flip a bucket; a change type must be composed across
   deliverables rather than taken from the first; a drift check must read the analysis prose, not only
   the title and metadata.
   *Done when:* each derived field is computed from the write-set, asserted by a fixture where intent
   and write-set disagree.
3. **D2 — outline completeness is CLOSURE, not existence.**
   Compute referrer, projection and claim-versus-index closure rather than only asserting that
   declared paths exist. **Run the declared sweep before freezing the write-set**, enumerate the result
   **including hits outside the request's constraints**, and treat an out-of-constraint hit as a
   **scope contradiction to resolve explicitly** — widen with a recorded authorisation, or narrow the
   declared scope and record the un-swept surface as a deliberate documented exclusion.
   ⛔ **Assert `detector_population ⊇ fix_set_population` explicitly**, as a normative line rather than
   an implicit consequence of a chosen root constant.
   *Done when:* a declared-wide / listed-narrow pair is detected mechanically, and the population
   assertion exists with a positive-population guard.
4. **D3 — a closure claim is a hint, never a licence.** A declared closed set must not carry the
   authority to suppress downstream re-checking.
   *Done when:* a downstream re-check runs regardless of an upstream closure assertion.
5. **D4 — pre-flight integrity for the derivation order.**
   A phase-3 consumer whose precondition is a phase-5 artifact is a **derivation-order defect**, not a
   missing directory — resolve against the main checkout rather than a not-yet-materialised worktree.
   ⭐ **Adopt the generalisable rule**: *when a producer publishes an explicit discriminator for a
   multi-state contract, consumers MUST branch on THAT discriminator, not re-derive the state from
   primitive fields.* **Re-derivation is where "success" silently collapses into "error".**
   ⭐ And: *any precondition that is a pure function of the footprint should be evaluated as soon as
   the footprint is known.* ⛔ **A fix that only special-cases one known path has learned the example,
   not the lesson.**
   *Done when:* the consumer branches on the discriminator, and a footprint-derived precondition is
   evaluated at planning time rather than at finalize.
6. **D5 — tests**, each verified to fail pre-fix, plus a **characterization-corpus rule**: a fixture
   corpus is **population-derived from the live corpus directory** — enumerate every fixture, then
   justify each **exclusion** explicitly. ⛔ **Opt-out with a stated reason, never opt-in by
   selection**; an unstated exclusion is indistinguishable from an endorsement of the behaviour on the
   excluded case.

Six deliverables with D0 a gate — **and the split above is mandatory**, so the shipped plan is one arm
of it. ⚠ If a deliverable grows a further arm, **split it out rather than absorbing it silently.**

## Out of scope

- **The task-artifact emission defect.** ⛔ **Struck — a sibling plan owns it** as a full deliverable
  plus a test. Two plans in two workstreams were carrying one defect. ⚠ The framing worth carrying
  across: a non-zero count check **cannot see the collapse**, so the under-emission is invisible to the
  check that would report it.
- **The plan-efficiency calibration table.** ⛔ **Struck — already closed**, verified first-party: the
  table is the exact cross-product of both live axes and a test re-derives both and asserts set
  equality in both directions. ⛔ **Do not scope it.** Its *other* half — a per-task figure computed
  from wall-clock, grading operator idle time as agent cost — belongs to a different plan. ⚠ **The
  originating lesson is therefore NOT retirable by this plan alone.**
- **Moving the worktree creation point.** Excluded — it would collide with other work; prefer reading
  the main checkout unless the outline genuinely needs worktree state.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-3-outline/` — the discovery sweep and closure pass.
  **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/phase-4-plan/` — bucket, change-type and write-set
  derivation. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/` — the module-context
  worktree-state branch. **HYPOTHESIS**, verify at outline.
- The shared project-directory resolution helper — the discriminator defect. **HYPOTHESIS.**
- `marketplace/bundles/plan-marshall/skills/manage-tasks/` — deliverable segmentation. **HYPOTHESIS.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Consumed scope fields are summarised from intent rather than derived from the write-set | **OBSERVED, many instances** | ⛔ **Confirm each at its own site in the clone.** The archetype is established at high recurrence — **spend the budget on the fix shape, not on re-proving prevalence.** |
| A closure claim can suppress downstream re-checking | **OBSERVED, first-party** | The outline-to-execute handoff. Read it. |
| The shared resolver reads primitive fields and never the published state discriminator | **OBSERVED** | The resolver in the clone — this one is cheap and decisive. |
| A named defect site did not exhibit the behaviour, and the real producer had several consumers | **OBSERVED, corroborated against a merged diff** | ⚠ **The consumer COUNT is the sending plan's** — ⛔ **corroborate it yourself before making it the deliverable's scope.** |
| A staged premise EXPIRES; re-measure at outline rather than inheriting it | **OBSERVED** | ⛔ **Sharpest member for this epic specifically**, because these specs are long-lived and heavily folded. |
| An outline mandated an edit to a symbol a prior plan had already REMOVED | **OBSERVED** | The natural test for the item above. |
| The routing decision's pre-override input is overwritten by its output | **OBSERVED** | ⭐ **The evidence needed to audit the router is destroyed by the router** — and the routing checker audits *which steps were pruned*, never *whether the lane was right*. |
| Every remaining derivation gap is still open | **HYPOTHESIS** | **D0.** Expect at least one to be closed. |
| Any count quoted in this plan | **LEAD, not a fact** | ⛔ **Never carry a count forward from a spec, an outline, or a reviewer's list.** Re-derive from the live tree at the moment of consumption. |

## Verification

- **The population axis is verified explicitly, not implied by a passing fixture.** Assert the scanned
  slice is non-empty **and** contains a known hit. ⛔ Without it, widening a glob is unverified.
- **Each fixture carries the pre-fix text verbatim** for the predicate axis.
- **The characterization corpus is verified by its exclusions**, each stated with a reason. An
  unstated exclusion fails D5 regardless of what the included cases prove.
- **D3 is verified adversarially**: assert an upstream closure claim and confirm the downstream check
  still runs.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- ⭐ **The recurrence signature worth being able to detect**: *a rationale paragraph that correctly
  rejects an allowlist on one axis, immediately followed by a rule that is an allowlist on a different
  axis* — and *a guard test whose collection step carries a filter the rule it guards does not*. Both
  are derivable from the outline text plus the rule, which is this plan's own surface.
- **Related generalisation, recorded rather than folded**: the same thesis extends from **enumeration**
  to **invariants** — *a stated invariant is not a checked invariant.*
