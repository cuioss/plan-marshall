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

# The dispatch-boundary ledger is not a commensurable population

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The dispatch-boundary ledger is the **only per-dispatch view of context spend** — it is what the
attribution instrumentation reports against, and what every share-of-dispatch-spend figure is divided
by. It currently publishes a coverage ratio whose numerator and denominator come from **different
populations**, omits **whole dispatch classes** without saying so, and **mislabels exact agreement as
a discrepancy**.

⭐ **The three defects are one defect seen from three angles**, and that framing is the reason they
are one plan. Each was filed separately; each turns out to be a symptom of *the ledger having no
declared population*:

| Angle | Symptom | What it says about the population |
|---|---|---|
| **The ratio** | a rendered coverage line whose **numerator exceeds its denominator**, annotated `complete` | numerator and denominator are drawn from different sets, and nothing asserts commensurability |
| **The omission** | some phases' dispatches record **no** boundary at all | the denominator's set structurally excludes some dispatches |
| **The comparator** | equal totals annotated *"smaller than total_tokens"* | the comparison asserts a strict inequality that does not hold |

⇒ ⛔ **The omission is very likely the mechanism behind the ratio.** If whole classes never register,
a numerator counted one way and a denominator counted another **cannot** agree, and the impossible
ratio becomes an *expected outcome* rather than an anomaly. **D2 must test D3 as its first candidate
explanation before treating the ratio as an independent defect** — fixing the ratio while the class
omission stands would produce a clean figure over an incomplete set, which is strictly worse than a
visibly impossible one.

## Goal

The ledger is a **declared population** whose figures are commensurable — or it states plainly what
it excludes. A coverage ratio either compares two counts drawn from one declared set or it does not
render; a dispatch class that registers nothing is named; and an exact agreement between two
independent producers reads as agreement.

## Deliverables

1. **D1 — GATE: declare the population. Mutates nothing.**
   Answer, before changing anything: **which set of dispatches is the ledger's denominator meant to
   be?** Enumerate the dispatch classes that exist, then determine for each whether it registers a
   boundary.
   ⛔ **Derive the class list from the dispatching code, never from a list of classes observed in a
   run** — a run-derived list cannot contain a class that never registers, which is precisely the
   defect.
   *Done when:* the class count and the registering count are reported as **two separate figures**,
   both derived from source.
2. **D2 — a recorded-vs-expected ratio is commensurable, or it does not render.**
   Numerator and denominator must come from **one declared population**, and a ratio whose numerator
   exceeds its denominator must be a **loud failure**, never `complete`.
   ⛔ **Do not fix by clamping the display** — a clamped ratio is the same defect with the evidence
   removed.
   *Done when:* an impossible ratio produces a failure verdict, and the populations behind both
   figures are named in the output.
3. **D3 — every dispatch records a boundary, or the ledger names the classes it excludes.**
   ⛔ **Silent exclusion is the defect** — a ledger that omits a class without saying so is
   indistinguishable from a class that did not run.
   *Done when:* either every enumerated class registers, or the non-registering classes appear in an
   explicit exclusion list that the coverage figure references.
4. **D4 — the comparator stops mislabelling exact agreement.**
   ⛔ **Equal is not smaller.** The max-selection is arithmetically fine; the *message* asserts a
   strict inequality that does not hold, so a reader is told the ledger under-counted when it agreed
   exactly.
   ⭐ **State why this is more than a wording fix**: an exact agreement between two independent
   producers is **the single most valuable signal this surface can emit** — it is the reconciliation
   identity the attribution work proved by arithmetic — **and it is currently rendered as a
   discrepancy.** A reader trained by this message learns to distrust the one case that should build
   trust.
   *Done when:* equal figures are annotated as agreement, and a test pins the three-way distinction
   (smaller / equal / larger).
5. **D5 — tests, each verified to FAIL pre-fix.**
   (a) a ratio whose numerator exceeds its denominator renders as a failure, never `complete`;
   (b) a class that registers no boundary is named in the exclusion list;
   (c) equal boundary and total figures are annotated as agreement.
   ⚠ Each test is verified to fail against current code **before** the fix. A test that passes today
   is a characterization test and **must be labelled as one** — mixing the two is how a suite comes
   to certify the defect it was written to catch.

Five deliverables with D1 a gate — under the split guard.

## Out of scope

- **The retrospective's render path.** Excluded because another staged plan owns it; this plan reads
  the boundary figures' consumption but does not restyle the report.
- **The step/dispatch *emission* arm** — whether each step emits its instrumentation at all.
  Excluded because it is a sibling plan's subject; this plan was split out of that one precisely to
  keep the ledger *arithmetic* separable from the *emission* question.
- **Clamping or otherwise smoothing any displayed figure.** Excluded because the visible impossibility
  is evidence: removing it hides the population defect without fixing it.
- **Re-deriving per-phase cost rankings from the corrected ledger.** Excluded because that ranking is
  retired on independent grounds; this plan makes a denominator trustworthy, it does not revive a
  ranking.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-metrics/` — the dispatch-boundary record writer
  and the recorded-vs-expected renderer. **HYPOTHESIS**: the render site was not located first-party;
  verify at outline.
- The dispatch sites that fail to register — the refine phase and the quality-gate validation spawn
  path. **HYPOTHESIS**, verify at outline.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/` — consumption of the boundary
  figures, **read-only here**.
- `test/plan-marshall/manage-metrics/` — the D5 tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| A coverage line rendered a numerator larger than its denominator and certified it `complete` | **OBSERVED, but the artifact is NOT reachable from this clone** | It was seen in a machine-local run record under the git-ignored `.plan/` tree. ⛔ **Do not go looking for it.** Confirm the *capability* instead, in the clone: read the renderer and establish whether the two counts can come from different sets. **If they can, the defect is confirmed without the artifact.** |
| Some phases' dispatches record no boundary at all | **OBSERVED on an independent plan neither epic ran** | Same reachability caveat. ⛔ **Confirm in the clone by reading the dispatch sites**, not by hunting run records. |
| Equal totals were annotated as "smaller than" | **OBSERVED, same caveat** | The comparator's message construction is in the clone — read it; the string settles the claim. |
| The class omission is the mechanism behind the impossible ratio | **HYPOTHESIS** | Confirm or refute by determining whether the two populations differ **by exactly the non-registering classes**. ⛔ **This is a real fork**: if they differ by something else, the ratio has a second cause and fixing the omission will not close it. |
| The two named phases are the complete set of non-registering classes | **HYPOTHESIS** | ⛔ **Almost certainly a FLOOR, not the set** — it is a two-run sample, and the standing rule here is that a named list is a sample. **D1 derives the real set from source.** |
| A resumed run may contribute to numerator and denominator inconsistently | **HYPOTHESIS** | A sibling plan owns the resume-instrumentation question, but it hands this one a candidate explanation. **D2 must consider it alongside the omission.** |

An asserted **absence** ("these classes register nothing") is verified exactly as an asserted
presence, and is the higher-risk half: an unverified absence sends this plan to add registration to
a site that already has it.

## Verification

- **D1 is verified by derivation, not by observation.** The run report must state that the class list
  came from the dispatching code. A list assembled from what a run happened to emit fails this
  deliverable by construction — it cannot contain the classes the defect hides.
- **D5's fail-first requirement is itself verified**: each test is run against unmodified code and
  shown to fail before the fix lands. Record the pre-fix failure in the run report; a test whose
  pre-fix behaviour was never observed is a characterization test wearing a regression test's label.
- **D3's exclusion list is verified by a negative control**: remove a class's registration and
  confirm it appears in the list rather than silently shrinking the denominator.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why the split happened.** This plan was carved out of a sibling that had accreted to eleven
  deliverables — the worst split-guard breach in its queue. The three items here were moved together
  because they **compound with one another**: each was filed as a candidate explanation for the
  others. Keeping them together is what makes them tractable.
- **Consequence of the split, worth knowing.** The share-of-dispatch-spend plan is blocked on **this**
  plan, not on the larger sibling it came from — its figures need a denominator that is not visibly
  impossible. The sibling's emission arm may now land in any order relative to it.
- **Serialization.** Never run concurrently with the sibling emission plan or the finalize-ordering
  plan: the split was a scoping fix, **not** a disjointness claim, and they still share the finalize
  dispatch neighbourhood.
