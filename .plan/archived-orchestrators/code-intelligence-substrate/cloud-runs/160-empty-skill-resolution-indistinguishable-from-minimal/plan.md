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

# An empty skill resolution is indistinguishable from a deliberately minimal one

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

At task-allocation time, a task whose module and profile resolve **no** architecture-provided skills
is handled identically to one that resolves a **deliberately minimal** set: both degrade silently to
the persona floor. The task then runs, produces output, and **nothing reports that its methodology
skills were absent.**

## ⭐ The masking effect is what makes this a fix rather than a note

The observed instance: a module-testing-profile task resolved the persona floor **only**, with no
architecture-resolved defaults.

The proximate cause was a **task mis-domaining**, and it was fixed in-plan by re-domaining the task.
⛔ **But a mis-domained task hits the SAME empty resolution as a genuinely empty inventory**, so the
symptom is easy to misdiagnose as an allocation bug and "fix" **without ever touching the
inventory — which is exactly what happened. The real inventory gap survived the fix.**

⇒ **Two distinct causes converge on one indistinguishable observable, and the cheaper explanation
wins every time.** That is the defect: not the empty set, but the fact that the two cannot be told
apart at the moment someone is deciding what to fix.

## ⛔ The design caveat that makes a naive fix worse than the defect

⛔ **A fix that simply ERRORS on an empty set will be worked around by inserting a placeholder skill,
and the signal is lost again — this time invisibly, because the inventory will then look populated.**

⇒ A deliberately-minimal profile needs a way to **say so**. The distinction must be **expressible in
the inventory, not inferred from cardinality.** Two sibling plans in this epic defend a
closed-vocabulary, fail-closed posture; **align with that rather than inventing a third mechanism.**

## Goal

"The inventory answered nothing" is a distinct, named condition at allocation time, separable from
"the inventory answered, and the answer is small" — reportable without being fatal, and impossible to
launder by inserting a placeholder.

## Deliverables

1. **D1 — GATE: re-ground against the current tree. Mutates nothing.**
   ⚠ The originating observation was checked against a bundle version that **predates this tree**.
   Confirm or refute that an empty resolution is still indistinguishable from a minimal one at
   allocation time **today**, and **name the resolution site**.
   ⛔ **Do not build on a version-stale observation.**
   *Done when:* the resolution site is named with its symbol, and the indistinguishability is either
   confirmed or the plan re-scoped on the refutation.
2. **D2 — make the two states distinguishable in the inventory.**
   A profile that is deliberately minimal must be able to **declare** it. Settle the mechanism
   against the existing closed-vocabulary posture and **record the reasoning**, including what makes
   the *next* unmarked-empty profile detectable.
   *Done when:* the declaration exists in the schema and an undeclared empty is representable as a
   distinct state.
3. **D3 — report the named condition at allocation time.**
   An unresolved profile — as opposed to a declared-minimal one — emits a distinct, named condition
   rather than degrading silently to the persona floor.
   ⛔ **The condition must be reportable without being fatal.** An empty inventory in a consuming
   project is a real state; hard-failing it **strands that project rather than informing it**, and
   that is contrary to the project's no-vacuous-success posture, which asks for a reported condition
   rather than a crash.
   *Done when:* the condition surfaces in allocation output and does not abort the run.
4. **D4 — a test that fails today, in BOTH directions.**
   A task whose profile resolves nothing is asserted to surface the named condition; a task whose
   profile resolves a **declared-minimal** set is asserted **not** to.
   ⛔ **Both directions, or the fix is the vacuous guard this epic keeps finding** — an assertion
   that only checks the empty case cannot detect that the declared-minimal escape hatch swallowed it.
   *Done when:* both assertions exist and the empty-case assertion is verified to fail before the
   fix.

Four deliverables with D1 a gate — below the split guard.

## Out of scope

- **A consuming project's own inventory gap.** ⛔ Explicitly excluded: a genuinely empty profile in
  someone else's repository is a **repo-side fix** tracked in their own ledger. It is not a bundle
  item and not this plan's — **do not let the outline drift into fixing their data.**
- **Hard-failing on an empty resolution.** Excluded per D3's reasoning: it converts an informative
  state into a broken one for every consuming project with a sparse inventory.
- **Inventing a new vocabulary mechanism.** Excluded — align with the existing closed-vocabulary
  posture. A third parallel mechanism for "this value is deliberate" is the drift this epic keeps
  paying for.

## Expected surface

- The task-allocation skill-resolution site in the planning phase. **HYPOTHESIS**, verify at outline.
- The architecture skill's profile-to-skills producer and its schema. **HYPOTHESIS** — resolve the
  owning module at outline rather than assuming.
- The persona resolution verb, **if** the persona floor is applied there rather than at allocation.
  **HYPOTHESIS**, verify at outline.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| An empty resolution is indistinguishable from a deliberately minimal one at allocation time | **HYPOTHESIS (second-hand, and version-stale)** | **D1 is this verification.** ⛔ The originating check ran against a bundle predating this tree. **Re-derive at the resolution site in the clone.** |
| The observed task resolved the persona floor only | **OBSERVED (reported first-party by the filer), but the artifact is NOT reachable from this clone** | It lives in a machine-local run record. ⛔ **Do not go looking for it.** The *mechanism* is confirmable in the clone by reading the resolution site — do that instead. |
| A naive error-on-empty fix will be worked around with a placeholder skill | **HYPOTHESIS about future behaviour, stated as a design constraint** | Not verifiable in advance; it is why D2 exists. Treat it as binding rather than as evidence. |
| The three surfaces named under Expected surface are where the change lands | **HYPOTHESIS** | Resolve each at outline; the resolution site named by D1 is the anchor, the rest follow from it. |

An asserted **absence** ("nothing reports the missing skills") is verified exactly as an asserted
presence — confirm at the allocation site that no such report exists before building one.

## Verification

- **D4's two-directional assertion is the deliverable's proof.** A test suite that only covers the
  empty case passes against a fix whose escape hatch silently swallows the signal — which is the
  precise failure mode D2 introduces the escape hatch for. **Both, or neither counts.**
- **The empty-case assertion is verified to FAIL before the fix.** Record the pre-fix failure; a test
  whose pre-fix behaviour was never observed proves nothing.
- **D3 is verified to be non-fatal**: a run against an empty inventory must complete and report,
  not abort.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Provenance and ownership.** This item was raised by another epic and **delegated here, removed
  from their ledger** — one owner, not two. They noted it is also *their* archetype (a signal that
  cannot distinguish "nothing to report" from "nothing was looked at") and offered to take it back on
  that basis. **The decision recorded is to keep it here**, because the routing rule goes by subject
  and the subject is inventory resolution.
- **Sequencing.** No dependency. ⚠ Aligns with two sibling plans on the closed-vocabulary posture —
  check surface disjointness before running alongside either, since a shared vocabulary mechanism is
  exactly the same-namespace-different-file shape that has cost this epic time before. ⛔ Never run
  concurrently with the architecture-store concept-model plan — both touch the store's schema.
