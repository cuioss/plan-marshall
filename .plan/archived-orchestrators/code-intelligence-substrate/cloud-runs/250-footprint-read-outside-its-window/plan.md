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

# A footprint read outside the window in which the footprint exists reports zero as a finding

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

Several independent sites derive a plan's file footprint at a moment when the footprint's **source
does not exist**, and render the resulting emptiness as a **measured zero** — one as a failing
coverage metric, one as a build-skip decision, one as a step-pruning predicate.

**The mechanism is one line, repeated.** The predicate is *"if not footprint"* in every case, so
*"I could not measure this"* and *"I measured this and it is empty"* **collapse into one branch — and
the branch that wins is the confident one.** There is no third state to lose, because none was ever
built.

**The reader-side instance.** A coverage check derives the footprint live from the plan's worktree,
but the step that **removes the worktree** is ordered **before** the retrospective that reads it. So
the worktree is always gone by the time the check runs. A plan between worktree removal and archival
is in **neither** documented footprint state — the worktree is gone **and** the plan is still live —
so both documented sources miss and the resolver silently resolves to the empty set. Multiple runs
have reported total coverage failure where the true recall, reconstructed by hand from the merge
commit, was **perfect**.

**The composer-side instance, and it is worse.** A build-or-skip decision is evaluated at plan time,
**before any file has been written**, on the stated grounds that nothing changed. It has been observed
surviving only because an unrelated always-on setting re-added the step four log lines later. ⛔ **A
reader that grades an absent input emits a wrong number; a composer that prunes on an absent input
removes a gate from the run.** Two consecutive runs have had their security/quality lane pruned this
way while touching production code.

## ⛔⛔ The partial-fix trap — read this before scoping any ordering fix

**The coverage failure has TWO independent causes, either of which alone produces it.**

1. **Ordering** — the measurement runs after the worktree it derives from is deleted.
2. **Vacuity — independently fatal.** The recall **denominator counts read-intent files as expected
   modifications.** A plan that declares files it intends to *read* is penalised for not *modifying*
   them, which can cap achievable recall **below the pass threshold by construction** — no execution
   of such a plan could pass.

⛔⛔ **Fix the ordering alone and the check goes from failing for a demonstrably wrong reason to
failing for a differently wrong reason — while looking like it was addressed.** Worse, a green
ordering fix would **destroy the evidence that the second cause exists.**
⇒ **This plan MUST address both, or explicitly split them into two sequenced plans and say so.
Shipping the ordering half alone is a defect of this plan.**

## Goal

A footprint read distinguishes *"the footprint is empty"* from *"the footprint source is
unavailable"*, and never renders the second as the first — with the **reader** side failing open to
an explicit unknown and the **composer** side failing **closed**.

## Deliverables

1. **D1 — GATE: derive the population of footprint reads. Mutates nothing.**
   Enumerate every site that derives a footprint and grades or decides on it.
   ⛔ **Population-derived, not the sites this plan names** — two named sites became at least four by
   observation alone, which is the standing *a reported instance is a sample* rule firing against this
   very plan. Establish for each site whether its source can be absent at its call time.
   *Done when:* the population is derived from source and published with its count.
2. **D2 — a third state at the read seam.** When the derivation source is absent, the output is
   `unknown` / `skipped` **with a reason token** — never zero, never a graded failure.
   **Adopt this as the success criterion verbatim:**
   > **An unmeasurable quantity must not be reported as a measured zero.** A zero that means *"could
   > not measure"* and a zero that means *"measured nothing"* must not share a representation.
   *Done when:* an absent source yields the named state, and a genuinely empty footprint still yields
   zero — **both asserted.**
3. **D3 — fix the recall denominator.** Read-intent declarations must not count as expected
   modifications.
   ⚠ **Check whether any other derived metric shares that denominator** — the intent-classified path
   list is likely consumed by more than one check. **Derive the consumer set rather than assuming it
   is one.**
   *Done when:* a plan declaring read-intent files can reach a passing recall, asserted by fixture.
4. **D4 — the composer's decision stops being a constant, and fails CLOSED.**
   A decision taken against a footprint that cannot exist yet is not a decision. Either defer it to a
   point where the footprint is real, or state the predicate's precondition and **skip** when it is
   unmet.
   ⛔ **An unresolvable footprint must make every footprint-dependent prune predicate INADMISSIBLE,
   not false.** ⭐ **Fail-closed is the only safe direction here** — keeping the step is recoverable,
   dropping it is not — **which is the inverse of the reader-side remedy where an inconclusive result
   is correct. State that asymmetry explicitly; it is why the two cannot share one fix.**
   ⚠ If the intent was to skip a gate for a no-op plan, derive it from the **declared** deliverable
   footprint, which **is** available at composition time.
   *Done when:* no composition-time predicate reads the realized footprint, pinned by a test.
5. **D5 — assess the blast radius on the archived corpus.** Determine whether archived plans' coverage
   figures are affected the same way and report the count.
   ⛔ **Report the affected count SEPARATELY from the number of plans examined** — a volume is not a
   coverage number, and volume-read-as-coverage is a recorded recurring archetype here.
   ⚠ **Corpus reachability**: the archived records live under a **machine-local, git-ignored** path
   **not present in this clone** ⛔ **— do not search for it.** If unreachable, **report D5 blocked on
   corpus availability** rather than estimating. No corpus rewrite is in scope either way; the
   deliverable is the honest assessment.
6. **D6 — tests, each verified to FAIL pre-fix.**
   (a) a coverage run with the source absent yields the unknown state, not a graded zero;
   (b) a composition run before any file is written emits no footprint-empty omission;
   (c) a read-intent declaration does not depress recall.

Six deliverables — **at the split guard.** Proceeding unsplit is deliberate: D1 is a gate that D2–D4
all consume, and D5/D6 are small. ⚠ **If D1 finds the population is materially larger than the named
sites, SPLIT and re-stage rather than growing this plan.**

## Out of scope

- **Capturing or persisting the footprint.** ⛔ **Struck — a sibling plan owns the producer side.**
  Shipping both would produce **two writers for one key**. **The split is producer versus consumer and
  it is settled twice — do not re-litigate it.** This plan owns **how a reader behaves when the
  producer gave it nothing**.
- **Rewriting the archived corpus.** Excluded — D5 assesses, it does not repair.
- **A posture-driven step drop.** ⛔ Excluded and **not to be confused with D4**: dropping certain
  steps under a lighter execution posture is a standing **operator decision**. D4 is about a
  **predicate** evaluated against an **unresolvable** footprint. Different mechanism, and only one of
  them is the operator's call.
- **A checker that mis-attributes a posture drop to a prune predicate.** Excluded — a sibling plan
  owns that. One is a **mis-report**, this is a **mis-action**.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/` — the coverage check. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/` — the composer. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/manage-config/` — **a consumer discovered by observation
  rather than by design.** ⛔ **D1's population derivation must reach it.** **OBSERVED.**
- A shared footprint-derivation helper, if one exists. **HYPOTHESIS**, verify at outline.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The predicate collapses "could not measure" into "measured empty", in every consumer | **OBSERVED** | ⛔ **Read the predicate in each consumer in the clone.** This is the mechanism, it is one line, and it settles the whole plan without any run record. |
| The worktree-removing step is ordered before the retrospective that reads the worktree | **OBSERVED** | The step ordering in the clone. ⚠ **Confirm whether that order is the DEFAULT or per-plan** — it is load-bearing: if per-plan, the "fires on every plan" claim narrows and D5 shrinks. |
| A plan between worktree removal and archival is in neither documented footprint state | **OBSERVED** | The resolver's documented tiers — read them; the gap is visible in the contract itself. |
| The legacy fallback is **gone**, retained only for archived plans | **OBSERVED** | ⛔ **Do not scope a fix that assumes the fallback can be re-pointed** — a live post-cleanup plan has no fallback at all. |
| The recall denominator counts read-intent files as expected modifications | **OBSERVED, first-party** | The denominator's construction in the clone. ⛔ **This is the second, independently fatal cause — verify it before fixing the ordering.** |
| The composer pruned a quality lane on an unresolvable footprint, twice, on runs touching production code | **OBSERVED, two consecutive sightings** | The run records are machine-local ⛔ **and not reachable here — do not look for them.** ⭐ **Confirm the capability in the clone instead**: if the prune predicate can evaluate against an unresolved footprint, the defect is structural. |
| Reconstructed true coverage was perfect in several reported failures | **OBSERVED, verified against merge commits** | ⭐ The reconstruction method is reproducible **in this clone**: derive the merge base and diff the range. Use it to build D6's fixture rather than trusting a stated figure. |
| Archived plans carry the same false column | **HYPOTHESIS** | **D5**, subject to corpus reachability. |
| Every count or ratio quoted in this plan | **LEAD, not a fact** | Re-derive at the moment of the claim. |

## Verification

- **D2 is verified in BOTH directions**: absent source yields the named unknown state; a genuinely
  empty footprint still yields zero. A one-directional test cannot tell the fix from the defect.
- **D4's fail-closed direction is verified adversarially**: make the footprint unresolvable and assert
  the gate is **kept**, not dropped. ⛔ The dangerous direction is the one to test.
- **D3 is verified by a fixture that could not previously pass** — a plan whose declarations are
  mostly read-intent must be able to reach the threshold.
- **D5 reports affected-count and examined-count as two separate numbers.** One number is not a
  coverage claim.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- ⭐ **The self-referential sting, worth keeping.** The tool whose job is to detect false signals
  emitted one **about itself, in its own report** — and because the failure is **ordering-driven
  rather than data-driven, it fires identically on every plan**.
- ⚠ **Polarity note.** This is a confident **RED manufactured by ordering**, where this programme's
  usual case is a confident green hiding a caveat. Same defect class, opposite sign — **which is why
  it survived so long: a red gets explained away as "the plan's fault", a green does not get
  questioned at all.**
- **Serialization.** Shares the retrospective and manifest surfaces with several siblings — sequence,
  never run concurrently.
