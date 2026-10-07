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

# The ordering space is an accreted flat integer, not a banded contract with reserved gaps

**Epic:** truthful-signals
**Branch prefix:** feature

> **Split into two plans (operator decision, reversing the original "no split").** This plan is now
> **Phase 1 — the space** only: the banded allocation contract with reserved gaps, the resolved
> same-phase collision, and the compose-time collision check (**D0–D3**). ⭐ **The reserved terminal slot
> this contract creates is filled by plan [`302`](../302-the-terminal-report-is-a-machine-readable-emission-the-inbox-drains.md)**,
> which owns **the emission and the payload** — the dedicated terminal step, its orchestrator-only
> composition, the report↔inbox delta, the machine-readable facts, and the drain-completeness check
> (former **D4–D8**). The two plans describe one seam; 302 serializes after this one, because its
> terminal step needs the slot this plan reserves.

## Problem

> **A plan reports its outcome to two audiences over two channels, at a time when neither channel can
> yet carry the truth, into an ordering space with no room to fix it.**

| End | Symptom |
|---|---|
| **What** | The inbox gets narrative; the operator report gets per-step outcomes, totals, repository state. **They are not the same facts.** |
| **When** | The landing is emitted at `order: 991` — **three steps and two producers before the run ends.** |
| **Where** | `998 → 999 → 1000` is contiguous. **There is no slot for a terminal step.** |

> **Scope after the split.** The Problem describes the whole seam; the two plans divide it. **This plan
> owns the "Where" row and § C** — the ordering space has no slot, collides, and has no contract.
> **Plan `302` owns the "What" and "When" rows and §§ A, B** — the channel gap and the non-terminal
> emission — plus § E. § D (ordering alone cannot fix it) is the shared bridge: this plan adds the
> "reads X"/"destroys X" ordering keys § D calls for; 302 applies them. The full seam is kept here so
> each plan reads against the same evidence.

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

The finalize ordering space has a **banded allocation contract with reserved gaps** — reserving an
integer terminal slot after the last reporting step and before `archive-plan`, and reserving ranges for
project-local and third-party steps versus the shared bundle — **and a collision check that fails** on
two same-phase steps sharing an order; the live same-phase collision is resolved; and the ordering key
can express **"reads X"** and **"destroys X"** as declared facts. ⭐ **The terminal emission that occupies
the reserved slot, and the machine-readable payload it carries, are plan `302`'s** — this plan builds the
space they need.

## Deliverables

⚠ **Four deliverables (D0–D3) — Phase 1 only.** ⭐ The original plan carried nine across three phases as
one landing, on the rationale that **splitting a seam is how this codebase produces half-fixes.** By
operator decision that "no split" was reversed and the seam was cut at its **safest joint**: the space
(this plan) is a genuinely separable foundation, while **the emission and its facts payload stay together
in plan `302`** — because a terminal step emitting prose at the right time, or facts at the wrong time,
is exactly the half-fix the original rationale warned against. The renumber-without-a-contract and
write-before-terminus risks it named are answered *within this plan* (D1's contract, D2/D3's collision
work); the "cannot carry facts produced after it" risk is answered *within 302* (its emission and
payload are one deliverable-set).

⛔ **INTERNAL ORDER IS LOAD-BEARING: D3 must FIRE on the live collision BEFORE D2 fixes it.**

### Phase 1 — the space

1. **D0 — GATE: derive the population and the semantics, in both directions.** Mutates nothing. Every
   order declaration — ⛔ **re-derive; any count in this file is today's answer, not an inheritance** —
   plus two questions the space's behaviour depends on: **is the space per-phase or global?** and **what
   is the tie-break for equal orders?**
   *Done when:* the population is derived and both semantics are answered **from the composer's source**.
   ⛔ **Read the composer — do not infer from output.**
   ⚠ Enumerate consumer repositories' declarations too; this tree is not the only one writing the key.
   ⛔ **Also confirm whether the plan's source identifier is available at COMPOSE time** — plan `302`'s
   orchestrator-only deliverable depends on it, and if it is only available at runtime, that deliverable's
   shape changes and observability gets *harder*. (Recorded here because D0 reads the composer anyway.)
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

### Phases 2 & 3 — the emission and the payload → split to plan `302`

The former D4–D8 (a dedicated terminal step in the slot D1 reserves; the step existing only under an
orchestrator; the report↔inbox delta; the machine-readable facts payload; and the drain-completeness
check) are now owned by
[`302-the-terminal-report-is-a-machine-readable-emission-the-inbox-drains.md`](../302-the-terminal-report-is-a-machine-readable-emission-the-inbox-drains.md).
⛔ **This plan does NOT build the terminal step or route facts** — it only **reserves the slot** (D1's
banded contract) and the declared-fact ordering keys ("reads X" / "destroys X") that 302 relies on. 302
serializes after this plan.

## Out of scope

- **The terminal emission and its machine-readable payload.** ⛔ **Plan `302` owns them** — the dedicated
  terminal step, its orchestrator-only composition, the report↔inbox delta, the facts routing, and the
  drain-completeness check. This plan builds only the space (the slot and the ordering keys) they need.
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
  project-local step skills under `.claude/skills/` — the population D1's contract renumbers into bands
  and D2 de-collides.
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py` — the
  default step list (`DEFAULT_PHASE_6_STEPS`, kept in lock-step with frontmatter order).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py` —
  the frontmatter-order resolver and ascending-order assertion (`_sort_steps_by_frontmatter_order`,
  `check_emitted_steps_ascending_order`).
- The **banded allocation contract** standards document (new), plus the extension-api documentation where
  `order` is described for third-party authors
  (`extension-api/standards/ext-point-finalize-step.md`) — extended with the reserved bands and the
  "reads X"/"destroys X" declared-fact keys.
- `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py` — the existing
  step-discovery test D3 extends with the collision check (⭐ **extend it, do not add a competing
  checker**).
- ⛔ **The emission/payload surfaces** — the orchestrator's detection/inbox-write verbs, `manage-status`'s
  typed facts map, the new terminal step document + dispatch table, the inbox envelope standard, and the
  orchestrator's analyze workflow — **belong to plan `302`, not here.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The order declarations, the saturated terminal region, and the same-phase collision | HYPOTHESIS | ⛔ **re-derive every one.** A first attempt at this asserted a free terminal slot from four steps it had read, and **a full sweep refuted it within the hour** ⇒ ⭐ **a list produced by looking is a SAMPLE, not an enumeration — knowing the archetype does not protect against it; only running the enumeration does** |
| The archive step runs last because it moves the plan directory out from under later readers | HYPOTHESIS | that step's own source — **reachable and cheap** |
| The space is per-phase | HYPOTHESIS | ⛔ **strongly suggested by one cross-phase duplicate pair, and stated NOWHERE.** If it is global, that pair **is** a collision and D2 grows |
| The composer's tie-break for equal orders | HYPOTHESIS | ⛔ **NOT ESTABLISHED — deliberately not claimed.** The colliding pair may be deterministic (discovery order, name) or not. ⚠ **Do not report "undefined order" as an impact until the composer is read** |
| Any consumer project pins an order D1 would break | HYPOTHESIS | ⛔ **NOT ESTABLISHED. Consumer repositories were not read** |

The emission/payload claims — the seven report-only findings, the cross-repository corroboration, the
compose-time orchestration signal, the typed facts map's both-direction guards, and the retrospective's
session rebind — moved to plan `302` with the deliverables that turn on them.

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D3 must be SEEN to fire on the live collision before D2 fixes it.** This is the one ordering
  constraint in the plan that cannot be recovered later: once D2 lands, the fixture is gone.
- ⛔ **D1's contract is text-whose-value-is-what-a-reader-does**, so it gets a **cold read**: give the
  Step 6 verification sub-agent the new contract with no other context and ask where a third-party step
  that must run after the merge but before the archive should be numbered. **If it cannot answer, the
  bands have no usable gaps** — which is the defect restated.
- ⛔ **The reserved terminal slot is D1's deliverable, not 302's.** Verify D1 leaves an integer slot free
  after the last reporting step and before `archive-plan` — plan 302's terminal step occupies it, so a
  band with no gap there blocks 302 before it starts.
- ⚠ **Cross-epic:** D1 must not contradict the post-run band contract (`code-intelligence-substrate`
  plan 050): a `post_run_review: true` step sits after the merge gate and declares `mutates_source:
  false`. **Cite that contract; do not restate or alter it.**
- Python, documentation, and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Split serialization:** plan `302` (the emission + payload) needs the terminal slot D1 reserves and
  the "reads X"/"destroys X" ordering keys D1 adds. **302 serializes after this plan.** D0 of 302 stops
  and reports blocked if this plan has not landed.
- ⚠ **Cross-epic: the post-run band contract is owned by `code-intelligence-substrate` plan 050**
  (landed as PR #1175) — whether a source-mutating step may be post-run: a `post_run_review: true` step
  sits **after** the merge gate (`default:branch-cleanup`, order 70) and MUST declare `mutates_source:
  false`; the two facts are mutually exclusive. ⛔ **The banded allocation contract must layer reserved
  gaps on top of this and CITE it — it must not restate or alter the P1/P2 discriminator or the
  mutual-exclusion rule.** The contract text lives in `source-edit-pushability.md` and
  `ext-point-finalize-step.md` § "Implementor Frontmatter".
- ⚠ **The terminal emission is a termination signal by construction** — that overlap with the sibling
  inbox-protocol work (amend/supersede, plan 250) is **plan 302's** concern, not this plan's.
- ⛔ **Do not go looking for the orchestrator spec, the archived plans, the run reports, the drained
  messages, or the other repository's report.** They live under `.plan/` or outside this repository, and
  are absent from this clone. Everything this plan needs is stated above; where the evidence is
  second-hand, this file says so.
