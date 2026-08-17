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

# The derived set is incomplete, and the claim of completeness suppresses the re-check

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Provenance

This is **arm A** of the split mandated by
[`280-outline-plan-scope-derivation-integrity`](280-outline-plan-scope-derivation-integrity/plan.md).
That plan recorded the cut and shipped **arm B** — *the derived BUCKET or classification is wrong*,
whose failure signature is **wrong routing**. This plan carries the other arm.

The axis is not a convenience. The two arms have different tests and different failure signatures:

| Arm | What fails | Failure signature |
|---|---|---|
| A — **this plan**: the derived SET is incomplete | coverage of a derived set | **silent omission** |
| B — shipped in 280 | classification of an already-derived set | wrong routing |

⚠ The **request-classification material** went to arm B, explicitly, and is out of scope here.

## Problem

An outline or plan asserts that a derived set is complete, and nothing computes the closure that
would test the assertion. Existence is checked where closure is meant: *the declared paths resolve*
is confirmed, *the set contains everything it must* is not. The result is a surface nobody swept, and
no downstream check can see the gap because the gap is precisely what never entered the write-set.

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

**Under-enumeration in a characterization corpus is an ACTIVE ENDORSEMENT of the bug.** A
characterization test's job is to pin *current* behaviour — so an under-enumerated corpus **faithfully
pins the defect as expected behaviour**, converting a latent bug into a green test that certifies it.
⇒ Unlike a missed call site, this fails **silently and permanently**.

⛔ **And prose warnings are NOT a control.** One plan identified this exact enumeration risk in its own
overview **and then committed it three times in the same run.** A plan that identifies an enumeration
risk must discharge it with a **concrete enumeration step in a deliverable.**

## Goal

Completeness checks are **closure-based, not existence-based**; a declared sweep is run before the
write-set is frozen; and a claim of closure cannot license skipping the verification that would test
it.

## Deliverables

1. **D0 — GATE: confirm each defect at HEAD. Mutates nothing.**
   ⚠ **Expect closed items** — 280's own gate found one of its six sub-claims already shipped.
   *Done when:* each defect below carries a confirmed/refuted verdict with a file-and-symbol citation.
2. **D1 — outline completeness is CLOSURE, not existence.**
   Compute referrer, projection and claim-versus-index closure rather than only asserting that
   declared paths exist.
   *Done when:* a closure computation exists and a fixture in which every declared path resolves yet
   the set is incomplete is detected.
3. **D2 — run the declared sweep before freezing the write-set.**
   Enumerate the result **including hits outside the request's constraints**, and treat an
   out-of-constraint hit as a **scope contradiction to resolve explicitly** — widen with a recorded
   authorisation, or narrow the declared scope and record the un-swept surface as a deliberate
   documented exclusion.
   *Done when:* the `{declared scope wide, write-set narrow}` pair is detected mechanically, by
   comparing a declared glob against the enumerated file list.
4. **D3 — assert `detector_population ⊇ fix_set_population` explicitly**, as a normative line rather
   than an implicit consequence of a chosen root constant.
   *Done when:* the population assertion exists and carries a positive-population guard — the slice
   is non-empty **and** contains a known hit.
5. **D4 — a closure claim is a hint, never a licence.** A declared closed set must not carry the
   authority to suppress downstream re-checking.
   *Done when:* a downstream re-check runs regardless of an upstream closure assertion, verified
   adversarially — assert the closure claim and confirm the check still runs.
6. **D5 — tests**, each verified to fail pre-fix, plus a **characterization-corpus rule**: a fixture
   corpus is **population-derived from the live corpus directory** — enumerate every fixture, then
   justify each **exclusion** explicitly. ⛔ **Opt-out with a stated reason, never opt-in by
   selection**; an unstated exclusion is indistinguishable from an endorsement of the behaviour on the
   excluded case.

⚠ If a deliverable grows a further arm, **split it out rather than absorbing it silently.**

## Out of scope

- **Everything arm B shipped** — the worktree-state discriminator, the write-set-derived bucket, the
  keyword-drift haystack. ⛔ Do not re-scope; read 280's run report first.
- **The task-artifact emission defect.** ⛔ **Struck — a sibling plan owns it.** ⚠ The framing worth
  carrying across: a non-zero count check **cannot see the collapse**, so the under-emission is
  invisible to the check that would report it.
- **The plan-efficiency calibration table.** ⛔ **Struck — already closed**, verified first-party.
  ⚠ **The originating lesson is therefore NOT retirable by this plan alone.**
- **Moving the worktree creation point.** Excluded — it would collide with other work.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-3-outline/` — the discovery sweep and closure pass.
  **OBSERVED** (280's gate confirmed the bucket classifier is an authoring instruction with no
  mechanical closure pass).
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/consumer-sweep.md` — the
  declared-sweep surface. **HYPOTHESIS**, verify at outline.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-artifact-consistency.py`
  — the recall check that cannot see a path absent from every write-set. **HYPOTHESIS.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Completeness is checked by existence rather than closure | **OBSERVED** | The outline validator: it asserts declared paths resolve and never that the set is closed. |
| A closure claim can suppress downstream re-checking | **OBSERVED, first-party** | The outline-to-execute handoff. Read it. |
| A declared sweep wider than the listed write-set goes unreconciled | **OBSERVED** | The survey-scope deliverable class in `outline-workflow-detail.md`. |
| The routing decision's pre-override input is overwritten by its output | **OBSERVED, not yet sited** | ⭐ **The evidence needed to audit the router is destroyed by the router** — and the routing checker audits *which steps were pruned*, never *whether the lane was right*. 280 did not site this; confirm it at D0. |
| A staged premise EXPIRES; re-measure at outline rather than inheriting it | **OBSERVED** | ⛔ **Sharpest member for this epic specifically**, because these specs are long-lived and heavily folded. |
| Every remaining gap is still open | **HYPOTHESIS** | **D0.** Expect at least one to be closed. |
| Any count quoted in this plan | **LEAD, not a fact** | ⛔ **Never carry a count forward from a spec, an outline, or a reviewer's list.** Re-derive from the live tree at the moment of consumption. |

## Verification

- **The population axis is verified explicitly, not implied by a passing fixture.** Assert the scanned
  slice is non-empty **and** contains a known hit. ⛔ Without it, widening a glob is unverified.
- **Each fixture carries the pre-fix text verbatim** for the predicate axis.
- **The characterization corpus is verified by its exclusions**, each stated with a reason. An
  unstated exclusion fails D5 regardless of what the included cases prove.
- **D4 is verified adversarially**: assert an upstream closure claim and confirm the downstream check
  still runs.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- ⭐ **The recurrence signature worth being able to detect**: *a rationale paragraph that correctly
  rejects an allowlist on one axis, immediately followed by a rule that is an allowlist on a different
  axis* — and *a guard test whose collection step carries a filter the rule it guards does not*.
- **Related generalisation, recorded rather than folded**: the same thesis extends from **enumeration**
  to **invariants** — *a stated invariant is not a checked invariant.*
- **Carried from 280's residue**: a `disabled` plan's footprint is derivable from the main checkout,
  yet every footprint gate in the tree reports it permanently unresolvable. 280 confirmed this and
  deliberately did **not** fix it — the change is cross-cutting (it touches `manage-references`, the
  composer, and `extension_base` together) and a naive fix makes footprint derivation depend on
  whatever else is uncommitted in the checkout. It is an incomplete-derived-set defect, so it belongs
  to this arm; see 280's run report for the analysis before scoping it.
