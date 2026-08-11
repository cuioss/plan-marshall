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

# The executor generator fails open, and its fixtures are structurally unable to notice

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

Two defects with one root: **the executor's surface derivation cannot tell "derived nothing" from
"derived everything", and the suite that guards it is built from fixtures that cannot express the
difference.**

**A — the generator is fail-open at the last gate.** A documented executor regeneration reported
`status: success` while producing a **surfaces-less executor**: an invalid invocation fell through
to argparse *after* spawn instead of being rejected pre-spawn, so the pre-spawn guard was not live
despite a green sync and a green regeneration. Recovery required running the generator directly
against merged source, which then derived its full surface set.

⛔ **The only observable distinguishing the two outcomes is the ABSENCE of a surface-stats line, and
nothing consumes an absence.** The same shape was hit independently twice within a single run, so it
is a recurrence rather than a one-off.

**B — the fixtures cannot see a strip-the-attribute defect.** The run that shipped the guard found
four defects in it — every one a valid call refused or an operator misdirected — and **every one was
caught by running the guard live, none by the test suite**:

| # | Defect | Why the suite missed it |
|---|---|---|
| 1 | `--help` refused on **every** script (`reason=unknown_flag, accepted=[]`) | no fixture had an empty flag set |
| 2 | a leading top-level flag desynchronised the parser walk — the same two accepted tokens came back for *different* verbs, so the walk never left the root node | no fixture invocation started with one |
| 3 | short `-h` still refused after the `--help` fix | zero occurrences of the token anywhere in the test tree |
| 4 | the `unknown_flag` corrective advertised a set **contradicting its sibling corrective** on the same node — an operator following it is refused on the next attempt | no fixture declared a flag that was also universal |

⛔⛔ **The root cause, stated exactly:** it shipped past a green synthetic suite **because every
fixture surface happened to declare at least one flag**. A hand-built fixture is written to be
*representative*, and therefore **populated** — which makes the entire class *"the derivation strips,
omits, or mis-attributes attribute X"* **structurally invisible**, because X is only absent on a
surface nobody would hand-write.

## Goal

A regeneration that derives nothing where something was derived before **fails loudly**, the
surface-stats line is emitted unconditionally so consumers assert on a value rather than infer from
an absence, and the guard's fixture corpus is derived from the real surface index so that dropping
an attribute fails a test instead of shipping.

## Deliverables

1. **D1 — fail a regeneration that derives zero surfaces where the previous one had surfaces.**
   The generator already computes reused and derived surface counts, and already knows the outgoing
   entry count. When the previous count is greater than zero and the new generation emits zero
   (neither derived nor reused), **exit non-zero rather than reporting success.**
   ⛔ **Emit the surface-stats line UNCONDITIONALLY, including the zero.**
   *Done when:* a regeneration forced to derive zero against a non-empty previous state exits
   non-zero, and the stats line is present in **both** the zero and non-zero cases — asserted by a
   test that would fail if the line were emitted only when non-empty.
   ⭐ *An absence nothing consumes is not a signal* — state that as the contract in the emission
   surface, not as a code comment.
2. **D2 — derive the fixture corpus from the real surface index.** The generator produces an index
   of registered scripts and derived surfaces. A test that walks **that index** and asserts every
   registered notation's `--help`, `-h`, and declared-flag invocation is accepted is
   **population-derived**, so it fails the moment the derivation drops an attribute — which four
   hand-built rounds could not do.
   ⛔ **Publish the population size** in the test's output.
   *Done when:* the test enumerates the index rather than a literal list, publishes the count it
   enumerated, and fails when an attribute is stripped from the derivation.
   ⛔ **Do not sample the population.** A sampled population-derived test is a hand-built fixture
   with extra steps. If the full corpus is too slow for the edit-time gate, move it to a slower
   tier — do not thin it.
3. **D3 — make a regenerate-and-dispatch live smoke part of shipping a validator change.** All four
   defects were caught that way and none by the suite.
   ⛔ **This is NOT "add more unit tests."** It is evidence that the synthetic and live surfaces
   differ in a way the suite cannot self-detect.
   *Done when:* the smoke exists as a required step (not a reviewer's judgement) and **includes a
   help spelling and a leading top-level flag** — the two shapes that actually bit.

Three deliverables — well below the split guard.

## Out of scope

- **Hardening the repair path.** Excluded because it already works: every one of the four fixes
  shipped with a fail-first proof and matched negative controls, so the fix could not read as
  disabling validation. **The gap is detection, not remediation** — spending this plan on repair
  would harden the half that is not broken.
- **Hand-written fixtures for the four known defects.** Excluded because that is the exact move that
  produced the blind spot: it fixes four instances and leaves the class. D2 is the alternative.
- **The plugin-registry pin inversion.** Same failure *class* (the on-main executor disagrees with
  merged source), **different mechanism** — that one is a registry-versus-cache problem repaired by
  hand, this one is a generator fail-open. ⛔ **Do not merge them.** A fix for one does not cover the
  other, and reporting them together would hide that.
- **Changing the shipped pre-spawn guard's behaviour.** Excluded because the guard itself works —
  this plan is about the **regeneration path** that can leave it inert. Do not conflate the two.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/tools-script-executor/` — the generator and the executor
  template. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/argparse_surface.py` — the
  derivation. **OBSERVED.**
- `test/plan-marshall/tools-script-executor/` — the fixture corpus. **HYPOTHESIS**, verify at
  outline.
- `test/_shared/_dispatch_roster.py` — the population-derived shape to copy. Read, not edited.
  **HYPOTHESIS**, verify at outline.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The shipped pre-spawn guard works and its corrective is on **stdout** (it survives `2>/dev/null`) | **OBSERVED** | Re-derive by running an invalid invocation in the clone. ⇒ **Arm A is about the regeneration path, not the shipped guard.** Do not conflate them. |
| A regeneration reported success while producing a surfaces-less executor | **OBSERVED, but the evidence is NOT reachable from this clone** | The observation lives in a machine-local run log under the git-ignored `.plan/` tree. ⛔ **Do not go looking for it.** The claim is confirmable **in the clone instead**, by reading the generator's success path: if it can return success with a zero surface count, arm A is confirmed without the log. **Do that.** |
| The four false-rejection defects, each with a live reproducer | **OBSERVED, same reachability caveat** | Confirm the *class* in the clone by reading the derivation for attribute-stripping paths, not by hunting the run record. |
| Every hand-built fixture declared at least one flag | **HYPOTHESIS — and it is the plan's load-bearing premise** | ⛔ **Re-derive it in the clone**: enumerate the fixture corpus and count how many declare an empty flag set. If some already declare one, D2 changes shape. **This is an asserted absence and carries the higher verification burden.** |
| A population-derived corpus is affordable at the current script count × three invocations | **HYPOTHESIS** | ⚠ The derivation probes per parser node under a per-probe timeout and a shared wall-clock deadline, so a full-population test **may be too slow for the edit-time gate**. **Measure at outline**; if it is too slow, move the tier — do not sample. |
| Part of D1 may already exist | **HYPOTHESIS** | ⛔ **Re-ground arm A against HEAD before scoping.** The originating run shipped generator guard-ordering changes as in-radius consequences, so some of D1 may be present already. Building it twice is the failure this label prevents. |
| Script and surface counts quoted anywhere in this plan | **LEAD, not a fact** | Re-derive in the clone; the tree the run sees is not guaranteed to match the tree these were taken from. |

## Verification

- **D1 is verified adversarially**: force a zero-surface derivation against a non-empty previous
  state and assert a **non-zero exit**. A positive-only test (normal regeneration still succeeds)
  passes against the defect and proves nothing.
- **D2 is verified by breaking the derivation on purpose**: strip an attribute and confirm the
  population-derived test **fails**. A green run against an unmodified derivation is not evidence
  that the test can see the class.
- **D3's requiredness is verified by a cold read.** Whether the smoke is a *required step* or a
  *suggestion* is entirely a matter of how a later reader takes the text. Dispatch the pre-PR
  verification sub-agent to read it cold and report which reading it took.
- **Self-exercisability is better than assumed and should be used.** Phase-5 of a run generates a
  worktree-bound executor, so regenerating inside this very run exercises the guard end-to-end
  against the real notation set. The boundary is main-checkout-and-cache-scoped, **not absolute** —
  so a live end-to-end exercise is available to this plan and should be taken.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why this sits near the top of its workstream.** It is two of this project's standing rules
  colliding in one place: *every set-guarding detector must be population-derived*, and *probe the
  objective live*. Arm A is also a **second, independent mechanism** by which the on-main executor
  silently disagrees with merged source — and a pre-launch check for the *other* mechanism does not
  cover it, because this one manufactures a green finalize over an inert guard.
- **Sequencing.** No dependency; the surface this repairs has already shipped. ⛔ **Never pair with
  the self-review-surfacing plan** — both change what "population-derived fixture" means in this
  repository, so land one and read it before scoping the other.
