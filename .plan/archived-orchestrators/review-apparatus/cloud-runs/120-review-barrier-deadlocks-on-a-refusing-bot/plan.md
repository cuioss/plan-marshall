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

# The refusal taxonomy has no STRUCTURAL member, so a size-capped reviewer is offered a non-option

**Epic:** review-apparatus
**Branch prefix:** fix

## ⛔⛔ READ FIRST — this plan's original premise is REFUTED, and two of its three deliverables are already shipped

This plan was staged as *"the pre-merge review barrier deadlocks when a required bot refuses, and there
is no sanctioned way to record 'this bot is degraded, proceed with a documented gap'."*

**That is false, verified first-party against merged `main`:**

| Original deliverable | Verdict |
|---|---|
| Distinguish a **refused** bot from an **unproven** one | ✅ **SHIPPED** — the completeness script splits an awaitable-window refusal from a hard-quota one via the bot's registry `rate_limit_class` |
| A sanctioned, recorded coverage-gap acceptance | ✅ **SHIPPED AND EXERCISED** — a merge-authorization grant/check surface exists, is HEAD-bound, is gap-class-bound, and is **fail-closed** (an unmatched class fails rather than acting as a wildcard). It has been used on a real PR |

⛔ **Do not implement either. Do not re-litigate the deadlock framing** — a refusing bot no longer traps
a plan, because the override is the exit.

⚠ **The slug no longer describes the work.** Keep the file name (a cloud session is bound to its path)
but **state the real subject in the first line of the PR and the report**, so no reader is misled by it.

## Problem — what genuinely survives, and it is one thing

**The taxonomy models *temporal* refusal only.** Ground-truth check: the completeness script contains
**no** `diff_size` / `size_cap` / `150000` / `too_large` / `size_limit` token anywhere.

⭐⭐ **The remedy sets are DISJOINT, which is why this is a missing member rather than a missing label:**

> A rate limit is a **temporal** refusal — the same request succeeds later. A diff-size cap is a
> **structural** one — the same request **never** succeeds. Any handling that offers *"wait / accept the
> gap"* as the option pair is **offering a non-option on the size branch.**

The step config carries a rate-window await and a rate-window timeout — **the machinery it has is a
rate-window one.** A size refusal is therefore either silently bucketed with the rate refusal or
reported as unexplained non-participation.

⭐ **And the exclusion recurs by size, not by chance:** one reviewer's cap is a fixed diff-character
threshold, so **every** plan over it gets no review from that reviewer, predictably and forever. ⭐ The
cap is **knowable before the barrier runs** — a diff size is measurable at PR creation — so this is a
predictable exclusion that can be **disclosed in advance** rather than discovered at the gate.

## Goal

A structural refusal is a distinct, first-class member of the refusal taxonomy with its own remedy set,
its cap value recorded so the gap is auditable against the actual diff size, and no await ever offered
on it.

## Deliverables

Three. ⚠ **This plan is small by design** — see the folding note under Notes.

1. **D0 — GATE, mutates nothing: DERIVE the barrier's terminal-state population.** Enumerate every state
   in which the barrier can end and classify each as *passable by the plan's own action* or *not*.
   ⛔ **A state a plan cannot exit by acting is a deadlock, and deadlocks are the finding.**
   ⛔ **Derive from the shipped taxonomy, not from a hand-list.** The contract now enumerates the
   members normatively, which makes a hand-list strictly worse than the source. Classify each member,
   and identify which have a remedy that is a **non-option** for them.
   ⛔ **This deliverable HALTS the plan** if the taxonomy members cannot be enumerated from the contract
   and the classifier.
   *Done when:* every terminal state is classified with its remedy set, and each non-option pairing is
   named.

2. **D1 — structural refusal becomes its own taxonomy member with its own remedy set.** Remedies are
   **split / accept / disable-for-this-PR** — ⛔ **never await.**
   Record the **cap value** in the finding, so the gap is auditable against the actual diff size rather
   than asserted.
   ⭐ **Disclose in advance where possible.** The diff size is measurable at PR creation, so a plan whose
   footprint exceeds a declared cap can know at outline that a given reviewer will not review it. Surface
   each bot's declared size limits where a plan can consult them.
   *Done when:* a size-capped refusal resolves to the structural member, carries the cap, and is never
   offered an await — proven by a test per branch.

3. **D2 — tests, each verified to FAIL pre-fix.** (a) A size refusal classifies as structural, not as a
   rate refusal and not as unexplained non-participation. (b) No await is offered on the structural
   branch. (c) The recorded finding carries the cap value and the measured diff size. (d) The
   terminal-state population from D0 is derived, **non-empty-asserted first**, and every member covered.

## Out of scope

- **Re-implementing the refused-versus-unproven split.** Shipped.
- **Building a coverage-gap acceptance mechanism.** Shipped, exercised, HEAD-bound, and fail-closed.
- **Re-litigating the deadlock framing.** The override is the exit.
- **Splitting large PRs as the remedy.** A plan-shape change with its own costs, explicitly declined
  elsewhere in this epic. D1 *offers* split as an operator-facing option; the plan does not perform it.
- **Making the barrier block on a coverage gap.** The existing design is fail-closed on required-bot
  participation and correct; this plan adds a member to the taxonomy, not a new gate.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the
  refusal state constants and the `rate_limit_class` branch.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/` — the per-bot registry
  documents, for the declared caps.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the barrier's
  terminal states and its remedy prose. ⚠ **Recently modified by a merged PR — re-ground every line
  reference and every quoted predicate against merged `main` before scoping.**
- `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py` and the completeness tests.
  ⚠ Also recently modified.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The refused/unproven split is shipped, keyed on the registry `rate_limit_class` | OBSERVED | The branch in `review_completeness.py` |
| A HEAD-bound, gap-class-bound, fail-closed merge-authorization surface exists and has been used | OBSERVED | The merge-authorization command module — read its grant/check verbs and its fail-closed unmatched-class path |
| The completeness script contains **no** size-refusal token (an asserted **absence**) | OBSERVED — ⛔ **but re-verify by reading the classifier's branches, not by re-running a token search.** A later edit can add the word in a docstring and make a literal search wrongly read as a refutation; this epic has already been bitten by exactly that. **State the predicate and the scope searched** |
| One reviewer's cap is a fixed diff-character threshold | HYPOTHESIS — reported by the run that hit it, **second-hand here** | ⛔ **Re-derive before pinning a test to the number.** The *existence* of a structural cap is what D1 needs; the exact figure is a lead |
| A recent merged PR already altered the barrier's behaviour on a refusing bot | HYPOTHESIS | ⛔ **Check this specifically.** If any part of D0's population is already handled there, **scope only the remainder and say what moved** |
| The plan's own original premise | ⛔ **REFUTED** | Stated above with its evidence. Do not carry the original wording forward |

⛔ **Do not go looking for `.plan/`.** The inbox messages and landing records behind this plan are
git-ignored and **absent from your clone**. Everything needed is restated here.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **Every D2 case proven discriminating by mutation.** Case (b) — no await on the structural branch — is
  the one that distinguishes this plan from a relabelling exercise.
- **Publish the terminal-state population and its size** in the run report, with the derivation method.
- ⭐ **Cold read, aimed at the operator-facing remedy text.** D1 introduces a new refusal member with a
  new remedy set. Have the pre-PR verification sub-agent read the new text **cold** and answer: *this
  reviewer did not review my PR — what are my options?* ⛔ **If "wait" appears among the options for the
  structural case, the fix has reproduced the non-option it was written to remove.** Report the answer
  verbatim.

## Notes

- ⭐ **The archetype this plan originally documented is still worth keeping, even though its premise was
  refuted:** the previous fix closed a false-green hole and opened a permanent-red one. Making a
  force-done record non-authorizing was **right** — it stopped a forced record buying a merge — but
  force-done was the only escape, and nothing replaced it until the authorization surface shipped.
  **A fix for a defect that reproduces the defect's family** is this epic's most frequent recurrence.
- **Why the barrier's design is correct and is not what changes.** Its first predicate cannot see an
  *absence* — a bot that never reviewed publishes nothing and reads as clean. Its second re-derives
  participation from the provider, **deliberately not trusting** the review step's own record, because a
  force-done record is byte-identical to an earned pass. Both remain right.
- ⚠ **Folding note, recorded so it is not re-derived.** With two deliverables dropped this plan is small
  and sits on the same surface as the epic's disclosure plan. **Whether to fold it there rather than run
  it alone is an open question for whoever hands this over** — it is recorded here, not decided here.
- **Sequencing.** Shares `branch-cleanup.md` with other staged plans in this epic. ⛔ **Sequence, never
  pair.**
