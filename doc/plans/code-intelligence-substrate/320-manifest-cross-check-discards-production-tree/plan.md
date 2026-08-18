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

# The manifest cross-check discards this project's own production tree, then reports zero findings

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The manifest cross-check carries a **private hardcoded prefix list** declaring the project-local
artifact tree to be "bookkeeping" — while this project's own build map classifies the Python files in
that tree as **production**.

**Two components hold contradictory classifications of the same path class, and the one that is wrong
for this repository silently wins.** On a real plan the filter discarded **10 of 11 files**, and every
downstream rule then evaluated a **1-file phantom footprint** — reporting `passed: 2, failed: 0,
findings: 0`. The discarded set included the ~7000-line production module that was **the entire
subject of the plan**.

⛔⛔ **And the private list exists at more than one site.** A sibling check declares **the same
constant with the same literal value in the same bundle**, consumed by the same predicate. ⇒ **The
population is at least TWO, and the originating report named ONE.** ⭐ **This is the epic's own
"a named list is a SAMPLE, not an enumeration" archetype, found inside a spec written to fix a
private-classification-list defect.**

## ⭐⭐ A third defect in the same script: a vacuous skip on the invocation its own documentation prescribes

The skill documentation shows the capture pattern with a **plan-relative** diff-file argument. Run
verbatim it produces a **skip** with *"no realized footprint"*. The **identical file** passed as an
absolute path finds a **real violation**.

**Same file, same content, same run.** ⛔ **The documented form silently degrades and reports skip;
the undocumented form finds the defect.**

**Root cause**: an unresolvable path is treated as *absent* rather than as *supplied-and-unreadable*.
⛔ **A could-not-look is reported with the same token as a nothing-to-look-at**, and skip reads as
benign in every downstream summary. ⚠ **The asymmetry is what makes it invisible**: a caller who
successfully used the relative form on a sibling flag in the same workflow has every reason to expect
it on the next one.

## Goal

The component consults the **declared oracle** instead of its own guess, at **every** site that
carries a private copy; a rule whose input set was reduced **says so** in its verdict; and a supplied
but unresolvable input is never reported with the same token as an absent one.

## Deliverables

1. **D0 — GATE: derive the population of private classification lists. Mutates nothing.**
   Enumerate every component carrying its own hardcoded notion of *"is this path implementation"*
   instead of querying the oracle.
   ⚠ **Population-derived, not the sites this plan names** — at least one site was missed by the
   originating report. **Report the count found separately from the number of components examined.**
   *Done when:* the population is enumerated from source and published.
2. **D1 — replace the private prefix lists with an oracle lookup**, at **every** site D0 found.
   A path whose resolved role is production or test is implementation; only config or unclassified
   paths are bookkeeping.
   ⭐ The genuinely-runtime state directory may stay hardcoded — it appears in no build map.
   ⛔ **Do not scope this to a single named file**, or the fix ships against half the population and
   the guard passes over the half it changed. **Every site moves, or the deliverable states why one
   does not.**
   *Done when:* each site queries the oracle, asserted per site.
3. **D2 — a rule whose input set was reduced MUST report the reduction.** Surface the filtered count
   in the verdict, or downgrade the rule to `indeterminate`.
   ⛔ **A clean pass with zero findings must not be emittable when the large majority of the supplied
   footprint was discarded before evaluation.**
   *Done when:* a reduced input set produces either a reported reduction or an indeterminate verdict —
   never a bare pass.
4. **D3 — fix the unreachable rule in the same file.** It compares a step list against a value the
   composer never emits in that form, so the predicate **can never fire**.
   ⚠ This was a standing unowned defect; it lands here because it is the same file and the same class
   (a detector that cannot detect).
   *Done when:* the rule fires on the composer's actual step-list shape.
5. **D4 — a supplied-but-unresolvable path fails loudly or resolves as documented.**
   Either resolve a plan-relative argument against the plan directory — matching both the documented
   capture pattern **and** the sibling flag that already accepts that form — or **fail loudly**.
   ⛔ **Do not report skip.** Whichever is chosen, **the documentation and the script must agree**;
   today they do not, and the disagreement is silent **in the direction of a clean result**.
   *Done when:* the documented invocation and the absolute-path invocation produce the same verdict.
6. **D5 — tests, each verified to FAIL pre-fix.**
   (a) a multi-file footprint under the project-local tree survives the filter intact;
   (b) a rule fed a reduced input set reports the reduction rather than a bare pass;
   (c) the previously-unreachable rule fires on the composer's real step-list shape;
   (d) the documented relative-path invocation produces the same verdict as the absolute one.

Six deliverables with D0 a gate — **at the split guard**; the third-defect fold pushed it there.
⚠ **Verify at outline whether the count still clears the guard**, and if D0 finds a materially larger
population, **stage the sweep separately rather than growing this plan.**

## Out of scope

- **Consolidating the oracle itself.** Excluded — this plan is one **consumer** adopting the oracle,
  not the consolidation. ⚠ **And a standing position that the build map *is* the oracle is a position,
  not a verification** — ⛔ **do not treat it as confirmation that the lookup API exists in the shape
  this plan needs.**
- **The auditor's other detector-integrity defects.** ⛔ Excluded deliberately: that plan sits at its
  own split guard with an explicit *do not add to it*. **Staging separately is the split-guard rule
  working as intended, not duplication.** ⛔ The unreachable rule **moved here** — do not re-add it
  there.
- **Attribution of the project-local tree to a module.** Excluded — a sibling plan owns it. **Not a
  duplicate: different maps in different files** — but ⚠ **re-check the interaction at outline**, since
  changing how these predicates classify those paths is visible to it.

## Expected surface

- The manifest cross-check — the private prefix constant, the rule-evaluation path, and the
  unreachable rule. **OBSERVED.**
- The routing-decisions check — **the SECOND site with the same constant and the same predicate**, and
  the diff-file resolution. **OBSERVED.**
- The oracle lookup API the components must call. **HYPOTHESIS — locate before scoping.**
- The retrospective reference docs describing the cross-check's contract and the capture pattern.
  **HYPOTHESIS**, verify at outline.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| A private prefix constant declares the project-local tree to be bookkeeping, filtered before any rule is evaluated | **OBSERVED, quoted from source** | The constant and its comment, in the clone. ⛔ **Re-derive the location — this plan must not pin to a line.** |
| **A second, identical constant exists in a sibling check in the same bundle** | **OBSERVED** | Both files. ⭐ **This is why D0 exists.** |
| A real footprint was reduced to a single file and the rules then reported a clean pass | **OBSERVED, measured** | ⛔ The measurement is from a machine-local run ⛔ **not reachable here — do not look for it.** ⭐ **Reproduce in the clone**: run the check with a footprint of project-local production files and observe the filtered count. |
| The build map classifies those Python files as production | **HYPOTHESIS — and it is LOAD-BEARING** | ⛔ **D1's entire remedy is "consult the oracle", so the oracle's actual content must be READ, not assumed.** |
| Several rules are skipped as a **consequence** of the filter rather than for independent reasons | **HYPOTHESIS** | The rule-evaluation site. |
| The unreachable rule's predicate cannot fire for the stated reason | **HYPOTHESIS (inherited, previously unowned)** | The predicate symbol. |
| The documented relative-path invocation degrades to a skip while the absolute form finds a violation | **OBSERVED, first-party, same file and same run** | ⭐ **Reproducible in the clone — run both forms.** This is the cheapest and most decisive check in the plan. |

## Verification

- **D1 is verified per site**, not once. ⛔ A fix asserted only at the originally-named file leaves the
  population half-fixed and the guard passes over the half that changed.
- **D2 is verified adversarially**: feed a footprint that the filter reduces and assert the verdict is
  **not** a bare pass.
- **D4 is verified by equality**: the documented invocation and the absolute-path invocation must
  produce the **same verdict** on the same file. That equality is the deliverable.
- **Each test is verified to fail pre-fix.** Record the failures.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- ⭐ **Two archetypes at once**: **source-of-truth duplication** (a private list mirroring a set defined
  authoritatively elsewhere) and **confident-signal-hides-a-caveat** (zero findings over a small
  fraction of the real input). ⭐ It is also **the same archetype the audited plan was itself fixing** —
  which is why the pattern is worth fixing at the **oracle** rather than at the site.
- **Serialization.** Shares the retrospective bundle with sibling plans and the detector surface with
  the auditor plan — sequence, never run concurrently.
