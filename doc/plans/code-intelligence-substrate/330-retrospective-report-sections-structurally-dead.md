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

# The written / omitted / dropped partition holds the wrong thing in every bucket

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The retrospective report declares a section registry shared by its fragment producer and its report
compiler, and partitions the outcome three ways: **written**, **omitted** (benign — nothing to say),
**dropped** (a real loss).

⛔ **The probe is miscalibrated in BOTH directions at once.** On one run:

- **written** included a headline section whose entire body was a placeholder;
- **dropped** listed a section carrying genuine content loss **and** a harmless zero-result aspect
  whose fragment explicitly declared itself skipped.

⇒ ⭐ **The one signal that fired loudly was the only one with nothing behind it, while an entirely
empty headline section passed as clean.** **A three-valued outcome in which every bucket holds the
wrong thing is worse than a two-valued one, because it reads as precision.**

## ⛔⛔ HALF THIS PLAN HAS ALREADY SHIPPED — the scope below reflects a re-grounding

The originating spec was authored against a tree that has since moved, and a first-party re-check
found:

- **The "cannot be registered at all" premise is REFUTED** — the compiler accepts the fragment and
  uses it verbatim. ⭐ **What survives is sharper**: the compiler falls back to a literal placeholder
  **and appends the heading to `written` unconditionally.** ⇒ The deliverable is **not** "make it
  registerable"; it is **"stop counting a placeholder as written"** — the partition invariant violated
  by the compiler itself.
- **The render path for the lost section is DONE**; only its registration in the skill documentation
  is still open.
- **The skipped-fragment fix is SHIPPED**, and went further than asked — it matches falseness by
  identity so a numeric zero payload is not misclassified. ⛔ **Drop it.**
- **The three-way partition mechanism is implemented; the invariant ASSERTION is not** — and the
  placeholder above is a **live violation of it.**

⇒ ⭐ **The split-guard breach resolved by arithmetic rather than by a split.** ⛔ **Do not scope from
any older deliverable list.**

⭐ **The systemic finding is not about this plan**: a staged spec **decays against a moving tree** and
nothing re-grounds it, so **a spec's age is a silent correctness risk.**

## Goal

The partition means what it says: *written* implies non-empty, *omitted* means the producer had
nothing to say, *dropped* means real content was lost — and every registry row is either reachable or
removed.

## Deliverables

1. **D1 — assert the partition invariant, with the placeholder as its failing case.**
   *Written implies non-empty.* A partition is only useful under that invariant; **pin it with a test
   rather than a convention**, and fix the unconditional append that violates it today.
   ⭐ **Extend the invariant to a property that closes a related class: a section that reports zero
   must be able to name what it checked.** Every *"zero findings"* line carries the ambiguity this
   epic exists to kill — **looked and found nothing** versus **could not look** — and recording the
   signals that were checked and **held** is the discriminator. ⭐ **The counterexample set is evidence
   too.**
   *Done when:* an empty-bodied section is not listed as written, and a zero-reporting section names
   its checked set.
2. **D2 — GATE: derive the population of registry rows against their reachability. Mutates nothing.**
   ⚠ **Two dead rows were found by one run — that is a SAMPLE.** Check **every** row for (a)
   registerability and (b) a live render path, and **report the dead count separately from the number
   examined.**
   *Done when:* every row carries a reachability verdict and both counts are published.
3. **D3 — the documentation that instructs a registration supplies the exact argument.**
   The skill's aspect table names aspects in **prose**, while the registration verb validates against
   a **closed registry** — and the canonical keys appear nowhere in that document, so registrations
   are rejected on first attempt.
   Add the canonical key to each row.
   ⛔ **Derive the key from the registry, never restate it** — a hand-copied key in a table is this
   epic's count-prose archetype wearing a different hat, and the standing remedy for a restated claim
   is **to point at the declaring source rather than to copy it correctly.**
   *Done when:* each row carries its canonical key, derived rather than transcribed.
4. **D4 — the retrospective stops destroying its own primary input.**
   The capture **overwrote the measured plan's session identity with the observing process's own** —
   caught by hand; left alone it would have corrupted the metrics for the plan being measured.
   ⛔ **The near-miss is the finding, not the outcome**: nothing in the pipeline would have reported
   it, and **the corrupted value is well-formed**, so no downstream consumer would reject it.
   ⭐ **The root cause, and why the naive fix is wrong**: a plan can legitimately span **multiple
   sessions**, so the field is **a scalar modelling a list** — which is *why* a second writer
   overwrites rather than appends.
   ⇒ **Record the identity as a LIST.** ⭐ **This subsumes the clobber fix rather than sitting beside
   it**: with a list there is no single slot to clobber, and the observer's own identity becomes an
   **append**, which is what it was always trying to express.
   ⛔ **Do not ship a guard without the list** — an assertion that the scalar is unchanged would make a
   legitimate multi-session resume fail.
   *Done when:* the identity is a list, the observer appends, and a multi-session run is representable.
5. **D5 — tests, RE-BASELINED.**
   ⛔ Two previously-planned assertions now **PASS against current code** and can no longer be
   *verified to fail pre-fix*. **Do not ship them as regression proofs** — either drop them or restate
   them as characterization tests pinning shipped behaviour, **and say which.**
   The empty-section assertion still fails today and remains a genuine regression test.

Five deliverables with D2 a gate — comfortably under the split guard after the re-grounding.
⚠ **If D2 finds a materially larger dead population, split the sweep out and re-stage** rather than
growing this plan.

## Out of scope

- **Making the skipped-fragment case an omission rather than a drop.** ⛔ **Already shipped** — verified
  first-party. Do not re-scope it.
- **Making the headline section registerable.** ⛔ **Premise refuted** — it already is. The surviving
  defect is the unconditional write-count, which is D1.
- **The producerless per-dispatch context-load columns.** Excluded — another epic **keeps** that half
  by explicit agreement, and it is recorded on both sides. ⛔ Do not re-file it.
- **Fixing the finalize step ordering.** Excluded — a sibling plan and another epic own it. ⛔⛔ **But
  read the sequencing warning below: this plan can be fully correct and still render a destroyed
  input.**

## Expected surface

- The section registry and its key-validation helper. **OBSERVED.**
- The report compiler — its payload predicate and the written/omitted/dropped partition. **OBSERVED.**
- The fragment collector — its add, init and finalize verbs. **OBSERVED.**
- The skill's aspect table and the report-structure document's conditional rule. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The compiler falls back to a placeholder and appends the heading to the written list **unconditionally** | **OBSERVED, re-verified first-party** | The compiler's fallback and its append. ⛔ **Read both — this is D1's failing case.** |
| The three-way partition mechanism is implemented but its invariant is not asserted | **OBSERVED, re-verified** | The partition code and the absence of a test over it. |
| The canonical registry keys appear nowhere in the skill's aspect table | **OBSERVED, corroborated by search** | ⛔ **An asserted ABSENCE — re-derive it**, since it is the whole of D3. |
| The capture overwrote the measured plan's session identity | **OBSERVED, first-party, two consecutive sightings** | ⛔ The run records are machine-local and **not reachable from this clone — do not look for them.** ⭐ **Settle it from the capture's write target in the clone** — if it writes to the measured plan's metadata, the defect is structural. |
| A plan can legitimately span multiple sessions | **OBSERVED** | ⭐ **This is why the naive guard is wrong.** Confirm from the resume path. |
| No orchestrator injection path exists for the headline section | **REFUTED** | Recorded so it is not re-derived. ⚠ The original spec called this an asserted absence and it **was wrong** — a live instance of why an absence needs verifying like a presence. |
| The dead-row count and the payload sizes | **LEADS** | ⛔ **Re-derive from the registry** rather than quoting. |
| The finalize step ordering | **HYPOTHESIS** | ⛔ **Read it from the run's own manifest or step log — NEVER from the ordering values on post-merge main**, which record what a plan **installed** rather than what it **ran**. |

## Verification

- **D1's invariant is verified against the known failing case**: a section whose body is only a
  placeholder must not appear as written. That assertion fails today.
- **D2 publishes two numbers** — dead rows and rows examined. One number is not a coverage claim.
- **D5's re-baselining is explicit**: each retained test is labelled regression or characterization.
  ⛔ Shipping a passing test as a regression proof misrepresents what was verified.
- **D4 is verified with a multi-session case**: the observer's identity appends, the measured plan's
  identities survive, and a resume does not fail.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- ⭐ **The retrospective component is itself an instance of the archetype it exists to detect.** That
  is why this plan is scoped at the **partition contract** rather than at the individual dead rows: a
  reporting surface that cannot represent *empty* correctly will keep generating them.
- ⛔⛔ **Sequencing warning — this plan can be fully correct and still read a destroyed input.** The
  retrospective runs after a step that destroys its footprint input and before the step that makes the
  plan's own fixes live. **If this plan fixes the report while that ordering stands, the fixed sections
  will faithfully render a destroyed input — strictly worse than an empty section, because it looks
  authoritative.** Coordinate before starting; do not treat it as a finalize-time discovery.
- **Serialization.** Several sibling plans edit the same bundle — sequence, never run concurrently.
