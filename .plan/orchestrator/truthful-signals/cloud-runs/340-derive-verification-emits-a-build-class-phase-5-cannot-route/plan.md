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

# `derive-verification` emits a build class the execute phase cannot route

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

The architecture skill's `derive-verification` emits compile and test-compile `build_class` commands
that the execute phase's per-task routing **cannot map to a valid canonical step**. Manifest
composition then fails with an unresolvable-step error.

⭐ **And the emission reports `status: success` while producing the unroutable command.** The failure
surfaces **two components downstream, at compose time, where its cause is no longer visible.**

⭐⭐ **The dedup evidence is the most interesting part of this finding.** Five separate lessons were
filed over four days against **three different components** — and they are **one defect**. Each was
filed **from the side it happened to fail on**, which is exactly why the duplication went unnoticed for
days.

⚠ **All of that is SECOND-HAND.** Those are corpus lesson texts relayed by a lessons-handling run;
**no symbol was read.** Per this project's standing rule, **a claim repeated across five messages is
still ONE SOURCE until independently derived.**

## Goal

An emitter cannot produce a `build_class` that has no route; a payload carrying an unroutable command
cannot report success; and if compose still fails, its error names which emitter produced the command
and under which class.

## Deliverables

1. **D0 — GATE: re-derive the defect against HEAD before scoping anything.** Mutates nothing.
   *Done when:* the emission site and the compose resolution site are **read by symbol**, and the defect
   is confirmed or refuted at HEAD.
   ⛔ **STOP CONDITION, and refutation is a legitimate outcome.** The source lessons are weeks old and
   **a fix may have landed since.** ⛔ **If HEAD refutes it, the plan CLOSES as already-fixed and the
   corpus lessons are retired — that is a successful run, not a wasted one.** Do not manufacture work to
   justify the launch.
   ⚠ **Resolve every component name to a file and a symbol first.** The cluster names components, and **a
   component name is not a file.**
2. **D1 — Constrain the emitter to routable classes only.** An unroutable class is **a failure at
   emission**, not a success payload that breaks compose later.
   *Done when:* the emitter validates against the registered route set **derived from that registry**,
   not from a hand-listed copy of it.
   ⛔ **Do not hard-code the valid class list at the emitter.** A second copy of a vocabulary is how this
   kind of mismatch is born.
3. **D2 — Make the emitter's status honest.** A payload containing an unroutable command **must not**
   return success.
   *Done when:* the status reflects the payload.
   ⭐ **This is the deliverable that matters even if D1 turns out to be hard**: a truthful failure at the
   emission point is diagnosable; a success that breaks two components later is not.
4. **D3 — Give the compose error its provenance.** The unresolvable-step error names **which emitter
   produced the command, and under which class**.
   *Done when:* the next instance is diagnosable **at the point of failure**.
   ⭐ The reason five lessons were filed instead of one is that **nobody at the failure site could see
   where the command came from.** D3 is the fix for the *dedup* problem, not just the routing one.
5. **D4 — Tests: a matched control pair.**
   - A **routable** class composes successfully.
   - An **unroutable** class is **refused at emission and never reaches compose**.
   *Done when:* both pass, and each was seen to fail pre-fix.
   ⛔ **The routable half is not optional** — a validator that refuses everything satisfies the negative
   case alone.

Four deliverables, under the split presumption.

## Out of scope

- **Redesigning the build-class vocabulary.** The plan makes the emitter agree with the router; deciding
  which classes *should* exist is a different question with a wider surface.
- **Fixing the routing table to accept the emitted class.** ⛔ That would be the wrong direction unless
  D0 establishes the class is legitimate and the router is the one that is wrong. **If D0 finds that,
  say so and re-scope** rather than silently reversing the fix's direction.
- **Retiring the corpus lessons.** They live in a store this run cannot reach. ⛔ **Record in the report
  which lessons this closes**, and leave the retirement to a local run — see Notes.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-architecture/**` — the `derive-verification`
  build-class emission site.
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/**` — the compose step resolution
  that raises the unresolvable-step error.
- `marketplace/bundles/plan-marshall/skills/phase-4-plan/**` — the stamping site that writes the command
  into a task's verification commands.
- Tests.

⛔ **Every surface entry above is a HYPOTHESIS on purpose.** The source named *components*, and a
component name is not a file. **Resolve each to a file and a symbol at D0 before scoping on it.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `derive-verification` emits build classes the execute phase cannot route | HYPOTHESIS | the emission site § the class emission, and the compose resolver § the unresolvable-step raise — **both by symbol. D0 owns this** |
| The emission reports success while carrying an unroutable command | HYPOTHESIS | the emitter's return path — ⭐ **the half that makes this an epic-theme defect rather than a plain bug** |
| Five lessons across three components are one defect | HYPOTHESIS | ⛔ **SECOND-HAND: corpus lesson texts relayed by another run, with no symbol read.** ⚠ **Five reports of a defect are not five observations of it** — one source until independently derived |
| The cluster reports eight corpus instances | HYPOTHESIS | ⛔ **a count over a corpus not reachable from this clone.** A **lead**, and not a basis for sizing |
| The defect is still live at HEAD | HYPOTHESIS | ⛔ **D0, and the whole plan turns on it.** The source lessons are weeks old |
| A registered route set exists that the emitter can validate against | HYPOTHESIS | the routing registry — ⛔ an asserted **presence**. **If there is no single registry, D1 grows and must be re-sized** rather than improvising a second list |
| Nothing already validates the emitted class | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — check before adding a validator |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D0's verdict must be explicit in the report, including a refutation.** *"Confirmed at HEAD, here
  are the two symbols"* and *"refuted at HEAD, here is the fix that landed"* are both complete outcomes.
  **Silence is not.**
- ⛔ **D4's routable control is what stops the over-broad fix.** A validator that refuses every class
  would pass the unroutable case and break every plan.
- **D3's provenance must be verified by reading an actual error**, not by inspecting the code that
  formats it. The test is whether a reader of the error can find the emitter.
- **D1's route set must be derived, not copied.** Verify by checking that adding a class to the registry
  makes the emitter accept it **without a second edit**.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⭐ **The most transferable thing here is why the duplication happened**: five people each filed from
  the side the failure surfaced on, and none could see the emitter. **D3 exists to make that impossible
  next time** — which is worth more than the routing fix itself.
- ⚠ **Sequencing:** a sibling plan on build-gate coverage parity may touch the same class vocabulary.
  **Check at outline; if it does, serialize.** Another sibling covers a hard-coded toolchain in the same
  build-class family — **different axis, no file overlap expected.**
- ⛔ **Do not go looking for the orchestrator spec, the lessons corpus, the cluster record, or any
  landing record.** They live under `.plan/`, which is git-ignored and absent from this clone. **Record
  which lessons this closes in the run report** so a local run can retire them.
