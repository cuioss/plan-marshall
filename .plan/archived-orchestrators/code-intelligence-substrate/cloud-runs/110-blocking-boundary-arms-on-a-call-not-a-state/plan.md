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

# The one blocking gate arms on a call that must happen, not a state that must hold

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

A plan merged with **nineteen quality-gate findings still at `resolution: pending`** — every finding
its six self-review rounds had filed. The gate that exists to prevent exactly that **never evaluated
them**.

The mechanism, read from the invariants module:

- the actionable-finding types **include** the quality-gate type, aggregated at pending resolution;
- the blocking-boundaries set is **exactly one phase** — the finalize phase;
- the raise fires **only when a phase-handshake `capture` call arrives carrying that phase**;
- that run's handshake store carries rows for every earlier phase and **none for the finalize
  phase**.

⇒ ⛔⛔ **No finalize-phase handshake was persisted, so the one boundary where a pending finding
blocks was never reached.** The class docstring claims the intra-finalize boundaries are guarded by
the finalize orchestrator re-issuing that capture; **the run's own handshake store does not
corroborate it.**

**The defect is the arming condition, not the predicate.** The predicate is correct. The gate is
armed by *a call that must happen*, and **a missing call is indistinguishable from a passing gate** —
both leave no row and raise nothing.

## ⭐ Why this is worth a plan even though nothing shipped broken

**No real defect reached main** — the nineteen findings were genuinely fixed; only their records
stayed pending. ⭐ **That is precisely what makes it worth filing: the gate's inertness was invisible
because the outcome was fine.** On a run where the fixes had **not** landed, the same silence would
have shipped them, and the same green report would have been produced.

⇒ The blocking-findings count is **not a trustworthy merge signal on this path**, and anything
reading it as one — including any audit counting *"plans that merged clean"* — is reading a number
nobody computed. **A gate that never ran, presenting as a gate that passed.**

## Goal

*"The gate never ran"* can no longer present as *"the gate passed"*: the merge boundary asserts a
state that must hold rather than trusting a call that must happen, and the self-review loop stops
leaving permanently-pending records behind on plans whose fixes actually landed.

## Deliverables

1. **D1 — GATE: establish the population. Mutates nothing.**
   Across the archived-plan corpus, how many plans carry **no finalize-phase handshake row**, and how
   many of those merged with pending actionable findings?
   ⛔ **Derive the population — do not sample.**
   ⚠ **If the missing row is universal rather than incidental, the remedy is a workflow defect and
   not a guard defect, and D2 changes shape. This gate decides which.**
   *Done when:* both counts are reported with the population size, and the universal-versus-incidental
   question is answered.
   ⚠ **Corpus reachability:** the archived records live under a **machine-local, git-ignored** path
   that is **not present in this clone** ⛔ **— do not search for it.** If no corpus is reachable,
   **derive what can be derived from the clone** (the handshake-writing call sites: is there any code
   path that emits a finalize-phase capture at all?) and **report the population question blocked**,
   rather than assuming either answer. That source-side derivation is often decisive on its own: if
   **no** call site emits it, the row is universally absent and D2's shape is settled without the
   corpus.
2. **D2 — the absence of a finalize-phase handshake row is itself a blocking condition.**
   ⛔ **Convert the arming condition from a call to a state**: the merge boundary asserts the row
   exists, rather than the row's writer asserting the findings are clean.
   ⚠ **This must not become a vacuous guard** — the most-recorded archetype in this project, and one
   **repeatedly introduced BY A FIX for it**.
   ⛔ **Ship a negative-control fixture**: a plan with no finalize-phase row and pending actionable
   findings MUST be refused, and **the fixture must fail against the pre-fix code**.
   *Done when:* the negative control fails before the change and passes after, and a positive control
   confirms a clean plan is still admitted.
3. **D3 — the self-review loop-back path resolves the findings whose fixes it lands.**
   The store accumulated nineteen permanent pending rows on a plan that was, in fact, green.
   ⭐ **D2 and D3 are both needed and neither substitutes for the other**: D2 closes the gate; D3
   stops the gate from having to be closed against a store that is wrong anyway.
   ⚠ **Do not let this auto-resolve a finding whose fix cannot be evidenced** — a finding marked
   `fixed` without a landed change is **strictly worse** than one left `pending`.
   *Done when:* a loop-back that lands a fix transitions the corresponding finding, and a finding
   with no evidenced fix is left alone — both asserted.

Three deliverables with D1 a gate — well below the split guard.

## Out of scope

- **Weakening the predicate.** Excluded because it is correct — the actionable-type set and the
  pending-resolution aggregation both do what they should. The arming is what is broken.
- **Adding more blocking boundaries.** Excluded because the question here is whether the *existing*
  one can be reached, not whether there should be more. Widening the set while the arming defect
  stands would produce more gates with the same silent-pass failure.
- **Any guard shipped without a negative control.** ⛔ Excluded as a matter of method: the
  vacuous-guard archetype has been introduced by a fix for itself repeatedly in this project, so a
  positive-only test is not acceptable evidence here.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — the boundaries
  set, the actionable-type set, and the raise. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — **a second
  consumer of the same set.** **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md` and
  `.../workflow/execution.md` — the contract docs. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — where the missing capture should
  originate, and the merge-boundary assertion's home. **HYPOTHESIS**, verify at outline.
- `.../phase-6-finalize/workflow/pre-submission-self-review.md` — D3's resolution path.
  **HYPOTHESIS**, verify at outline.
- `test/plan-marshall/manage-status/test_manage_status_transition.py` — existing coverage.
  **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The blocking-boundaries set is exactly the finalize phase, the raise is guarded on membership in it, and the actionable types include the quality-gate type | **OBSERVED at HEAD** | `_invariants.py`. ⛔ **Re-read all three — line numbers move and this is the plan's whole premise.** |
| Nineteen quality-gate findings sat at pending at merge, and the handshake store carried no finalize row | **OBSERVED, but the artifacts are NOT reachable from this clone** | Machine-local run records. ⛔ **Do not go looking for them.** ⭐ **The claim is settleable in the clone instead**: if no call site emits a finalize-phase capture, the row's absence is structural. **Derive that.** |
| The missing row is not unique to that one run | **HYPOTHESIS — actively suspected TRUE, and it changes the remedy** | D1. If every orchestrated finalize omits it, the gate has been inert fleet-wide and D2 is a **correctness fix** rather than a hardening. |
| The lifecycle module is a second consumer with the same arming assumption | **HYPOTHESIS** | ⛔ **Read it at outline.** A fix to one consumer that leaves the other is a repeated archetype here — the standing instance is a prefix-set correction applied at one site and not its twin. |
| Any count quoted in this plan | **LEAD, not a fact** | Re-derive at the moment of the claim. |

An asserted **absence** ("no finalize-phase capture is emitted anywhere") is verified exactly as an
asserted presence and is the **higher-risk half** here — it is also the cheapest thing in this plan to
check, and it decides D2's shape. Do it first.

## Verification

- **D2's negative control is the deliverable's proof and must fail pre-fix.** Record the pre-fix
  failure in the run report. A guard whose test never failed before the fix has demonstrated nothing.
- **Both consumers are verified, not just the one that was changed.** If the lifecycle module shares
  the arming assumption, a test must cover it too — otherwise this plan reproduces the second-site
  archetype it names.
- **D3 is verified in both directions**: a finding with an evidenced fix transitions; a finding
  without one does **not**. The second assertion is the important one.
- **D1's honesty**: if the corpus is unreachable, say so and report what the source-side derivation
  established instead. A population figure invented to fill the gap fails the deliverable.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **This is the confident-signal-hides-a-caveat theme in its purest form.** Nothing shipped broken,
  which is exactly why it went unnoticed — and exactly why it is worth fixing before a run where the
  outcome is not fine.
- **Sequencing.** No dependency. ⛔ Never run concurrently with plans touching the finalize dispatch
  surface or the self-review workflow doc. ⚠ A sibling plan touches the same handshake record from
  the capture side — coordinate.
