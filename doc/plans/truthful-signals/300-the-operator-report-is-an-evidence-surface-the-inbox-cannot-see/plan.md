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

# The plan's terminal report — one emission, at the end, in a slot that exists

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

> **A plan reports its outcome to two audiences over two channels, at a time when neither channel can
> yet carry the truth, into an ordering space with no room to fix it.**

| End | Symptom |
|---|---|
| **What** | The inbox gets narrative; the operator report gets per-step outcomes, totals, repository state. **They are not the same facts.** |
| **When** | The landing is emitted at `order: 991` — **three steps and two producers before the run ends.** |
| **Where** | `998 → 999 → 1000` is contiguous. **There is no slot for a terminal step.** |

### A. The channel gap is systematic, and it is cross-repository

**Seven findings across two runs existed ONLY in the operator report**: a fourth token total 3.4% from
the others (*the magnitude that gets quoted rather than investigated*); a housekeeping step reporting
`0 removed, 0 promoted, 0 adapted, 180 retained` on a run whose own log declared its input unavailable;
the **runtime** step order rather than the order the merged tree shows; a merge call returning
`merged: true` on an unmerged branch; a total that exposed a three-way disagreement; a split guard never
evaluated; a review-bot withdrawal.

⭐ **Operator, first-party:** *"After the last plans I started again pasting the result and **always** the
result has additional infos."* ⇒ **Not an incident. Every run.**

⭐⭐ **Cross-repository corroboration:** another repository's orchestrator **drained and reconciled
correctly from its inbox** — shipped, landing written, rows stamped, spec archived — **and the paste
still carried three things the inbox lacked**, including a version-cut deadline on two standing public
elements. ⇒ ⛔ **The gap is a property of the CHANNEL, not of drain discipline.**

### B. The emission is not terminal

The merge and its outcome are produced at `order: 70`. The landing emission sits inside a step at
`991`. The run's token totals are produced at `998`. The archive path at `1000` — and ⭐ **the source
says why `archive-plan` runs last: it moves the plan directory out from under every later reader.**

⛔⛔ **An earlier retirement of this exact finding was OVER-BROAD.** It was marked superseded because a
change had moved the emitting step into a post-merge band. **That closed write-before-MERGE and left
write-before-TERMINUS open — post-merge is not terminal.** ⭐⭐ **And the disproving fact was held at the
same moment**: the same review recorded that the retrospective at `995` runs before metrics at `998`,
and then never ran the identical arithmetic on the step being retired. ⇒ **A retirement justified by a
sibling's evidence still needs its own arithmetic.**

### C. The order space is saturated, collides, and has no contract

1. ⛔ **The terminal region is SATURATED** — `998 → 999 → 1000` contiguous. **No slot exists.**
2. ⛔ **A real same-phase COLLISION at `order: 9`** — two of *our own* steps share it. ⚠ **Another
   duplicate pair is CROSS-phase and is NOT a collision — do not "fix" it.** ⭐ It is also the *only*
   evidence the space is per-phase, which is **stated nowhere.**
3. ⛔ **No allocation contract.** Several declarations are project-local steps interleaved with the
   shared ones: third parties allocate into **one flat integer space with no reserved band and no
   collision check.** ⭐ **The live collision is between two of our own steps**, so the mechanism needs no
   third party to fail.

⭐ The shape is dense low, sparse middle, then a jump to a late band — **accreted, not designed.** The
late band means "late" with no room reserved inside it.

⭐⭐ **The window is open only until the version cut**: renumbering breaks consumers that pin an order,
and it is free only for now. ⛔ **Leaving it is not neutral; it is a choice with an expiry date.**

### D. And ordering alone cannot fix it

Two further independent reports name the same seam and add what a slot number cannot express:

- The retrospective is ordered **after the steps that destroy its inputs** — it reads a metrics file
  written later, **and** it runs after the worktree is removed. ⛔ **Its slot is perfectly legal; the
  worktree's absence is what makes it wrong.**
- A housekeeping step at a very early order reads an artifact produced near the end **and cannot be
  relocated**, because band membership requires it not to mutate source. ⇒ **Two steps mis-ordered, one
  structurally immovable under the current band rule.**

⛔ ⇒ **The ordering contract must express *"reads X"* and *"destroys X"* as declared facts, not merely a
slot number.**

### E. A second, independent defect at the same seam

The retrospective **unconditionally rebinds the session it measures** — it captures the *currently
running* session into the plan's session field, and a later step's enrichment resolves the session from
that rebound value. On one run it was armed to enrich against a session containing **none of the earlier
phases**.

⇒ ⭐ **This is NOT fixed by re-ordering.** Moving the retrospective later still leaves an unconditional
overwrite of a field a later step reads. ⛔ **The ordering half and the rebinding half must be fixed
together** — fixing the order alone leaves a mis-attributed enrichment; fixing the rebind alone leaves
the retrospective reading an un-enriched store.

⭐⭐ **The consequence names this plan's thesis exactly.** A sibling plan shipped a billing-cost column
and a partiality declaration; both **passed verification and are operationally inert in their own
output** — every phase renders "coverage undecidable" and the cost column is empty. **The plan was
raised because someone asked "why did this cost so much?" The report now has a cost column, and it is
empty.** ⚠ And the operator's own report says the deliverable *is* working. ⭐ **Both are true at
different sampling points** — the later step populates what the earlier one could not see.

## Goal

The terminal report is **one emission, at the end, in a slot that exists**, carrying machine-readable
facts; the ordering space has a banded allocation contract with reserved gaps and a collision check that
fails; and no step silently overwrites state a later step reads.

## Deliverables

⚠ **Nine deliverables — far past the split guard, BY EXPLICIT OPERATOR DECISION ("no split").** ⭐ The
rationale is recorded rather than assumed: **these were three specs describing one seam from three ends,
and splitting a seam is precisely how this codebase produces half-fixes.** A previous change fixed
write-before-merge and left write-before-terminus. A renumber without a contract would re-accrete. A
landing carrying more facts, emitted at the same wrong time, still cannot carry the ones produced after
it. ⚠ **The honest risk of one plan is a long run with many loop-backs. Sized deliberately, not
overlooked.**

⛔ **INTERNAL ORDER IS LOAD-BEARING: D3 must FIRE on the live collision BEFORE D2 fixes it.**

### Phase 1 — the space

1. **D0 — GATE: derive the population and the semantics, in both directions.** Mutates nothing. Every
   order declaration — ⛔ **re-derive; any count in this file is today's answer, not an inheritance** —
   plus two questions the space's behaviour depends on: **is the space per-phase or global?** and **what
   is the tie-break for equal orders?**
   *Done when:* the population is derived and both semantics are answered **from the composer's source**.
   ⛔ **Read the composer — do not infer from output.**
   ⚠ Enumerate consumer repositories' declarations too; this tree is not the only one writing the key.
   ⛔ **Also confirm whether the plan's source identifier is available at COMPOSE time** — D5 depends on
   it, and if it is only available at runtime, D5's shape changes and observability gets *harder*.
2. **D1 — A banded allocation contract with RESERVED gaps.** State the bands, their meaning, and which
   ranges are **reserved for project-local and third-party steps** versus **owned by the shared
   bundle**.
   *Done when:* the contract is documented with **insertion room inside every band**, and the ordering
   key can express **"reads X"** and **"destroys X"** as declared facts.
   ⛔ **The contract is the deliverable; the renumbering is its consequence.** ⭐ **The defect is a band
   with no gaps** — sparse-by-convention is not sparse-by-guarantee.
3. **D2 — Resolve the live same-phase collision deliberately.**
   *Done when:* the two steps have distinct orders **and the intended order was established first**.
   ⚠ **Today's behaviour may already depend on the accidental tie-break.** ⛔ **Do not renumber them
   apart and assume the observed order was correct.**
4. **D3 — A collision check that FAILS.** No two same-phase steps may share an order.
   *Done when:* it is **verified to fire on the live collision BEFORE D2 fixes it.**
   ⛔ **Sequencing is load-bearing: fixing D2 first destroys D3's fixture.**
   ⭐ **Extend the existing step-discovery test rather than adding a competing checker** — a new checker
   would be yet another restatement of the pipeline order.

### Phase 2 — the emission

5. **D4 — A dedicated terminal step, in a slot D1 created.**
   *Done when:* the emission is the last thing that happens before the archive step.
   ⛔ **The archive step stays last.** ⚠ **Do NOT relocate the currently-emitting step wholesale** — its
   other work is legitimately mid-band; **only the emission moves.** ⭐ **Separating the two is the
   point**: relocating a whole step past what it needed is how the read-direction defect was created.
6. **D5 — The step exists ONLY under an orchestrator.**
   *Done when:* a non-orchestrated plan composes the step **out**, as an **observable compose-time
   decision** — ⛔ **never a silent runtime no-op.**
   ⭐ **The existing detection verb is the single sanctioned seam.** ⛔ **No second detector, no new
   persisted field** — that skill's contract says so, and a second producer over one field is a defect
   this epic has already shipped a plan for.

### Phase 3 — the payload

7. **D6 — Derive the report↔inbox DELTA, in both directions.**
   *Done when:* the set difference is derived **over at least three archived plans** — one run's delta is
   a sample — and **every item is classified MECHANISABLE or NARRATIVE-ONLY**.
   ⛔ **The set difference IS the payload specification.**
   ⭐ **The seven known report-only findings are the non-empty control: if the derived delta lacks them,
   D6 is wrong.**
   ⛔ **At least one known item may not be mechanisable at all** — the false-merge report arrived as
   operator narrative, not as a step fact. **Say so rather than forcing it.**
8. **D7 — The terminal emission carries the facts, machine-readable.** Consume the existing typed facts
   map.
   *Done when:* the emission carries typed facts, not prose.
   ⭐ **The schema already exists with both-direction guards — this is a ROUTING gap, not a modelling
   problem.** ⛔ **Do not re-narrate facts into prose**; the plan that built that map found precisely
   that prose step records are not facts. ⚠ **Verify the report actually renders from that map**; if it
   renders from something else, D7's source changes.
9. **D8 — A drain-completeness check, and retire the workaround.** After a drain reports zero, the
   orchestrator must be able to establish nothing material is outstanding.
   *Done when:* the check exists, is **verified to FAIL on a pre-fix archived plan** where the delta is
   known non-empty, and the report **states explicitly whether the manual paste is retired — naming any
   residue that is irreducibly narrative and therefore correctly keeps it.**
   ⛔ **A completeness check that passes on a known-incomplete input is the vacuous guard this project
   counts at n≥5.**
   ⭐⭐ **The operator is the oracle: this is done when a paste stops yielding anything new.**

## Out of scope

- **Fixing the totals' sampling point itself.** A sibling plan owns it. ⭐ **This plan removes the
  *reason* for partiality at the landing**; it does not fix the sampling defect. **Serialize against it.**
- **Renumbering consumer repositories' declarations.** ⛔ **It is NOT ESTABLISHED whether any consumer
  actually pins an order that D1 would break** — the project-local declarations examined were all in this
  tree. **Derive it at D0; do not assume either way.**
- **Two transferable classes carried from another repository's report** — a comment explaining *why* a
  guard exists being load-bearing (a guard was deleted while its justifying comment stayed), and an
  anchor that appears to bound and does not (a `$`-anchored pattern still admitting a trailing line
  terminator). ⛔ **Neither is ours to fix** — different language, different repository. Recorded because
  both are this epic's theme, and the second is *a validator that looks total and is not*.

## Expected surface

- Every finalize workflow and standards document's frontmatter carrying an `order`, plus the
  project-local step skills under `.claude/skills/`.
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py` — the
  default step list.
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/orchestrator.py` — the
  detection and inbox-write verbs.
- `marketplace/bundles/plan-marshall/skills/manage-status/**` — the typed facts map.
- A new finalize step document plus the dispatch table; the standards document where the emission lives
  today; the inbox envelope standard; the orchestrator's analyze workflow (D8); the extension-api
  documentation where `order` is described for third-party authors.
- `test/plan-marshall/phase-6-finalize/**`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The order declarations, the saturated terminal region, and the same-phase collision | HYPOTHESIS | ⛔ **re-derive every one.** A first attempt at this asserted a free terminal slot from four steps it had read, and **a full sweep refuted it within the hour** ⇒ ⭐ **a list produced by looking is a SAMPLE, not an enumeration — knowing the archetype does not protect against it; only running the enumeration does** |
| The archive step runs last because it moves the plan directory out from under later readers | HYPOTHESIS | that step's own source — **reachable and cheap** |
| Seven findings existed only in the operator report | HYPOTHESIS | ⛔ **run reports under `.plan/`, not reachable here.** ⭐ **But the fact this plan needs — that a paste carried what the inbox did not — is established by the act of pasting**, independently of any technical claim in it |
| The cross-repository corroboration | HYPOTHESIS | ⛔ **second-hand and unverifiable from this checkout.** Same note as above applies |
| The space is per-phase | HYPOTHESIS | ⛔ **strongly suggested by one cross-phase duplicate pair, and stated NOWHERE.** If it is global, that pair **is** a collision and D2 grows |
| The composer's tie-break for equal orders | HYPOTHESIS | ⛔ **NOT ESTABLISHED — deliberately not claimed.** The colliding pair may be deterministic (discovery order, name) or not. ⚠ **Do not report "undefined order" as an impact until the composer is read** |
| Any consumer project pins an order D1 would break | HYPOTHESIS | ⛔ **NOT ESTABLISHED. Consumer repositories were not read** |
| The detection verb suffices to gate composition at compose time | HYPOTHESIS | **D0's compose-time check** — D5's shape depends on it |
| The retrospective unconditionally rebinds the session it measures | HYPOTHESIS | that step's first action, **by symbol** — ⛔ **checkable from source, and the most self-contained claim here** |
| The typed facts map exists with both-direction guards | HYPOTHESIS | the status skill — ⭐ **if true, D7 is routing, not modelling** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D3 must be SEEN to fire on the live collision before D2 fixes it.** This is the one ordering
  constraint in the plan that cannot be recovered later: once D2 lands, the fixture is gone.
- ⛔ **D8 must be SEEN to fail on a known-incomplete input.** A completeness check that only ever passes
  is the vacuous guard this plan exists to stop shipping.
- ⛔ **D1's contract is text-whose-value-is-what-a-reader-does**, so it gets a **cold read**: give the
  Step 6 verification sub-agent the new contract with no other context and ask where a third-party step
  that must run after the merge but before the archive should be numbered. **If it cannot answer, the
  bands have no usable gaps** — which is the defect restated.
- **D6's delta must include the known control items.** A derived delta that misses them is measuring the
  wrong thing, however clean it looks.
- Python, documentation, and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Cross-epic: another epic owns the post-run band contract** — whether a source-mutating step may be
  post-run. ⛔ **A banded allocation contract must not contradict it. Align before implementing D1.**
- ⚠ **A terminal emission IS a termination signal by construction**, which substantially overlaps a
  sibling plan's inbox-protocol work and reduces the need for an amend verb. **Re-evaluate both after
  this lands.**
- ⛔ **Do not go looking for the orchestrator spec, the archived plans, the run reports, the drained
  messages, or the other repository's report.** They live under `.plan/` or outside this repository, and
  are absent from this clone. Everything this plan needs is stated above; where the evidence is
  second-hand, this file says so.
