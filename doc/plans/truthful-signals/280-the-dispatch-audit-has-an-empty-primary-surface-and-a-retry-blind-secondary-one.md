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

# The audit machinery returns values that are not measurements

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

The dispatch-discipline audit exists to catch a step that ran inline when it should have been
dispatched. **Both of its evidence surfaces are broken, in the two different ways this epic tracks**,
and the audit therefore reports clean **for the same reason a healthy plan would**.

⭐⭐ **This is the flagship archetype sitting inside a tool built to detect that archetype.**

**Surface A — the dispatch trail under-counts by roughly 35%, and every gap is a re-fire.** One plan
showed 15 trail lines against ~23 envelopes independently evidenced by their own log prefixes; a second,
different plan showed 11 against ≥17. Steps that fired five times logged once. ⛔⛔ **And the most
consequential dispatch in a plan's life — the step that holds the merge mutex, performs the merge, and
prunes the branch — was entirely absent from the trail.** Under the audit's own coverage rule that is
**indistinguishable from the merge having run inline**.

**Surface B — the primary surface has zero records, ever.** The documented pairing rule pairs an
effort-resolution decision entry with the next dispatch line carrying the same role. **Across 125
decision-log entries there was not one resolution record.** With the left-hand side empty, that check
**can only ever return zero** — structurally incapable of reporting a violation.

⭐⭐ **And the audit still reported three violations — found by going outside the documented rule.** So a
green from this audit is a green from an **undocumented ad-hoc method**, while the documented one is dead
code that has never once been able to fail. ⭐ **The inverse condition actually present — many dispatches
with zero recorded resolves — has no category at all.**

## ⛔⛔⛔ The methodological finding that invalidates the obvious remedy

The natural fix is *"reconcile the two ledgers."* **That remedy is unsound.**

Within one finalize, settle-band fix commits re-staled every head-dependent step: one step ran 5×,
another 7×, another 7× — **and the re-fires emit no step bracket at all.** ⇒ **The step ledger and the
dispatch-boundary ledger under-count THE SAME EVENTS IN THE SAME DIRECTION.**

> **Cross-checking them looks like corroboration and isn't. Two witnesses that share a bias are one
> witness.**

⇒ **The audit needs a third source with an INDEPENDENT emitter — or an explicit statement that no
independent source exists, making the reconciliation a consistency check and never a completeness one.**

⛔ **Three distinct under-count mechanisms are now known, all biased downward, across both ledgers:**
head-advance re-fires emit no bracket; the brackets that *are* emitted have an unguarded open/close
pairing and at least one broken pair; and the dispatch record emits **once per role, not once per
firing**. **A fix for any one of them makes the ledgers agree MORE while remaining wrong.**

⚠ **And the obvious performance fix already landed and did not help.** A change scoping self-review and
gate re-runs to the delta merged **before** the run that measured 5×/7×/7×. **Delta-scoping bounds the
cost of each re-run; it does not stop the re-stale trigger.** ⛔ **Do not read that change as having
addressed this** — it is exactly the kind of landed fix on the same surface that makes a reader assume
the problem is handled.

## The rule this makes concrete

> **A check whose input surface can be empty must report `indeterminate`, never `0 findings`.**
> *"I found nothing"* and *"I had nothing to look at"* must not share a representation.

⚠ This is a clause of a standard **this project already shipped** — the audit violates a rule that
landed in the same change that discovered the violation.

## Goal

No audit surface can report a verdict without stating the population it examined; a re-fired dispatch is
recorded; and where two ledgers cannot corroborate each other, the audit says so instead of treating
their agreement as evidence.

## Deliverables

1. **D0 — GATE: derive the emission population in both directions, and sweep for the token-mismatch
   class.** Mutates nothing.
   - Every code path that creates an execution-context envelope, and every path that emits a dispatch
     record. **The mismatch set is the deliverable.**
   - ⛔ **Sweep for the bare-versus-canonical comparison class.** A one-token vocabulary mismatch —
     comparing against `module-tests` where the composer only ever emits `verify:module-tests` — **has
     silently disabled a production-code safety gate**, confirmed on **three separate plans**. Both
     halves of the system are internally consistent, so **neither side looks wrong on its own**. ⛔ **A
     fix to that one rule leaves the class open.**
   *Done when:* both directions are enumerated with the population stated, and the token-mismatch sweep
   has reported its own population and hit count separately.
   ⛔ **Do not sample.** A per-step table from one run is **what one plan's logs happened to show**. Two
   independent ≈35% measurements establish that the first was not an artifact — ⛔ **they do NOT make 35%
   the population figure.**
2. **D1 — Move the emission into the seam.** Emit the dispatch record **from the dispatcher itself**, so
   no code path can skip it by forgetting to restate a hand-written logging step.
   *Done when:* a re-fire that reuses the envelope **still emits**, and emission is **per firing, not per
   role**.
   ⭐ **Load-bearing — this is the only deliverable that closes the retry blindness by construction**
   rather than by adding more emission sites to forget.
3. **D2 — Every check publishes the population it examined, and can say "could not look."**
   *Done when:* no aspect can return a verdict without a denominator, and an unexaminable input yields
   `indeterminate` rather than a zero.
   ⛔ **A control assertion is REQUIRED**: the check must be **shown to report indeterminate on an
   empty-population fixture**. Without it this is a vacuous guard in a new place — a counter this project
   has already run to n≥5, **with one prior instance introduced by a fix for it**.
   ⚠ **Distinguish an honest not-applicable from a silent skip.** One aspect legitimately skips steps on
   a zero-input and *says so* — **keep it as the matched control**, or D2 will flag honest skips as
   defects.
   ⛔ **Both failure directions are live in one component:** one check emits a **false failure**, another
   emits a **skip indistinguishable from a legitimate one**. A fix that only addresses *"the checks are
   too quiet"* leaves the false-positive arm running.
4. **D3 — Fix the post-merge footprint resolution ONCE.** Multiple aspects report `inconclusive` or scan
   an **empty diff** because the retrospective runs **after** the merge and worktree removal — so the
   commits are already in the main branch and the working diff is empty.
   ⛔ **This is the NORMAL finalize order, not a race**, which means every post-merge retrospective has
   reported a clean scan over an empty diff.
   *Done when:* one shared resolver recovers the footprint from the merge or squash commit when the
   worktree is gone, **and every affected aspect uses it**.
   ⭐⭐ **At least four separate findings are one missing capability. Fix the resolver once; do not patch
   the aspects individually.** The answer was one commit-listing call away in every case.
   ⚠ **Also fix the collapse underneath it**: a diff helper that returns an empty list on a missing
   binary, on a timeout, **and** on a non-zero exit means **a git failure and a genuinely empty diff are
   the same value** — and the consumer reports a leak count with **no denominator at all**.
5. **D4 — Reconcile the documented rule with the method that actually worked, and state the
   corroboration limit.**
   *Done when:* the working method is either promoted to the documented rule or D1's surface carries the
   same information — ⛔ **never leave a documented rule that has never fired standing next to an
   undocumented one that does** — **and** the audit explicitly records that its two ledgers share an
   emitter, so their agreement is a consistency check and not a completeness one.
6. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) A re-fired step emits a dispatch record — **use the observed five-fire shape**.
   - (b) A step that emitted nothing at all now emits.
   - (c) An empty-population corpus yields `indeterminate`, **not** `0`.
   - (d) D0's population is asserted non-empty and **the emission set equals the envelope set**.
   - (e) The token-mismatch rule fires on a footprint it should catch — **a counterfactual with a named
     result already exists**: a re-run against a true nine-file footprint still skipped, and the culprit
     set would have been two production files. That rules out "the footprint was genuinely tests-only."
   *Done when:* all five pass, each seen red first.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables. The source spec, after absorbing
a sibling and several drains, stood at **eleven against a raised cap of twelve** — with its own
instruction that **overlapping deliverables COLLAPSE rather than concatenate**. That collapse is applied
here: the absorbed read-order defect (the retrospective reading a metrics file written *after* it runs)
is **not a separate deliverable but the explanation for why several checks had nothing to examine**, and
it is folded into D2 and D3. ⭐⭐ **That merge is the point: a check whose population is empty because
its source is not yet written is NOT the same bug as one empty by construction — and neither plan alone
could tell them apart. Fixing the checks without fixing the read order would have "fixed" checks that
were never broken.**

## Out of scope

- ⛔ **Reconciling the two ledgers as the primary remedy.** See the methodological finding. It proves only
  that the emitter is self-consistent.
- **Widening the session identifier without fixing the leaf overwrite.** A single-valued field cannot
  hold what a multi-session plan has, and a dispatched leaf overwrites it. ⛔ **The two halves must be
  fixed together — widening alone just loses a different value.** Record it; do not half-fix it here.
- **The per-dispatch billing columns and the short termination-cause enum.** Declared, wired, and **zero
  on every row**, alongside an enum missing several values. ⛔ **Declared-and-always-zero is the worst of
  the three states** (absent / populated / present-but-vacuous), because a consumer sees a column, reads
  zero, and concludes "no context load". **Record both; they need their own plan** — a schema with
  unwired columns *and* a short enum cannot support the audit built on it, and fixing that is not a
  logging change.
- **The last-write-wins phase-step record that erases errored attempts.** It is the mechanism behind two
  errored dispatches appearing as one clean completion. ⛔ **Establish whether it is a gap left open by an
  earlier change or a regression of it BEFORE scoping** — and do that in its own plan.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/**` — the dispatch audit rules and
  the pairing contract.
- The effort/dispatch resolution path — the resolve-target verb, which today logs nothing.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` and its check scripts — the audit's
  consumer, including the manifest-consistency, routing-decisions, chat-signal, and direct-CLI-usage
  aspects.
- `.claude/skills/audit-archived-plan-retrospectives/**`, if the same checks live there.
- Tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 15 trail lines against ~23 envelopes on one plan; 11 against ≥17 on another | HYPOTHESIS | ⛔ **both from run logs under `.plan/`, NOT reachable from this clone.** Precise, internally consistent, and **not independently re-derived**. ⚠ The 23 is itself *"roughly 23"* — **the kind of number D0 exists to replace** |
| Every observed gap is a re-fire | HYPOTHESIS | **confirm by symbol**: is emission first-fire-only from a hand-written step rather than from the dispatcher? |
| The merge/branch-cleanup step is absent from the dispatch trail | HYPOTHESIS | same log provenance — ⛔ **the most consequential instance; re-derive it first** |
| Zero resolution records across 125 decision-log entries | HYPOTHESIS | ⛔ an asserted **absence** over a corpus not reachable here. **Verify the code-side claim instead**: does the resolve verb log at all? |
| The resolve verb has no logging at all, as opposed to logging under a key the audit does not read | HYPOTHESIS | that verb's source — ⚠ **an asserted absence, verified exactly like a presence** |
| The dispatch record emits once per role rather than once per firing | HYPOTHESIS | the emitter — **by symbol.** ⭐ One of three independent downward biases |
| Step brackets are unguarded in their pairing and at least one pair is broken | HYPOTHESIS | the bracket emitter |
| The manifest rule compares a bare token against a canonical prefixed one, and the composer only ever emits the prefixed form | HYPOTHESIS | that check's predicate **and** the composer's decision rule, plus the verb that lists verification steps. ⛔ **n=3 across three plans; the most reproducible claim here** |
| The retrospective runs after merge and worktree removal, so the working diff is empty | HYPOTHESIS | the finalize step order — ⛔ **this is the NORMAL order, so it is checkable directly** |
| A diff helper returns an empty list on failure, timeout, and non-zero exit alike | HYPOTHESIS | that helper — **by symbol** |
| The delta-scoping change landed before the 5×/7×/7× run and did not prevent it | HYPOTHESIS | git history — ⛔ **verify, and do not read it as having addressed this** |
| The checks-over-unexamined-populations class is a property of the checks, not of one run | HYPOTHESIS | ⭐ reported on **two independent plans, six checks**, plus nine further instances in one component. **Re-derive against the CURRENT detector source** — a detector fixed since would refute its instance and re-scope the plan |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5(c)'s control — reporting `indeterminate` on an empty fixture — is the single most important
  test in this plan.** Every other test can pass on a check that examines nothing.
- ⛔ **D4's corroboration-limit statement is text-whose-value-is-what-a-reader-does**, so it gets a **cold
  read**: show the Step 6 verification sub-agent the reconciliation output for two agreeing ledgers, with
  no other context, and ask what it establishes. **The correct answer is "the emitter is self-consistent",
  not "the record is complete."** If the reader treats agreement as completeness, the wording failed —
  and that is the exact error this plan was written to stop.
- **D2 must distinguish the honest not-applicable from the silent skip.** Verify both: the honest one
  stays green, the silent one becomes reportable.
- **Report the population and the hit count separately everywhere.** A count of things examined is a
  volume, not coverage.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⭐⭐ **A general rule worth stating once and citing twice: before treating two signals as corroborating,
  establish that they have independent producers.** The same error was found in an unrelated subsystem
  four hours apart — a cache-pin oracle where the "sole unmarked directory" is a *lagging function of the
  registry* and was being counted as an independent third witness alongside the registry itself.
- ⚠ **An explicit deferral record, carried deliberately.** A sender asked that three named remedies be
  *"either scheduled or explicitly recorded as deferred, so the next retrospective does not report them a
  third time as if they were news."* **This plan is that record**: they are scheduled into D0–D2. ⇒ **If a
  further retrospective reports them, that is not news either.**
- ⚠ **A prior fix at one of these sites made a persist land; it did not make the verdict honest.**
  **Do not assume that site is now understood** — it is a second defect at the same place by a different
  mechanism.
- ⛔ **Do not go looking for the orchestrator spec, the run logs, the archived plans, the drained inbox
  messages, or any landing record.** They live under `.plan/`, which is git-ignored and absent from this
  clone. Where a figure came from there, this file says so and marks it a lead.
