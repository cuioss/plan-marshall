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

# Split the user configuration doc, derive its coverage against the real knob population, and evict the meta-project content

**Epic:** truthful-signals
**Branch prefix:** chore

## Problem

`doc/user/configuration.adoc` is by a wide margin the largest user document — roughly **587 lines
across 26 subsections** under five top-level sections, against ~195 and ~55 for its siblings. It
**admits its own coverage gap in prose**, and it carries meta-project-only content on a
consumer-facing page.

Three findings shape the work:

**1. The split convention already exists — follow it, do not invent one.** `doc/user/` already holds
topic pages carved out of this same document (`efforts.adoc`, `parallelism-and-locking.adoc`,
`terminal-title.adoc`). ⭐ **And the leftover-stub pattern is already demonstrated in-file**: one
subsection is three lines that point at `efforts.adoc` rather than duplicating it. **That is the target
shape for every extraction** — a short pointer stub, not a deletion, so existing cross-references and
reader habits survive. ⛔ **Do not invent a `configuration-part-2.adoc` scheme.**

**2. ⛔ The document enumerates the knobs it does NOT document — in a hand-written prose list.** A
single parenthetical names roughly 25 knobs and then says *"see the canonical per-key reference."*
⭐ That half-answers the coverage question and names its own authority: the population is the config
skill's data-model standard, and the sweep is a **mechanical diff** of the doc's covered set against
that key set.
⛔ **But the parenthetical is itself the defect this epic tracks: a DERIVABLE SET WRITTEN AS
NARRATIVE.** It will drift the moment a knob is added, and nothing detects it. **Do not rewrite it as
a better prose list.** Generate it, or replace it with a pointer and let the data-model standard be the
single enumeration. **A hand-maintained "everything else" list is a guaranteed future divergence.**

**3. ⚠ The meta-project content is identifiable, and one class of it is subtler than prose.** There is
an explicit *"meta-project derived-state caveat"* paragraph, **and** a mid-sentence mention embedded in
a lane description — **prose-embedded, not a separable block, so a section-level move will miss it**.
⚠ **And the interesting one:** the document's primary "for everything else, see X" escape hatch links
into `marketplace/bundles/...` from roughly ten places. **If a consumer-project reader does not have
`marketplace/bundles/` present, the document's main escape hatch is broken for exactly the audience it
is written for** — which would make this the highest-value part of the work, not the tidying part.

## Goal

The configuration documentation is split along the existing convention with every extraction leaving a
working stub, its coverage is derived against the real knob population rather than asserted, the `lane`
vocabulary is documented from a settled definition, and no consumer-facing page carries meta-project-
only content or a reference a consumer cannot follow.

## Deliverables

1. **D1 — GATE: derive the population and settle the split.** Mutates nothing. Four things:
   - **Derive the knob population** from the config skill's data-model standard, cross-checked against
     the code-side defaults, and diff it against what the document actually covers. **Output the
     covered / uncovered / mentioned-but-undocumented split as a LIST, not a count.**
     ⛔ **Re-derive rather than trusting the in-file parenthetical — that list is the artifact under
     suspicion.**
   - **Settle the reference-link question** from finding 3. It decides whether the meta-project work is
     a *move* or a *re-pointing*, and it may be the highest-value item in the plan.
   - **Decide the split boundaries**, preferring extraction into **existing** topic pages over new files
     wherever a home already exists. Every extraction leaves a pointer stub in the demonstrated style.
   - **Confirm the `lane` vocabulary** before anything is documented — see D2.
   *Done when:* all four are settled and recorded, with the population's derivation method stated.
   ⛔ **STOP CONDITION.** If the data-model standard turns out **not** to be a complete enumeration —
   if it is itself a sample — **halt and report that.** Documenting coverage against a partial
   population would produce a confident completeness claim that is false, which is this epic's
   archetype committed in the document meant to fix it.
2. **D2 — Document the `lane` configuration.**
   ⛔ **BLOCKED ON A REAL AMBIGUITY — do not document the enum until it is settled.** Three sources
   disagree: a validation constant admitting `off, minimal, standard, full, ask`; a nearby comment
   saying `off, minimal, standard`; and a finalize-steps constant admitting `off, standard, full` —
   **which the `set-lane` verb validates against, so it rejects `minimal`.** A separate tier constant
   defines the lattice as `minimal, standard, full`, with `off` and `ask` being **dispositions, not
   tiers**.
   The narrow list may be legitimately narrower (it describes *the resolved answers an `ask` can
   produce*), but **`set-lane` accepting a different set than the override validator is a divergence a
   user hits directly.**
   *Done when:* the authoritative set is settled and documented — or, if it cannot be settled without a
   code change, **the divergence is reported as a defect and the enum is left undocumented.**
   ⛔ **Documenting the current state as-is would encode a contradiction into the user documentation,
   which is worse than the present silence.**
   ⚠ Also disambiguate the two unrelated concepts sharing the word: the **planning lane**
   (`light`/`deep`) and the **finalize step lane**. They share nothing but the noun, and one sentence in
   the document currently names both.
3. **D3 — Split, with pointer stubs.** Execute D1's boundaries.
   *Done when:* every extracted section has a stub at its origin and **no content is deleted** — every
   line either moves or stays.
4. **D4 — Close the coverage gap.** Document the uncovered knobs D1 identified, and **replace the
   hand-written parenthetical** — generated or pointer, ⛔ **never a new prose list**.
   *Done when:* the uncovered set is documented and the narrative enumeration is gone.
5. **D5 — Evict meta-project content.** Move the explicit caveat, and **sweep for prose-embedded
   mentions**.
   *Done when:* the sweep is done and every hit is moved or re-pointed per D1's verdict.
   ⚠ **A section-level move will miss the embedded ones** — search the whole file for `meta-project`,
   `sync-plugin-cache`, `deploy-target`, `target/claude`, and `marketplace/bundles`.
6. **D6 — Verification.** Cross-reference integrity across the split — **every moved anchor still
   resolves, including from files outside `doc/user/`** — plus the documentation lint gates.
   *Done when:* all inbound references resolve.
   ⚠ **The stubs are load-bearing here**: an extraction without a stub silently breaks inbound
   cross-references, and "silently" is the operative word.

Six deliverables, at the split presumption. **No split** — D1's derivation feeds D2–D5, and D6 verifies
the whole move. Splitting would ship a partially-split document with dangling references.

## Out of scope

- **Changing any knob's behaviour or default.** This is documentation. A defect found while documenting
  is **reported**, not fixed — notably the `set-lane`-versus-validator divergence in D2, which is a code
  defect surfaced by a docs plan and belongs in its own change.
- **Restructuring `doc/developer/`.** Content is evicted *into* it; reorganising it is a different job
  with a different audience.
- **Documenting knobs that a sibling plan is about to materialise.** See the sequencing note — the two
  plans must share one derived population, not race to describe different ones.

## Expected surface

- `doc/user/configuration.adoc` — the subject.
- `doc/user/efforts.adoc`, `doc/user/parallelism-and-locking.adoc`, `doc/user/terminal-title.adoc` —
  extraction targets and the stub precedent.
- `doc/developer/**` — destination for the evicted meta-project content; the exact file is **not yet
  chosen**.
- `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` — **read-only**, the
  claimed knob population.
- Inbound cross-references from `doc/concepts/`, `doc/developer/`, and bundle documentation.

⭐ **`doc/**` is disjoint from every other plan in this epic**, which all sit in `marketplace/bundles/`.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including every count and line
number. ⭐ **Asserted absences are the higher-risk half.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The document is ~587 lines across 26 subsections, far larger than its siblings | HYPOTHESIS | the file itself — **re-derive; the count is a lead** |
| A three-line pointer stub precedent already exists in-file | HYPOTHESIS | that subsection — locate **by heading**, not by line |
| A parenthetical hand-lists ~25 undocumented knobs | HYPOTHESIS | that paragraph — by content |
| The data-model standard is a **complete** knob enumeration | HYPOTHESIS | ⛔ **REPORTED, not verified. D1 must confirm it is the population and not itself a sample** — the entire coverage claim rests on it |
| Three sources disagree on the `lane` value set, and `set-lane` validates against the narrow one | HYPOTHESIS | the three constants and the `set-lane` validation path — **by symbol**. ⛔ This is D2's blocker and must be settled, not worked around |
| An explicit meta-project caveat paragraph exists, plus at least one prose-embedded mention | HYPOTHESIS | the file — the embedded one is the **easy-to-miss** half |
| The document's canonical-reference links point into `marketplace/bundles/` from ~10 places | HYPOTHESIS | the file. ⛔ Then the real question: **does a consumer-project reader have that tree?** An asserted **absence** on the consumer side, and **not directly verifiable from this clone** — settle it from how the documentation is distributed, and if it cannot be settled, say so rather than guessing |
| No sibling document already covers the sections being extracted | HYPOTHESIS | ⛔ asserted **absence** — check the three sibling pages before extracting, or the split creates duplicates |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **The stubs get a cold read**, because their whole value is what a reader does with them: give the
  Step 6 verification sub-agent one stub with no other context and ask where to find the content. If it
  cannot say, the stub is a deletion with extra steps.
- ⛔ **D4's replacement for the parenthetical must not be a prose list.** Verify by reading what shipped:
  if the new text enumerates knobs by hand, the deliverable has recreated the defect and must be
  reworked, however complete the enumeration looks today.
- **D6's cross-reference check must include references from outside `doc/user/`.** Checking only within
  the directory is the sampling error that makes a split look clean while breaking every inbound link.
- **D1's coverage output must be a list, not a count.** A count cannot be checked; a list can.
- Documentation-only changes are expected, so the build gate will likely take its docs-only path.
  **Confirm from git evidence rather than assuming.**

## Notes

- ⚠ **Sequencing — prefer running AFTER the knob-surfacing plan in this epic.** That plan materialises
  every seeded-able knob into the config file, making the population derivable from the file itself. If
  this plan lands first, D4 documents a set that the other plan then widens, and the documentation goes
  stale immediately. **They are not duplicates** — one is code, one is docs — **but they must share one
  derived population.**
- ⭐ The framing *"verify all config aspects available and ensure that each is documented"* is a
  **population-derivation gate**, which has been the highest-value deliverable in several consecutive
  plans in this project. **D1 is that gate; it mutates nothing and should be graded on its own.**
- ⛔ **Do not go looking for the orchestrator spec or any landing record.** They live under `.plan/`,
  which is git-ignored and absent from this clone. Everything needed is in this file.
