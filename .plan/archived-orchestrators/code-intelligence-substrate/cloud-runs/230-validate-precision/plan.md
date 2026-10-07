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

# Make the broken-reference validator precise enough to gate on

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The dependency validator is the closest thing this repository has to a corpus-wide broken-reference
gate, and it **cannot be used as one**: it reports a large unresolved set, and the visible sample is
dominated by false positives from **three distinct detector confusions**.

1. **Documentation placeholders counted as references.** The literal placeholder string used *when
   documenting the notation itself* is detected as a reference to a component of that name.
2. **Subcommands misread as scripts.** A three-part notation whose final segment is a **subcommand of
   the skill's entry script** is treated as a separate script that does not exist.
3. **Canonical command references counted as script notation.** Build-command references share the
   three-part shape and are resolved as if they named scripts.

A gate whose findings are mostly false trains readers to ignore the category — and this validator is a
**hard prerequisite** for any editor-facing surface, which would otherwise stream confident-wrong
diagnostics straight into an editor.

## Goal

The validator's findings are precise enough to gate on: the three false-positive classes are no longer
detected as references, the genuinely-broken residue is enumerated and either fixed or filed, and a
regression fixture keeps each class from returning.

## Deliverables

1. **D0 — GATE: classify the FULL unresolved set. Mutates nothing.**
   ⛔ **The originating analysis read only a fraction of the rows — that is a SAMPLE, not an
   enumeration**, and this project has already been bitten by exactly that.
   *Done when:* every unresolved row carries a class (placeholder / subcommand / canonical command /
   genuinely broken), and the per-class counts are published.
   ⛔ **Do not carry a "most of them are false positives" claim into the fix without this
   enumeration.**
2. **D1 — stop counting documentation placeholders as references.**
   *Done when:* prose documenting the notation produces no finding, asserted by fixture.
3. **D2 — stop misreading a subcommand as a script.**
   ⚠ **One branch may be the whole of this class**: the notation parser appears to treat *any*
   three-part notation whose middle segment is not one of a small reserved set as a script. **Read
   that branch first** — the fix may be far smaller than the class suggests.
   *Done when:* a subcommand reference resolves rather than reporting unresolved.
4. **D3 — stop counting canonical command references as script notation.**
   *Done when:* a build-command reference produces no finding.
5. **D4 — re-baseline and report the real unresolved set.** Genuinely-broken references are then fixed
   or filed.
   ⭐ **If the residue turns out to be EMPTY, the plan ships D1–D3 plus D5 and reports zero real
   breakage — that is a SUCCESS, not an under-delivery.** Say so plainly.
   *Done when:* the post-fix set is published with its population.
6. **D5 — a precision regression test**: a fixture containing **one instance of each false-positive
   class plus one genuinely-broken reference**, asserting **exactly one** finding.
   *Done when:* the fixture exists and the assertion is exact — not "at least one", not "no
   placeholders".
7. **D6 — documentation.** Update the validator's contract: what it detects, what it **deliberately
   does not** treat as a reference (placeholders, subcommands, canonical commands), and whether its
   output is now gate-grade. If it becomes a gate, the page describing repository quality gates must
   say so. ⛔ Ship docs **in this plan**.

Seven deliverables — **past the split guard.** ⚠ **Evaluate the split at outline and record the
verdict**; the natural cut is (D0+D1+D2+D3: the three false-positive classes) and (D4+D5+D6:
re-baseline, fixture, contract).

## Out of scope

- **Redesigning the detection layer.** Excluded — the three classes are expected to be separable
  within the existing parser. If they are not, that is a finding to report, not a licence to rewrite.
- **Fixing every genuinely-broken reference found.** Excluded as a blanket obligation: D4 fixes or
  **files** them. A large residue is a separate body of work and should not be absorbed silently.
- **Building an editor-facing surface over this.** Excluded — a sibling plan owns it, and it is
  **gated on this one** precisely because false diagnostics in an editor are the highest-visibility
  form of this epic's own archetype.

## Expected surface

- `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_detection.py`
  — the notation parser and the detectors. **OBSERVED.**
- `.../tools-marketplace-inventory/scripts/_dep_index.py` — the resolution pass. **HYPOTHESIS**,
  verify at outline.
- `.../tools-marketplace-inventory/SKILL.md` — the validator's contract. **OBSERVED.**
- `test/pm-plugin-development/` — the precision fixture and tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The validator reports a large unresolved set against a much larger dependency total | **OBSERVED — run live at staging time** | ⛔ **Re-run it in the clone.** Every number is a **LEAD**: the corpus moves, and no count in this plan may be carried into the fix. |
| Placeholders, subcommands and canonical commands each appear in the unresolved set | **OBSERVED** | Re-run and inspect. Each class is confirmable from the output plus the parser. |
| The **majority** of unresolved rows fall into these three classes | **HYPOTHESIS (a derived count)** | ⛔ **D0.** The originating read covered a fraction of the rows. **A reported list of instances is a sample, not an enumeration** — classify all of them before scoping. |
| The three classes are separable in the existing parser without a redesign | **HYPOTHESIS** | Read the notation parser and the script detector. ⚠ **The parser's "any three-part notation whose middle segment is not reserved is a script" branch may be the whole of class 2** — check that first. |
| A genuinely-broken residue exists at all | **HYPOTHESIS** | ⭐ D4 explicitly permits an empty residue as a success. **Do not assume breakage exists in order to have something to fix.** |

An asserted **absence** ("these references are not real breakage") is verified exactly as an asserted
presence — which is what D0's classification is for.

## Verification

- **D5's assertion must be EXACT.** A fixture asserting "at least one finding" passes against a
  detector that still reports all four rows. The count is the test.
- **Each false-positive fix is verified by its own fixture case**, and the genuinely-broken case is
  verified to **still** be reported — a precision fix that also suppresses real findings has made the
  gate worse, not better.
- **D0's classification is published with per-class counts**, so a later reader can tell how the
  residue was derived rather than trusting a summary.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why precision before presentation.** This converts a useful query tool into an enforceable
  contract. ⛔ **It must land before any editor-facing surface over the same data** — surfacing a
  set with a large false-positive share into an editor is this epic's own archetype at its
  highest-visibility point.
- **Serialization.** Shares the inventory skill with sibling plans — do not run those concurrently.
- **Dependency.** The index's file coverage affects the baseline; a coverage change underneath this
  work would shift the re-baseline. Confirm the coverage situation in the clone before D4.
