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

# A health verdict that strengthens as the signal it measures degrades

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The chat-signal reducer decides between *feed the reduced transcript to the model* and *refuse it as
too large* from a single flag computed as **"did the reduction keep zero turns?"** The verdict is a
**pure count of survivors** and carries no notion of what the survivors *are*.

Its provenance filter drops only **two** synthetic classes — blank turns, and one specific
skill-load injection shape recognised by a single literal marker. **Every other harness-authored turn
survives and counts as operator signal.**

⛔ **So the failure compounds rather than merely being incomplete.** Each additional class of injected
instruction text raises the survivor count, which drives the verdict further from *no signal*, which
reports **more** health. **Signal quality and the reported verdict move in opposite directions.**

**And the code asserts the property it does not provide.** An inline comment states the surviving set
is operator-authored *"by construction"*, and that claim is the stated justification for the verdict.
It is false: harness-authored turns carrying neither an empty body nor the one recognised marker pass
the filter unchanged.

**This is a recurrence of the defect the same file documents as fixed.** The original incident was a
transcript dominated by framework boilerplate being confidently classified as usable. The fix
enumerated **two** synthetic classes. ⛔ **The failure mode was never the two classes — it was
enumerating at all, against a harness that adds injection shapes over time.**

## ⭐⭐ The filter is wrong in BOTH directions at once

Measured retention ratios from real runs cluster around **a fraction of one percent retained**, every
one reported as a clean verdict. But the decisive observation is qualitative:

- **It discards the decisions.** In one enumerated case **zero** operator-authored turns survived —
  all survivors were harness boilerplate — while the run's most consequential operator input (a
  review escalation that created new tasks) was **absent entirely**. A retention that happened to
  keep the operator's dispositions would be defensible; one that discards exactly the turns carrying
  operator intent is **measuring the wrong thing** and reporting a clean verdict over it.
- **It admits the noise.** Harness task-notifications are counted as operator signal.

⇒ **The retained remainder is not "a small sample of operator signal" — it is a small sample
contaminated with non-signal.** Widening the filter alone would admit more noise.

**A whole channel is invisible.** On a gated run the operator's decisions arrive as **tool results,
not user turns**, so a reducer that keeps only free-form turns measures **only the channel the
operator did not use**. A run with zero free-form corrections and many gate decisions is
*well-instrumented*, and the instrument should be able to say so.

## Goal

The verdict reflects **operator-authored signal** rather than surviving volume: the filter identifies
provenance positively, the aspect can state what it retained and what it discarded **by provenance
class**, and a reduction that dropped every operator-decision turn cannot render as clean.

## Deliverables

1. **D1 — GATE: enumerate what actually survives, by provenance. Mutates nothing.**
   Run the reducer over real transcripts and classify the surviving turns.
   ⭐⭐ **The design question is ALREADY ANSWERED by evidence — invert to a positive predicate.** Record
   that as settled and **spend the budget on the marker inventory, not on re-litigating the choice**:
   - a **negation list** derived from a sample will always be incomplete, and it **fails toward
     "operator"** — the direction that manufactures the false clean verdict;
   - a **positive predicate fails toward "synthetic"** when the harness adds a new wrapper.
   Derive synthetic-ness from the harness's **own injection markers** — any turn wholly enclosed in a
   harness tag block, or a verbatim re-entry notice — and keep what is left.
   *Done when:* the marker inventory is derived from real transcripts and published, with the
   allow-list decision recorded rather than re-argued.
2. **D2 — the provenance filter matches the positive-predicate shape.**
   ⛔ **Correct the "by construction" claim in lock-step** — either make it true or stop asserting it.
   **Leaving an over-claiming comment beside a corrected filter is the exact pattern this project
   keeps finding.**
   *Done when:* the filter identifies provenance positively and the comment matches the code.
3. **D3 — the verdict stops being purely volume-derived.**
   At minimum the output gains an **operator-authored count distinct from the raw survivor count**, so
   a caller can tell *"kept 200 turns, 3 operator-authored"* from *"kept 200 operator turns"*.
   ⭐ **Retain gate-style operator decisions as a distinct signal class** and report **two counters** —
   free-form corrections and gate decisions — so the invisible channel becomes visible.
   *Done when:* the two states are distinguishable in the output. Whether the routing threshold also
   changes is D1's call, since raising the bar trades a false-healthy for a false-refusal.
4. **D4 — tests.**
   (a) A fixture composed of harness-injected turns **using the real block shapes, not invented ones**
   is verified to be classified healthy **by the current code** and correctly by the fixed code — the
   assertion that fails today.
   (b) A genuine operator-authored transcript still routes normally — **the mirror false-positive
   guard**: this fix must not make the reducer refuse real transcripts.
   (c) The new counters distinguish high-volume-low-signal from high-volume-high-signal.
   ⭐ **The cheap discriminating regression**: a transcript with very low retention and **zero** turns
   passing the positive predicate MUST report *no signal*. That single assertion fails against today's
   implementation and passes against the allow-list.

Four deliverables with D1 a gate — under the split guard.

## Out of scope

- **The footprint/coverage-recall defect.** ⛔ **Struck — a sibling plan owns it entirely**, supported
  by several independently-measured true values and a settled remedy. Carrying it here too would
  produce two writers for one fix.
- **A token-total mislabelling in a routing checker.** Excluded — cross-noted to the ledger-disagreement
  plan, not folded, to avoid a third writer.
- **A structurally-unfillable report section landing in the benign bucket.** Excluded — same remedy
  *shape* (declare inapplicability rather than emit a number), different surface. ⛔ Do not
  re-litigate the existing partition; if it is picked up at all it needs its own third state.
- **Changing the routing threshold** unless D1 decides to. Excluded by default because raising the bar
  trades one false verdict for another, and that trade needs evidence.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py` — the
  signal-bearing predicate, the synthetic-load detector and its marker constant, the verdict
  computation, the output payload, and the docstring claim. **OBSERVED.**
- `.../plan-retrospective/references/chat-history-analysis.md` — the aspect contract; update in
  lock-step if the vocabulary changes. **HYPOTHESIS**, verify at outline.
- The skill's own description of the two routing tiers, if D3 changes the threshold. **HYPOTHESIS.**
- `test/plan-marshall/plan-retrospective/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The verdict is a pure survivor count; the filter drops only a blank-turn class and one marker-matched injection shape; the docstring asserts "by construction" | **OBSERVED, verified first-party at HEAD** | The reducer script in the clone. ⭐ **The three sites were confirmed still correct at a recent re-check — spend the budget on the marker inventory, not on re-locating the code.** ⚠ Line numbers still move; find them by symbol. |
| Retention ratios of well under one percent were reported as clean verdicts across several runs | **OBSERVED, six measured instances** | ⛔ The run records are machine-local and **not reachable from this clone — do not look for them.** ⭐ **Reproduce instead**: run the reducer over any available transcript in the clone and classify the survivors. **D1 is that reproduction.** |
| In one enumerated case **zero** operator-authored turns survived, and the run's most consequential operator input was absent | **OBSERVED, turn-by-turn** | Same reachability caveat. This is the qualitative claim that matters and D1 re-establishes it. |
| Operator decisions on a gated run arrive as tool results, not user turns, so the reducer cannot see that channel at all | **OBSERVED** | Confirmable from the reducer's own role filter — read it. |
| Harness task-notifications are counted as operator signal | **OBSERVED** | Same — the predicate admits them. |
| The misclassification still occurs and still feeds the self-reported ratio | **HYPOTHESIS** | The turn-classification predicate plus the site computing the reported reduction. |

⛔ **A validation trap this plan must not fall into.** The reduction ratio is currently the
instrument's own evidence of working. **If document bodies are being counted as user turns, a HIGHER
reduction ratio can indicate a WORSE misclassification** — the metric moves the wrong way under the
defect. ⇒ **Do NOT validate the fix by the ratio improving.** Validate against the classification of a
known population of turns; the ratio is an **output of the defect, not a check on it.** ⭐ The
empty-turn half compounds this: an empty turn and a misclassified document body inflate the same
numerator, so the two cannot be told apart by the ratio either.

## Verification

- **Validate by classification, never by ratio** — see the trap above. This is the single most
  important verification instruction in this plan.
- **The discriminating regression must fail pre-fix.** Record that failure.
- **The mirror guard is mandatory**: a genuine operator transcript must still route normally.
  A precision fix that starts refusing real transcripts has traded one false verdict for another.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why this one matters disproportionately.** The chat aspect is an input to the retrospective
  machinery that produces this epic's own findings. A confidently-healthy verdict over instruction
  text means **retrospective conclusions have been drawn from a substrate whose quality was never
  measured** — absence of findings from this path has never been evidence of absence.
- ⭐ **The most instructive part of the record**: the previous *remediation* was itself the thing that
  sampled. It enumerated the synthetic classes visible in **its** sample; later transcripts exhibited
  several more. **That is the standing "a named list is a sample" rule applied to a fix rather than to
  a reviewer.**
- **A proven pattern to copy**: the same skill already ships a partition distinguishing *nothing was
  there* from *nothing was reported*. D3 is the same shape — reuse it rather than inventing one.
- **Serialization.** Shares the retrospective bundle with sibling plans — do not run concurrently.
