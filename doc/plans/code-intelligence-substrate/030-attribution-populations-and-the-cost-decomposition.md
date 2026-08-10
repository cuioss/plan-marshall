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

# Two different quantities are both called "unattributed", and the cost has no published decomposition

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The metrics instrument publishes a reconciliation identity: the attributed `cache_read` components
sum exactly to `cache_read_input_tokens`, delta zero. The identity is real. It holds **because one
of its terms is a catch-all** — `cache_read_unattributed` absorbs whatever the other terms did not
claim, so the sum cannot fail to reconcile regardless of how little was actually attributed.

Two consequences follow, and both are defects in what the instrument *communicates* rather than in
its arithmetic.

**First, the instrument attributes usefully in one phase and reads as though it attributes in all
six.** In the phase it was built and tested against, the unattributed share is a minority; in the
other phases it is the large majority. That is this project's signature archetype — *verified on one
phase, generalised to six* — landing on the instrument itself.

**Second, the word "unattributed" names two different quantities that are not the same number.**
Unattributed **bytes** and unattributed **`cache_read`** are separately computed, have different
denominators, and differ by roughly a factor of three. A sibling plan's deliverable says "settle the
unattributed share" and names only one of them. Nothing in the emission or the rendering
distinguishes them, so a consumer cannot tell which it is holding.

Separately, the cost has an **actionable decomposition that nobody emits**. `cache_read / tool_uses`
is the average resident context per API call; the phase row already carries the turn count; their
product is the read cost. Both factors are derivable today and neither is published, so every
consumer sees one opaque number instead of the two levers inside it.

## Goal

Every emitted or rendered "unattributed" figure names **which** unattributed it is and carries its
own denominator; the two cost factors — resident context and turns — are published rather than left
derivable-in-principle; and the mechanism behind the attribution shortfall outside the
well-attributed phase is either fixed or **stated**, on evidence, as something that cannot be
attributed there.

## Deliverables

1. **D1 — GATE: name and separate the two unattributed populations.** Report unattributed *bytes*
   and unattributed *`cache_read`* as distinct, separately-named quantities with their own
   denominators, everywhere either is emitted or rendered.
   *Done when:* no emitted or rendered field is named merely `unattributed`; each carries its
   quantity and its denominator, and a test asserts a consumer can distinguish them.
   ⛔ **Until this lands, no consumer may quote "the unattributed share" without saying which one.**
2. **D2 — attribute `cache_read` outside the well-attributed phase, or state why it cannot be.**
   Establish the mechanism behind the large unattributed share in the other phases.
   ⛔ **Read the mechanism — do not infer it.** A timing, a comment, an ordering or a ledger entry
   is a *proxy*: it can be accurate and still support the wrong conclusion, because it is silent
   about which mechanism produced it. The operational tell is a causal verb with no implementation
   file read.
   ⭐ **"It cannot be attributed there, and here is why" is a valid and valuable outcome.** What is
   not valid is an identity that reconciles into a catch-all while reading as attribution.
   *Done when:* the mechanism is named with the implementing symbol that enacts it, and either the
   attribution improves or the limitation is documented at the emission contract.
   ⚠ **This deliverable needs a population of instrumented records — see D0-scope note below.**
3. **D3 — emit resident context and turns per phase, and settle the creation inversion.** Publish
   both cost factors rather than leaving them derivable-in-principle. One phase spends the large
   majority of its billing weight on cache **creation** where the others spend a small minority, at
   a read/creation ratio an order of magnitude apart — **mechanism unknown, and this is where it
   gets read.**
   *Done when:* both factors are persisted fields (not render-time computations), and the creation
   inversion has a named mechanism or an explicit "not established" with what was ruled out.
   ⛔ **One writer, and it is this plan.** A sibling WS-06 plan carries the same anomaly from the
   consuming side — it must not add a second emitter.
4. **D4 — every figure names its population, its phase, and its sampling point.**
   ⛔ **Adopt the vocabulary already shipped** for value scope, cumulative-versus-last-close fields,
   and denominator sampling points — do not introduce a parallel one.
   ⚠ A prior change **renamed** the partiality keys with **no dual-key shim**, so any read of an
   archived record must implement a three-state read (`current` / `old-schema` / `pre-migration`)
   and report `old-schema` **explicitly**. Silently defaulting an old-schema record is how a bare
   rename manufactures a clean verdict.
   *Done when:* a record in each of the three states is read and reported as that state, asserted by
   test.

Four deliverables with D1 a gate — below the split guard.

**Scope note on the measurement corpus (applies to D2, and to D3's inversion mechanism).** The
originating figures were computed from archived plan records under a **machine-local, git-ignored**
path that is **not present in this clone**. ⛔ **Do not search for it.** Before scoping D2, establish
from git-reachable evidence whether any population of instrumented records is available here. **If
none is: do D1, D3's emission, and D4 — which are all code changes in this clone — and report D2 as
blocked on corpus availability rather than inferring a mechanism from the source alone.** Do not
substitute a hand-assembled corpus.

## Out of scope

- **The retrospective render path.** Excluded because a separate staged plan owns it; overlapping
  would put two plans in one file. Touch it only where a figure is *rendered without being
  persisted*, which is this plan's subject.
- **The ledger-disagreement question** (which of several token totals is "actual"). Excluded because
  another staged plan owns it, and merging the two would produce a plan large enough to need
  splitting immediately.
- **Re-deriving the per-phase cost *ranking*.** Excluded because that ranking is retired on
  independent grounds — several mechanisms disagree on the direction of its error — and re-deriving
  it here would launder a suspect figure into a corrected one. This plan publishes **factors**, not
  a ranking.
- **Any bias correction applied to a figure whose error direction varies.** Excluded for the same
  reason: correcting an error whose sign is not established manufactures confidence.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-metrics/` — the emission and its
  `standards/data-format.md` contract. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/` — **only** where a figure is
  rendered without being persisted. **HYPOTHESIS**; coordinate, do not overlap.
- `.claude/skills/audit-archived-plan-retrospectives/` — its billing-composition check.
  **HYPOTHESIS**, verify at outline.
- `test/plan-marshall/manage-metrics/` — tests for the three-state read and the separated
  populations.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The reconciliation identity holds because one term is a catch-all | **OBSERVED in the source** | Read the emission in `marketplace/bundles/plan-marshall/skills/manage-metrics/` — the catch-all's computation is in the clone and settles this without any archived record. |
| The unattributed share is large outside one phase, and that generalises beyond a single plan | **HYPOTHESIS** | Requires a population of instrumented records. ⚠ **The originating observation is n=1**, and the phase with the most extreme share is one that was re-entered during its run, so **do not rest the mechanism on that row alone.** |
| Unattributed *bytes* and unattributed *`cache_read`* are two different quantities | **OBSERVED in the source** | Both computations are in the clone. This is the one claim that needs no corpus — read both and confirm the denominators differ. |
| One phase's cache-**creation** inversion has a single nameable mechanism | **HYPOTHESIS** | Unverified. D3 reads it or reports it unestablished. |
| Context is ~99% of billing weight (composition, not ranking) | **OBSERVED, third independent confirmation** | Composition only. ⚠ The per-phase **ranking** stays retired; do not revive it from this row. |
| The originating per-phase figures | **NOT REACHABLE FROM THIS CLONE** | Machine-local archived-plan records under the git-ignored `.plan/` tree. ⛔ **Do not go looking for them.** They are stated here as motivation; the scope note above says what to do in their absence. |
| A prior change renamed the partiality keys with no dual-key shim | **HYPOTHESIS** | Verify against the current emission contract in the clone before implementing the three-state read — if a shim was added since, D4 changes shape. |

An asserted **absence** ("nothing publishes these two factors today") is verified exactly as an
asserted presence: confirm it against the emission source before building, because an unverified
absence produces a second emitter beside one that already exists.

## Verification

- **D1 is verified by a consumer test, not by inspection**: a caller holding both figures must be
  unable to confuse them — assert on the field names and denominators, not on their values.
- **D4's three-state read is verified with one record per state**, including a deliberately
  old-schema record asserted to be **reported as old-schema** rather than defaulted. A test that
  only exercises `current` passes against the exact defect this deliverable exists to prevent.
- **D2's outcome is verified by whether the mechanism was read.** The run report must name the
  implementing symbol it read. A causal claim with no implementation file behind it fails this
  deliverable even if it sounds right.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why this is worth a plan rather than a field rename.** The identity is the instrument's only
  published correctness claim, and it is structurally incapable of failing. That makes it a
  confident signal with a hidden caveat — the exact shape this project keeps finding, here on its
  own measuring device.
- **Sequencing.** Two WS-06 plans read these fields to size themselves; where a figure is
  load-bearing, this landing first makes them cheaper. Neither is hard-blocked — each can derive
  read-only — but **neither may add a second writer** if this has not landed.
- **Adjacency.** A sibling plan consumes the *byte* split; this one separates the two populations
  that split is stated in. ⛔ That plan's deliverable covers the **byte half only** — do not read it
  as covering `cache_read`.
