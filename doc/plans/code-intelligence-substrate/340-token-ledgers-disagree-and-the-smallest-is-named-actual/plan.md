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

# Three token ledgers describe one run, disagree row by row, and the smallest is named "actual"

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

One plan run produces **three independent token ledgers**. No two agree, and **none is a subset of
another** — each covers a different set of phases and a different set of steps. In one measured
window, two ledgers recorded overlapping-but-different dispatch sets, with values appearing in one and
not the other in **both** directions.

⭐ **The sharpest consequence**: a step that ran four times appears twice in one ledger and three times
in another. **Only the union shows all four — and nothing tells a reader to take the union.**

**The live defect.** One ledger's sum is emitted under the field name **`actual_tokens`**, compared
against a **whole-plan** cost prediction, and fed into a recalibration loop.

⛔ **Latent, not dormant.** On the observed run the prediction was absent, so nothing recalibrated.
**Any run that does carry a prediction gets its cost model recalibrated against roughly half its real
spend, under a field name claiming to be the actual.** ⭐ A partial actual compared against a total
prediction produces **plausible** numbers — which is exactly why it would not look wrong.

## ⭐⭐ A second, larger disagreement: the report and the STORE disagree about what exists

Three things a rendered report shows are **not in the machine-readable store at all**:

1. ⛔⛔ **The headline Total row is RENDER-TIME ONLY** — the store's header carries no aggregate. ⇒ The
   figure a human quotes, **and its population qualifier**, exist **only in prose**. A script must
   re-sum and **re-derive the population itself**, and may legitimately pick a different one than the
   renderer did. ⭐ **Two producers of one number, with one of them unpersisted.**
2. ⛔ **An inline-cost field is SPARSELY persisted**, so a large cost gap visible in the report is
   **not reconstructible from the store.**
3. ⛔ **The disambiguating caveats are render-only** — the exclusions, the comparator's reasoning, the
   scope of a timestamp. These carry **the semantics that make the numbers safe to use**, and a script
   reading the store gets the values without them.

⇒ ⭐⭐ **This is the plan's own subject one level up**: it was staged because *ledgers disagree and the
smallest is named actual*; here **the report and the store disagree about what exists at all** — and
the report wins, because it is what anyone reads.

**And a completeness verdict compounds it.** A phase's *recorded* status is keyed **solely off its
end timestamp**. A phase that dispatched many times and recorded every one is still "unrecorded" if
its terminal close never fired — ⛔ **and that close is the last thing the final phase does, so it is
simultaneously the phase most likely to be missing it and the phase most likely to hold the largest
figure.** In one case the boundary file for that phase held **more than the entire published total**.

⚠ **That last one is a USEFULNESS bug, not a truthfulness one** — the partiality marker is honest. But
every downstream consumer reads the total as a figure rather than a floor. ⛔ **A partiality marker
that is technically correct and practically ignored is how a multi-million-token phase disappears from
a cost review.**

## Goal

**A token figure carries its population or it is not named "actual."** The renderer derives its output
from the store rather than computing figures nobody can check, and a cross-ledger disagreement
produces a finding instead of a silent choice.

## Deliverables

1. **D1 — HARD GATE: re-derive the three totals and the row-level intersection. Mutates nothing.**
   ⛔ **The forwarding epic explicitly did NOT verify these numbers** — they are the originating run's
   first-party report of its own artifacts, **two hops from the observation with zero verifications.**
   ⚠ **Re-derive the repeated-step counts too** — a stated count is a sample, and this epic has shipped
   that error itself.
   ⛔ **No other deliverable may be scoped until this is done.** If the ledgers turn out to agree, or
   to be subsets after all, **everything downstream changes shape and the plan is re-scoped rather
   than continued.**
   ⚠ **Corpus reachability**: the three ledger files live under a **machine-local, git-ignored** path
   **not present in this clone** ⛔ **— do not search for it.** If unreachable, **derive what the clone
   can support** — the ledgers' *writers*, which establish whether the populations can differ by
   construction — and **report the arithmetic re-derivation blocked.** ⭐ The writer-side derivation is
   often decisive on its own: if two writers cover different phase sets, disagreement is structural.
2. **D2 — the "actual" figure stops being a partial.** Either rename it to name its population, or
   widen the sum to the union.
   ⛔ **Whichever is chosen, the comparison against a whole-plan prediction must be
   population-matched — the unmatched comparison IS the defect, not the field name.**
   *Done when:* a population-mismatched comparison is refused or annotated, asserted by test.
3. **D3 — every token figure carries its population, and the renderer persists what it renders.**
   ⭐ **The shape already exists in-tree** — one report prints a population marker beside its totals.
   **This is a copy, not a design.**
   Persist the aggregate **with its population count as a field**, the inline-cost field for every
   phase (**or an explicit not-measured marker — never absence**), and the comparator and exclusion
   semantics **as data rather than prose**.
   ⛔ **The renderer must derive 100% of its output from the store — any figure it computes and does
   not persist is a number nobody can check.** ⚠ **Do not solve this by parsing the rendered report**;
   the markdown is the artifact, not the source.
   ⛔ **This plan is a CONSUMER of the population vocabulary, not its author** — another epic owns
   *which* population a total names, as a field rather than a sentence. **If this plan finds itself
   defining permitted population values, it has taken the wrong half.**
   *Done when:* no rendered figure lacks a persisted counterpart.
4. **D4 — a deterministic cross-ledger reconciliation**, joining the sources on phase, step and
   timestamp window, emitting one finding per row present in one ledger and absent from another.
   ⭐ **Pure arithmetic, no judgement — so this is a SCRIPT, not a dispatched check.** Build it as one.
   ⛔ **It must handle BOTH shapes**: a phase whose row was **never closed**, and a phase that closed
   and was **re-entered**. The partiality labelling must say *"boundary never closed"* distinctly from
   *"row absent"*.
   *Done when:* a disagreeing pair produces a per-row finding, and both shapes are represented in
   tests.
5. **D5 — fold a recorded-but-unclosed phase's boundary sum into its cell, LABELLED.**
   When a phase has no end timestamp but **does** have a dispatch-boundary file, fold that file's row
   sum in as a **labelled** figure — the same default-plus-exception labelling discipline already used
   elsewhere in the same skill.
   ⛔ **Keep the partiality verdict for duration**, which the boundary file cannot supply honestly.
   ⭐ **Precedent in the same skill**: an existing path already folds inline cost into a zero-dispatch
   phase's total and labels the row's population. **Same move, same reason, applied to the dispatched
   population.**
6. **D6 — two derived figures whose names assert the wrong population.**
   - A per-task duration derived from **wall-clock**, so it grades **operator idle time as agent
     cost**. ⛔ **Do NOT fix by clamping or by heuristically excluding long gaps** — the worked figure
     is already recorded per phase; **the ratio simply needs to read it.** ⭐ The worked-duration fix
     **also resolves the unclosed-boundary case**, because the per-dispatch duration accumulates
     without depending on the phase boundary closing.
   - A persistence loop that **hardcodes** its usage-field list instead of deriving it from the
     canonical label set. ⭐ **A hardcoded field list cannot drift visibly** — it silently omits any
     field added to the canonical set, **and the omission reads as a zero rather than as an absence.**
   ⛔ **Do not merge the second with a superficially similar item another epic owns** — theirs is
   *producers never populate the columns*; this is *the persister does not derive its field list*.
   Different fixes; a merged item would ship one and claim both.
7. **D7 — tests, each verified to FAIL pre-fix.**
   (a) disagreeing ledgers produce a reconciliation finding per divergent row;
   (b) a population-mismatched comparison is refused or annotated;
   (c) a total rendered without a population marker fails the assertion.

Seven deliverables with D1 a hard gate — **past the split guard.** ⚠ **Evaluate the split at outline
and record the verdict**; the natural cut is (D1+D2+D4: reconciliation) and (D3+D5+D6: persistence and
labelling).

## Out of scope

- **The structurally-empty per-dispatch context-load columns.** ⛔ Excluded — another epic **keeps**
  that item by explicit agreement recorded on both sides. **Do not scope it here.**
- **Defining the population vocabulary.** ⛔ Excluded — another epic's plan supplies it and lands
  first; this plan **writes into it**. ⚠ The one event that reopens the question is that plan changing
  shape so it no longer supplies a vocabulary.
- **The render-path recovery of a lost report section.** Excluded — a sibling plan owns it, and the
  split is recorded on both sides.
- **Per-call cost truncation at the runtime and hook layer.** Excluded — the closest neighbour plan
  owns it. ⛔ **They are NOT the same plan**: that one owns per-call truncation, this owns cross-ledger
  reconciliation at the metrics layer. **Do not merge; do re-check for surface overlap.**

## Expected surface

- The retrospective's routing-decisions check and its cost-preview evaluation. **HYPOTHESIS**, verify
  at outline.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/` — the store writer, the renderer, the
  enrichment persistence loop, and the canonical usage-label set. **HYPOTHESIS**, verify at outline.
- The execution-log and per-phase dispatch-boundary writers. **HYPOTHESIS**; locate before scoping.
- The per-task duration derivation site. **HYPOTHESIS.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The three totals, the row-level intersection, and the repeated-step counts | **HYPOTHESIS — two hops from the observation, ZERO verifications** | ⛔ **D1.** The forwarding epic explicitly did not verify them. **Treat every number as a lead.** |
| The cost-preview evaluation sums one ledger and emits it as the actual | **HYPOTHESIS — LOAD-BEARING** | The symbol itself. **It is the whole of D2.** |
| The prediction was absent on the observed run, making the defect latent | **HYPOTHESIS** | ⚠ **If a prior run DID carry a prediction, the recalibration table may already be corrupted and D1 grows a blast-radius arm.** |
| A population marker already exists in one rendered report | **OBSERVED in-tree** | ⭐ D3's precedent. ⚠ **Re-confirm the exact form before copying it.** |
| The aggregate and its qualifier are render-time only; an inline field is sparsely persisted; the caveats are render-only | **OBSERVED, probed first-party** | ⛔ Confirm from the **store writer** in the clone — if it emits no aggregate, the claim is settled without any archived record. |
| A completeness verdict keys a phase's recorded status solely off its end timestamp | **OBSERVED** | The verdict's predicate. |
| A per-task duration is wall-clock derived, and one recorded instance was composed almost entirely of an overnight gap | **OBSERVED, sixth consecutive sighting, first-party on this epic's own plan** | The derivation site. ⛔ **Directly load-bearing: a wall-clock-derived cost figure is exactly the kind that gets cited as a token-reduction result**, so any efficiency claim resting on it is population-mismatched at the source. |
| The persistence loop hardcodes its field list | **HYPOTHESIS** | The loop against the canonical label set. |
| Any figure quoted in this plan | **LEAD** | ⛔ Each carries its own unpublished population. **Do not cite any as a measured result without re-deriving.** |
| The partiality keys were renamed with no dual-key shim | **HYPOTHESIS** | ⛔ Archived records still carry the old keys, so any read needs a **three-state read** (`current` / `old-schema` / `pre-migration`) with `old-schema` **reported explicitly**. |

## Verification

- **D1's outcome governs everything.** A run that re-derives and finds agreement should **re-scope and
  say so** — that is a success. A run that proceeds on unverified numbers has failed the gate whatever
  else it ships.
- **D3 is verified by a round-trip**: every figure in the rendered output must be locatable in the
  store. ⛔ A figure present only in the render fails the deliverable.
- **D4 is verified against both shapes** — never-closed and closed-then-re-entered — with the labels
  asserted distinct.
- **D6's duration fix is verified against a case containing a long idle gap**: the reported figure must
  reflect worked time, and ⛔ **must not be achieved by clamping.**
- Full `./pw verify` per the lane contract's build gate.

## Notes

- ⭐ **The keeper rule, and the plan's success criterion**: ***a token figure must carry its population
  or it must not be named "actual."*** This is the measurement half of the epic's thesis in its most
  literal form — three ledgers, one run, and the reader is given the smallest without being told it is
  partial.
- **Ordering.** The vocabulary-supplying plan in another epic lands **first**; this plan consumes it.
  ⛔ **Neither epic invents a second population enum.**
- **Serialization.** Several sibling plans edit the same bundle — sequence, never run concurrently.
