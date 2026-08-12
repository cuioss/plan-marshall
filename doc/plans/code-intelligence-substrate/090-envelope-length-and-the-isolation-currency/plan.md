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

# Cost is bytes × turns, and nothing owns the turn factor

**Epic:** code-intelligence-substrate
**Branch prefix:** chore

## Problem

A byte entering context is billed once at a creation multiplier and again, at a much smaller
multiplier, on **every subsequent turn it stays resident**. So the price of a byte is not its size:

```text
cost(byte) = creation_multiplier + read_multiplier × turns_remaining
```

Measured on one instrumented run, the average byte is re-read **dozens of times**, which makes the
average byte cost several times its nominal size — and a byte entering **early** in a long envelope
costs several times more again than one entering late.

⇒ ⭐⭐ **`turns_resident` is a first-class cost factor, it varies by more than 3× across envelopes,
and no plan in a long queue owns it.** Every other staged lever targets the byte *count*. This plan
targets the other factor.

This is a **decomposition, not a correlation**: average resident context per call is
`cache_read / tool_uses`, the phase row already carries the turn count, and their product **is** the
read cost. Both factors are separately attackable where the single number was not.

**The arithmetic that makes it a lever.** Splitting one long envelope into several short ones cuts
the multiplier on every byte that does not need to survive the whole run — on the measured run,
roughly a 3× reduction. The cost of doing so is re-creating the skill stack a few extra times, which
is on the order of tens of thousands of tokens against a phase costing tens of millions. ⇒ **The
isolation boundary is nearly free and is being under-used.**

## ⭐⭐ The second finding: the largest architectural bet is defended in the wrong currency

`doc/concepts/token-management.adoc` § 6 calls per-dispatch isolation *"the biggest single
token-management lever"* and defends it on the grounds that each dispatch's larger context is
independent **and never additive**.

Never additive **to the orchestrator**. Entirely additive **to the bill**. ⇒ **The document argues in
orchestrator-context-size while the measurement establishes that the cost driver is billing weight,
of which context is the overwhelming majority.** That is doc-contract-divergence on the system's
single largest architectural bet.

⭐ **The bet is almost certainly still correct — but for a reason § 6 does not state.** Isolation
does not make a byte cheaper; it **bounds how many turns a byte is re-read for.** That argument is
stronger *and* quantifiable. ⛔ **Do not weaken the isolation claim — restate it in the currency that
was measured.**

## Goal

Both cost factors — resident context and envelope length — are published per phase with their
populations; the isolation argument is stated in the currency that actually drives cost; one
concrete envelope-length lever has landed; and the one live anomaly in the creation/read ratio is
either explained by a mechanism that was **read**, or recorded as refuted.

## Deliverables

1. **D0 — GATE: is an instrumented population reachable in this clone?**
   The measurements this plan rests on come from archived run records under a **machine-local,
   git-ignored** path. ⛔ **Not present in this clone; do not search for it.**
   *Done when:* the run establishes either a reachable population or that none is reachable.
   ⛔ **If none is reachable: HALT D1, D3 and D4's selection, and report them blocked on corpus
   availability. D2 is still shippable** — it is a documentation correction whose evidence is the
   argument itself, not the corpus. Ship D2, report the rest blocked, do not fabricate a population.
2. **D1 — publish the two factors. Mutates nothing beyond the report.**
   Establish resident context and turns per phase and per envelope across the instrumented
   population, **with the population per phase**.
   ⛔ **Exclude or label every re-entered phase row** — a re-entered row blends cumulative and
   last-close fields and is arithmetically unsafe to quote as a rate. Use the published value-scope
   discriminators rather than hand-deriving which figures it mixes.
   ⛔ **Report the per-phase RANGE, never a single band** — this plan's own founding concern is a
   phase-specific figure read as a general one.
   *Done when:* both factors exist per phase with populations and ranges stated.
3. **D2 — restate `token-management.adoc` § 6 in the measured currency.**
   Per-dispatch isolation bounds turns-resident; that is the claim the data supports.
   ⛔ **Keep the isolation recommendation intact** — this corrects the *argument*, never the design.
   ⚠ Also check § 6's orchestrator-side and skill-body figures against D1 and either **re-derive or
   delete** them. A restated figure about a moving system is the archetype a sibling plan spent
   heavily learning to **delete rather than correct**.
   *Done when:* § 6's argument is in billing-weight terms, its recommendation is unchanged, and every
   surviving figure in it is either re-derived or removed — verified by cold read (see Verification).
4. **D3 — settle the creation/read inversion.** One phase spends the large majority of its billing
   weight on cache **creation** where others spend a small minority, at a read/creation ratio an
   order of magnitude apart. Something there repeatedly creates large prefixes that are read back
   only a handful of times.
   ⛔ **Read the mechanism — do not infer it from the ratio.** A timing or a ledger entry is a proxy:
   it is silent about which mechanism produced it. The tell is a causal verb with no implementation
   file read.
   *Done when:* the mechanism is named with the symbol that enacts it and its addressability stated,
   **or** it is recorded as refuted. ⛔ **Do not ship a remedy for a mechanism that was inferred.**
5. **D4 — one envelope-length lever, chosen by D1.** Land the single highest-value envelope split D1
   identifies.
   ⛔ **The split must preserve what is examined** — the same work in shorter-lived contexts, never
   less work.
   ⚠ **A dispatch boundary is not free of *quality* cost even when it is nearly free of *token*
   cost**: a leaf cannot see the previous leaf's reasoning. **State what each split envelope loses,
   and do not split across a boundary where continuity is load-bearing.**
   *Done when:* the split lands, its measured effect is reported with its population, and the
   continuity cost is stated rather than assumed absent.

Five deliverables with D0 a gate — under the split guard.

## Out of scope

- **Reducing what is examined.** ⛔ Excluded on principle: a shorter envelope must do the same work.
  The one measured intervention that improves the token number while degrading detection is
  examining less, and it is rejected on that ground rather than weighed.
- **Weakening per-dispatch isolation.** Excluded — D2 corrects the argument, never the design. A
  reader who comes away thinking isolation is in question has read it wrong, which is why D2 carries
  a cold read.
- **Reordering the dispatch prompt for cache-prefix sharing.** ⛔ **Excluded on measurement, and
  recorded so it is not re-proposed.** The prefix structure genuinely prevents cross-dispatch sharing
  past the system prompt, but it is worth a fraction of one percent of the bill: the overwhelming
  majority of creation is in-conversation growth, not prefix re-creation. ⭐ **A real structural
  defect can be quantitatively negligible — size a lever before staging it.**
- **Emitting the two factors** if a sibling plan has already landed that emission. Excluded to avoid
  a second writer; derive read-only instead and coordinate.

## Expected surface

- Archived run metrics records — read-only. ⛔ **Machine-local; see D0.**
- `doc/concepts/token-management.adoc` § 6 (and § 4's figures) — D2. **OBSERVED, git-reachable.**
- The phase whose envelope D1 selects — the execute phase's task loop and its packing, or a finalize
  step chain. **HYPOTHESIS**, verify at outline.
  ⚠ **The per-envelope packing budget is already operator-tunable** (see
  `doc/user/configuration.adoc`) — **check whether D4 is a config default rather than a code change**
  before scoping either.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/` — **only if** the sibling emission plan
  has not landed the two factors. Coordinate; do not add a second writer.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The cost model `creation + read × turns_remaining`, and the re-read multiple | **OBSERVED on one run** | ⛔ The record is machine-local and **not reachable from this clone** — do not look for it. The **model** is confirmable from the published billing multipliers; the **multiple** is what D1 re-derives. |
| The dispatch token order places the largest stable payload **behind** volatile per-dispatch fields, so cross-dispatch prefix sharing is impossible past the system prompt | **OBSERVED, and clone-reachable** | The execution-context agent contract under `marketplace/bundles/plan-marshall/skills/`. Read it. |
| Reordering that prefix is worth a fraction of a percent | **MEASURED and REJECTED** | Recorded so it is not re-staged. See Out of scope. |
| § 6 defends isolation in orchestrator-context terms while the driver is billing weight | **OBSERVED, clone-reachable** | `doc/concepts/token-management.adoc` § 6 — read the passage; the currency mismatch is in the text. |
| Shortening an envelope **reduces** total cost rather than relocating it | **HYPOTHESIS — and the failure mode is real** | ⚠ If a split envelope must re-read the same context to do its half of the work, the split converts cheap reads into expensive creation and **costs more**. **D1 must identify a split where the second half genuinely does not need the first half's residency** — that, not the arithmetic, is D4's real gate. |
| The creation/read inversion has a single nameable mechanism | **HYPOTHESIS** | D3 reads it or records it refuted. |
| Every figure quoted in this plan | **LEAD, not a fact** | Re-derive at the moment of the claim. |

## Verification

- **D2 is verified by cold read, and this is the deliverable where it matters most.** Its entire
  value is what a later reader concludes. Dispatch the pre-PR verification sub-agent to read the
  revised § 6 **cold** and report two things: which currency the argument is in, and whether
  isolation is being recommended or questioned. **If it reports the latter, the wording failed.**
- **D3 is verified by whether the mechanism was read.** The run report must name the implementing
  symbol. A causal claim with no implementation file behind it fails the deliverable however
  plausible it sounds.
- **D4 is verified by measurement plus a stated loss.** A split reported only as a token reduction,
  with no statement of what continuity it cost, has not met the deliverable.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Relationship to the other levers.** A sibling plan targets the cost of dispatches that produced
  nothing; this targets the cost of dispatches that ran too long. Different mechanisms; neither
  subsumes the other. ⚠ That sibling's own premise is under correction — read its plan before
  assuming any of its figures.
- **Ordering.** The WS-04 emission plan owns publishing these two factors and separating the
  `unattributed` populations; where a figure is load-bearing it should land first. If it has not,
  derive read-only and **do not add a writer**.
