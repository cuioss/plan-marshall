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

# `error` does not mean "produced nothing" — fix the proxy before sizing the lever

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## ⛔⛔⛔ Read this section before scoping anything: the founding premise is REFUTED

This plan was staged on the reading that a dispatch stamped `termination_cause=error` **produced
nothing**, and that a large share of finalize's dispatch spend therefore bought nothing.

**That reading is false, and it was measured first-party.** On one instrumented run, five of six
`error`-stamped dispatches in the finalize phase were the plan's **most productive** dispatches:
each found defects, filed findings, and returned for a loop-back. They carry the token the taxonomy
reserves for *"the dispatch raised a fatal error"*.

**The root cause is a vocabulary gap.** The dispatch termination taxonomy models how a dispatch
*stopped* but not the *verdict* a review-shaped dispatch returns. A findings-bearing return is a
**success of the step and a non-completion of the loop**, and only the second half has a token — so
the loop-back path falls through to `error`.

⭐ **The plan is not invalidated; its target is.** The principle stands exactly: *a dispatch that
examined nothing and returned nothing costs real tokens and buys zero detection capability, so
removing its cost removes nothing*. What is refuted is the **proxy** — `error` is not that
population. ⛔ **Fix the proxy first**, or this plan reproduces the sample-is-not-a-population error
it exists to detect.

## Problem

Two things are wrong, and the first must be fixed before the second can even be measured.

**The taxonomy cannot express a productive non-completion.** There is no member meaning *returned
with findings* / *loop back*. The step-completion surface already has a loop-back outcome with a
classifier; the dispatch ledger has no counterpart. This is the same shape as a previously-documented
carve-out where a deterministic, legitimate termination was counted as the failure mode until it got
its own member.

**Genuinely wasted dispatch spend is invisible inside an aggregate.** A dispatch that truly
terminated without producing anything costs full context and is not reported as a distinct quantity,
so nobody can act on it.

## Goal

A dispatch that returned findings is stamped as such rather than as an error; the population of
dispatches that genuinely produced nothing is separately identifiable; and that waste is a
**published figure** rather than one a reader must reconstruct from a ledger.

## Deliverables

1. **D1 — GATE: give the taxonomy a member for a productive non-completion, and widen the rule that
   reads it.**
   Add a `returned_with_findings` (or `loop_back`) termination cause and route the finalize
   loop-back path to it.
   ⛔ **Widening the taxonomy alone fixes only half.** The rule that audits these causes is scoped to
   the execute phase's boundary file only — the finalize file, which is where the mis-stamping was
   measured and which carries the majority of the spend, **is read by no rule at all.** Widen the
   rule's scope in this same deliverable.
   *Done when:* a loop-back dispatch is stamped with the new member, and the audit rule reads the
   finalize boundary file — both asserted by tests that fail before the change.
   ⚠ **Coordinate the vocabulary with the boundary-ledger plan — do not ship two writers for one
   taxonomy.**
2. **D2 — GATE: are the four per-dispatch token columns produced at all?**
   The per-dispatch token columns have been observed uniformly zero across multiple ledgers —
   **unproduced, not sparse** — because producers omit the flags and the defaults persist *as though
   measured*.
   ⛔ **The choice is binary and both arms are acceptable; silence is not.** Either **populate** them
   at the dispatch boundary, or **drop them from the schema** so nothing reads a manufactured zero.
   ⚠ Note the asymmetry with a shipped decision elsewhere that emits an attribution group
   unconditionally so *"a zero is a measured zero"*. That reasoning is sound **only while an absent
   field and a zero field remain distinguishable on disk**; these columns are the case where it
   already failed. **Whichever arm is taken must state how a reader tells a measured zero from an
   unproduced one.**
   *Done when:* the columns either carry real values or are gone, and the measured-vs-unproduced
   distinction is representable and tested.
   ⛔ **This plan cannot compute any share of dispatch spend until D2 is settled** — if the cost
   attribution reads those columns today, it reads zeros.
3. **D3 — re-derive the population, first-party. Mutates nothing.**
   Sweep for dispatch records whose terminal state is genuinely non-productive, report their count
   and token cost as a share of dispatch spend, **and report the population size**.
   ⛔ **Derive the terminal-state vocabulary from the schema**, not from the two names that happened
   to be observed — they are a sample, not the enum.
   ⛔ **Re-derive against finding-yield**, per the refutation above: a dispatch that returned
   findings is the opposite of this plan's target.
   ⚠ **This deliverable needs a corpus of archived records — see the scope note below.**
4. **D4 — separate RETRYABLE from TERMINAL.** A dispatch blocked by a session restart is
   infrastructure; one that errored may be deterministic. ⛔ **They need different remedies, and
   conflating them produces a fix for the wrong half.**
   *Done when:* the two classes are reported distinctly.
5. **D5 — make the waste a reported figure, not a derivable one.** Genuinely-wasted dispatch spend
   gets its own field, so a reader sees it without reconstructing it.
   *Done when:* the field is emitted and covered by a test.
   ⭐ This is the standing rule applied here: **a quantity nobody publishes is a quantity nobody acts
   on.**

**Scope note on the corpus (applies to D3, and to D4's class shares).** The originating measurements
came from archived run records under a **machine-local, git-ignored** path that is **not present in
this clone**. ⛔ **Do not search for it.** ⛔ **If no population of archived records is reachable here,
HALT D3/D4's measurement and report them blocked on corpus availability** — then ship D1, D2 and D5,
which are all code changes in this clone. **Do not substitute a hand-assembled corpus, and do not
quote a share derived from a single run.**

⚠ **Do not compute a share against a denominator that has not been settled.** A sibling plan owns a
coverage ratio that has rendered a numerator larger than its denominator; **that plan is this one's
blocker for any share figure.**

## Out of scope

- **"Retry less" and "give up earlier on hard dispatches."** ⛔ Excluded on principle: these are
  examination reductions wearing this plan's clothes. The measured finding is that cost per
  defect-found *improved* when effort rose, so any lever whose mechanism reduces to *examine less* is
  rejected **on that ground, not weighed**. The target is the **cost of a failure**, never the
  willingness to attempt.
- **The full-surface re-sweep loop.** Excluded because a separate, already-shipped plan addressed
  re-sweeps that **do** examine. Different mechanism, different fix, and neither subsumes the other.
- **The coverage-ratio defect itself.** Excluded because a sibling plan owns it; this plan consumes
  its result as a denominator.

## Expected surface

- The dispatch-boundary record writer and the ledger it writes. **HYPOTHESIS**, verify at outline.
- The finalize dispatcher's terminal-state handling. **HYPOTHESIS**, verify at outline.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/` — the taxonomy and D5's reported field.
  **HYPOTHESIS**; resolve the owning module at outline rather than assuming.
- The logging-gap rule whose scope must widen to the finalize boundary file. **HYPOTHESIS**, verify
  at outline.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `error`-stamped dispatches include the most productive dispatches in a run | **OBSERVED — and it REFUTES this plan's founding proxy** | The measurement is in a machine-local record ⛔ **not reachable from this clone; do not look for it.** Confirm **in the clone instead** by reading the termination-cause enum: if it has no member for a findings-bearing return, the mis-stamping is structural and the claim is settled without the record. **Do that.** |
| The termination taxonomy has no member expressing "returned with findings" | **OBSERVED, and clone-reachable** | The enum definition under `marketplace/bundles/plan-marshall/skills/manage-metrics/`. Read it. |
| The step-completion surface already has a loop-back outcome with a classifier | **OBSERVED, clone-reachable** | The step-completion verb's surface. Confirms the counterpart exists on one side and not the other. |
| The four per-dispatch token columns are uniformly zero because nothing produces them | **HYPOTHESIS** | ⛔ **Re-derive in the clone**: find the producer, or establish there is none. **This is an asserted absence and carries the higher verification burden** — if a producer exists and is merely unwired, D2 changes shape entirely. |
| The audit rule is scoped to the execute-phase boundary file only | **HYPOTHESIS** | Read the rule's scope in the clone before widening it. |
| The originating share figure ("a third of finalize dispatch spend") | **RETIRED AS EVIDENCE** | Measured over a **mixed population** — see the refutation above. ⛔ **Do not quote it.** D3 re-derives or reports blocked. |
| Any count or share quoted anywhere in this plan | **LEAD, not a fact** | Re-derive at the moment of the claim. |

## Verification

- **D1 is verified by a loop-back that actually happens**: exercise the loop-back path and assert the
  new member is what lands in the ledger. A unit test over the enum alone does not show the path was
  rerouted.
- **D2's chosen arm is verified by a negative control**: whichever arm is taken, assert that a
  measured zero and an unproduced column are **distinguishable**. If they are not, the deliverable
  has not been met regardless of which arm was implemented.
- **D3's honesty is the deliverable.** A halt with a clear statement of what was unreachable is a
  success; a share quoted from one run is a failure even if the number looks reasonable.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why this lever is the right shape.** The binding anti-goal here is that lowering examination
  depth is not a sanctioned saving. This lever is the opposite shape: a dispatch that examined
  nothing and returned nothing is *bytes that buy nothing*, which is where the savings actually are.
  ⛔ The refutation above does not weaken that argument — it removes a **bad proxy** for the
  population, which is why D1 comes first.
- **Adjacent constraint.** If any deliverable computes a per-phase figure, note that a re-entered
  phase row blends cumulative and last-close fields; use the published value-scope fields rather than
  hand-deriving which figures a re-entered row mixes.
