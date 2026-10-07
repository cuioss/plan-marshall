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

# The dispatch audit cannot fail, and a sparse channel makes its verdicts meaningless

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

A finalize step can reach a terminal outcome with **no record that it dispatched**, and the audit
built to detect exactly that **cannot fire**.

**The detector is vacuous, and provably so.** The shape-violation check pairs two evidence surfaces:
dispatch lines in the work log against effort-resolution entries in the decision log. **Nothing writes
the second surface at all** — the check's specification and the dispatcher's instrumentation were
never reconciled, so the pairing has no left-hand side and the check is **structurally incapable of
producing a finding**. Its `0` means *never evaluated*, not *evaluated clean*.

⭐ **And a reader cannot tell which zero it is.** A sibling direction of the same audit is *genuinely*
clean over a populated set and renders as the identical `0`. ⇒ **Every check that can return zero from
an empty population MUST publish the evaluated-population size next to the count.** That is what makes
the next vacuous guard self-announcing, and it generalises far past this audit.

⚠ **This is the vacuous-guard archetype at n≥5 in this project, and at least one prior instance was
introduced BY A FIX for it.** The standing counter-measure applies: every set-guarding detector must
be **population-derived, not literal**.

**The detector also mis-attributes in both directions, in a single run.** A step that *was* dispatched
but emitted no line is reported as *"ran inline where dispatch was required"* — **a fabricated
discipline violation against the step, when the real fault is an instrumentation gap in the
dispatcher**. And a step that is rostered as dispatching but legitimately runs inline under a
conditional tier is reported as a coverage violation on essentially every plan of a common change
type. ⚠ **A recurring false positive in a hard-rule check is worse than a missing check: it trains
readers to discount the category.**

**Separately, per-task artifact emission fires for a minority of completed tasks.** Any consumer
counting artifacts under-reports **by construction**, and reads the result as *"few artifacts
produced"* rather than *"emission is broken"*. ⛔ **A count-based detector cannot guard a per-item
emission defect** — the existing non-zero check is satisfied by the very partiality it should report.

## Goal

The audit can fail; it reports the size of the population it evaluated so a zero is legible; it
distinguishes an instrumentation gap from a discipline violation; and it publishes its own channel
completeness so a sparse evidence channel **downgrades the audit's confidence** rather than silently
weakening its verdicts.

## Deliverables

1. **D1 — make the audit able to fail.** Establish why the shape-violation check's second surface
   never fires, and settle **the prior question**: is the resolver expected to log and does not, or
   is the audit built on an evidence surface **no producer writes**? Until that is settled the check
   must report `not_evaluated` with its empty-population reason rather than `0`.
   ⚠ **Verify the corrected detector FAILS against a known-divergent site before trusting any clean
   run** — a detector that has never failed is not evidence.
   ⛔ **Publish the evaluated-population size beside every count**, and make the detector
   population-derived rather than literal.
   *Done when:* the check either produces a finding against a deliberately divergent site, or reports
   `not_evaluated` with its reason — and never a bare `0`.
2. **D2 — the CONSUMER distinguishes three states: dispatched / ran-inline / no evidence.**
   ⛔ **This is a detector change, not an emission change** — see Out of scope.
   Concretely: a step with envelope evidence but no dispatch line is reported as
   **`missing_dispatch_emission`** — an instrumentation finding against the **dispatcher** — never as
   a coverage violation, which is a discipline finding against the **step**. That requires consulting
   a **second, independent evidence source** (the envelope's own completion line, and/or a non-zero
   token record) before concluding "ran inline".
   ⚠ **Also close the false-positive direction**: a roster row whose dispatch is **conditional** needs
   a qualifier the coverage check evaluates. The closure invariant survives — a conditional row is
   still exactly one row.
   *Done when:* both mis-attributions are reproduced in tests and both are corrected.
3. **D3 — the channel-completeness report.** Publish dispatch-line count against envelope-completion
   count, so a sparse channel **downgrades the audit's own confidence**.
   ⭐⭐ **This is the single most reusable idea in this plan**, it generalises to every check in the
   programme that consumes voluntarily-emitted evidence, and it is a **consumer-side change that
   works whether or not the emission fix has landed.** ⭐ **Do it FIRST: it is cheap, it needs no new
   instrumentation** (the envelope completion line is already emitted) **and it makes the emission fix
   measurable when it arrives.**
   *Done when:* the ratio is reported alongside the findings and a deliberately sparse channel lowers
   the reported confidence.
4. **D4 — per-task artifact emission fires for every completed task**, or its scope limit is declared
   in the output so consumers cannot read a partial count as a total.
   ⛔ **The declared scope limit must be a POPULATION statement — "N of M completed tasks emitted" —
   never a non-zero assertion.**
   *Done when:* either emission is complete, or the output states both numbers.
5. **D5 — tests, each verified to FAIL pre-fix**, including one asserting the audit reports a
   deliberately-divergent step.

Five deliverables — at the split guard's edge; evaluate before implementing.

## Out of scope

- **Changing the dispatch-line EMISSION.** ⛔ **Excluded, and this is a settled ownership boundary**:
  a sibling plan owns the emission fix (emitting from the single shared dispatch seam so re-fires
  cannot bypass it). This plan owns the **detector** and the **task-artifact** emitter. Shipping both
  against the emission would produce **two writers for one emitter**.
- **The execute-phase re-entry marker defect** — a first entry logging a re-entry marker, and a
  coverage rule whose precondition is satisfied by the *presence* of a line rather than by the line
  being *correct*. Excluded because it is a different phase and a different bundle, and it is
  independently landable. Record it rather than absorbing it.
- **The aspect-naming defect** (one aspect known by three names, the documented label rejected by the
  registry). Excluded — a different surface, cross-noted only.
- **Retired blocker references.** ⛔ Every sequencing blocker this plan once carried referenced a
  **retired** epic whose plans all shipped long ago. **They are struck.** ⚠ **Do not re-derive a
  blocker from a plan id with no epic-code segment — those are all historical.**

## Expected surface

- The dispatch-audit implementation and its shape-violation check — exact file resolved at outline.
  **HYPOTHESIS.**
- The per-task artifact emission site. **HYPOTHESIS**, verify at outline.
- `test/plan-marshall/phase-6-finalize/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The shape-violation check's second evidence surface has **no producer at all** | **OBSERVED, measured on two independent plans** | ⛔ The measurements are in machine-local run records **not reachable from this clone — do not look for them.** ⭐ **The claim is settleable in the clone and that is the stronger check anyway**: search for any writer of that surface. **If no producer exists, the vacuity is structural and proven from source.** |
| A dispatched step that emitted no line is reported as a discipline violation | **OBSERVED** | Read the coverage check's message construction in the clone — the canonical message asserts the step "ran inline". |
| A conditionally-dispatching roster row produces a false positive on a common change type | **OBSERVED** | Read the roster and the coverage check together in the clone. ⭐ Token attribution independently confirmed no dispatch occurred in that case, so it is a **roster-expressiveness gap, not a lost emission** — do not fix it as an emission bug. |
| Per-task artifact emission fires for a minority of completed tasks | **HYPOTHESIS** | Re-verify at the emitter. ⛔ **And distinguish two causes**: *the step never emits* versus *this run bypassed the emitting path*. Both have been observed, and **scoping the wrong one produces a change that fixes nothing.** |
| Dispatch lines are far fewer than envelope completions, with the gap concentrated in re-fires | **HYPOTHESIS (second-hand)** | ⭐ **D3 makes this measurable rather than asserted** — that is the point of it. Do not quote the ratio; compute it. |
| Step markers cover only some completed steps | **HYPOTHESIS** | ⛔ **Marker absence does NOT mean the step did not run**, so any count derived from markers is a **FLOOR, not a count**. Settle how to enumerate step execution before asserting any coverage claim — **including this plan's own.** |
| Every count named anywhere in this plan | **LEAD, not a fact** | Every arm here names *observed instances*. The population of emission-gap sites and producerless columns is **unmeasured**, and the standing rule applies: **a reported instance is a sample.** |

An asserted **absence** ("nothing writes this surface") is verified exactly as an asserted presence —
and it is the cheapest and most decisive check in this plan. Do it first.

## Verification

- **D1's corrected detector must be shown to FAIL against a deliberately divergent site.** Record the
  failure. A detector that has only ever been observed passing is indistinguishable from the vacuous
  one it replaces.
- **Every reported zero is verified to carry its population.** Hand the audit output to the pre-PR
  verification sub-agent cold and ask, for each zero, whether the check evaluated anything. **If it
  cannot tell, D1 has not been met** — that ambiguity is the defect.
- **D2 is verified in both directions**: a dispatched-but-unlogged step must be reported as an
  instrumentation finding, and a legitimately-inline conditional step must not be reported at all.
- **D4's population statement is verified by a partial case** — some tasks emitting, some not — and
  asserted to report both numbers rather than a non-zero pass.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Ordering against the sibling emission plan.** ⛔ **Run this plan FIRST.** While the audit is
  vacuous, any measurement of the emission divergence reads clean, so the sibling cannot verify its
  own fix until this lands. ⭐ That ordering is doubly motivated: D3's completeness ratio is the
  instrument that will *show* the emission fix working.
- **Both plans edit the same finalize surface** — sequence, never run concurrently.
- **A structural point worth keeping.** Emission is currently an obligation on each individual call
  site rather than a property of the shared path, so any site that forgets produces a dispatch with
  no evidence — and the audit that exists to catch this reads exactly the evidence that is missing.
  ⇒ **A detector that consumes voluntarily-emitted evidence can only ever report a lower bound.**
  D1 is necessary but not sufficient on its own; D3 is what makes the shortfall visible.
