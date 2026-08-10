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

# The AI-agent-block ingestion contract contradicts itself in one file, four lines apart

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

`automatic-review/standards/coderabbit.md` gives **two mutually exclusive instructions** about a review
bot's `🤖 Prompt for AI Agents` block, **four lines apart**:

- a *"Strip from the body before reasoning (noise, not findings)"* list that names the AI-agent prompt
  block explicitly; and
- immediately after it, a trust-boundary section calling the **same block** *"high-value structure (the
  cleanest per-finding payload)"* and instructing the reader to **extract file/line/summary as fields**.

A reader following this document does one or the other depending on which paragraph they reach first,
and **nothing announces the divergence.**

⛔ **This is not a documentation tidy-up.** The contradiction is why a real configuration dispute could
not be settled: a change in the bot's own config repository turned `enable_prompt_for_ai_agents` **off**
on the grounds that nothing consumes the block, while the config comment it replaced said to keep it
**because plan-marshall ingests it.** Both cannot be true. Settle which behaviour is correct, make the
standard say exactly one thing, verify the enacting code matches, and then close the dispute on
evidence.

⭐ **The population is already settled — do not spend effort re-deriving it.** A first-party sweep of
all three per-bot registry documents found the contradiction in **exactly one** of them. The second
document carries the **extract** half alone with no strip-list naming the block, which is *consistent*,
not contradictory. The third records that its bot **emits no such block at all**, so this defect is
bot-specific and its resolution **must not be generalised** to that one.

⇒ **The population is ONE for the contradiction, TWO for the resolution:** if the resolution is
**STRIP**, the second document then diverges from the settled rule and must be aligned in the same
pass. **Scope accordingly and do not widen.**

## Goal

The AI-agent block has exactly one documented treatment, the code that enacts it agrees, and the
configuration dispute is closed on evidence rather than on either party's assumption.

## Deliverables

Four.

1. **D0 — one resolved instruction, with the losing reading REMOVED rather than qualified.** The block
   is either stripped as noise or extracted as a payload, stated once.
   ⛔ **Include the reasoning that settles it.** A contradiction removed without a recorded cause
   returns.
   ⚠ If the resolution is **STRIP**, align the second registry document in the same pass; if
   **EXTRACT**, it already agrees and needs nothing.
   *Done when:* one treatment is stated in one place, the other reading is deleted, and the rationale is
   recorded beside it.

2. **D1 — the enacting surface verified to match the resolved instruction.** Locate whatever actually
   strips or extracts, and confirm it agrees with D0. If the code and the resolved instruction
   disagree, **the code is corrected** — a standard describing behaviour nothing implements is the same
   defect in the other direction.
   ⚠ **The strip may be prose-only**, enacted by a model reading the standard rather than by a script.
   ⛔ **If it is, say so explicitly and report D1 as a no-op** — do **not** invent a code change to give
   the deliverable something to do.
   *Done when:* the enacting site is named, or its absence is stated as a finding with the search that
   established it.

3. **D2 — close the configuration dispute on the evidence produced here, as a PROPOSAL.**
   ⛔⛔ **The configuration lives in a DIFFERENT repository, and this plan changes nothing there.** Two
   independent reasons: revisiting that decision needs operator agreement, which this run cannot obtain;
   and this plan's diff is scoped to this repository.
   ⇒ **Write the verdict and the recommended action into the run report as a proposal**: either the
   config change stands (nothing consumed the block) or the standing watch is promoted to a real
   degradation and the config decision should be revisited with the operator. **Name the evidence for
   whichever way it goes.**
   *Done when:* the run report carries the verdict, its evidence, and the recommended action — and no
   commit touches another repository.

4. **D3 — if and only if the resolution is EXTRACT: a bounded ASSESSMENT of what was lost.** The block
   has been off since the config change, so an EXTRACT resolution means a live degradation on every
   review since.
   ⛔ **State it as a bounded assessment of the payload's ROLE, not as a tally.** A count of findings
   that would have been extracted is **unknowable after the fact — do not manufacture one.** This
   project has repeatedly read a volume number as a coverage number.
   *Done when:* the assessment names what the payload contributes and what its absence costs, with no
   fabricated count. If the resolution is STRIP, this deliverable is **not attempted** and the report
   says so.

## Out of scope

- **Touching any other repository.** D2 produces a proposal. The bot's config repo, its README, and its
  open PR are read-only inputs at most.
- **Generalising the resolution to the bot that emits no such block.** Its registry document already
  records that it produces nothing to strip or extract; changing it would be a fix aimed at a surface
  that has no defect.
- **Reviving a separate, closed configuration PR** in that repository. It is closed and falsified — its
  own final commit says so. Its notes remain readable for measurement context only.
- **Manufacturing a missed-findings count.** See D3.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — the strip-list
  and the AI-agent trust-boundary section. **The whole contradiction lives here.**
- `.../automatic-review/standards/sourcery.md` — touched **only if** the resolution is STRIP.
- The enacting ingestion path under `.../automatic-review/scripts/` or
  `.../workflow-integration-github/scripts/` — **may be prose-only**.
- `.../automatic-review/standards/comment-patterns.json` — if the strip patterns are data-driven, this
  is the real strip site.
- ⛔ **NOT in surface:** the bot's own configuration repository. Read-only, proposal only.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The contradiction is real and in one file | OBSERVED | `coderabbit.md` — **verify by SYMBOL (the two section headings), not by line number.** The strip-list names *"the AI-agent prompt block (next section)"*; the immediately following trust-boundary section calls it *"high-value structure (the cleanest per-finding payload)"* and says to *"extract file/line/summary as fields"* |
| The contradiction exists in **exactly one** registry document | OBSERVED — settled first-party | Re-run the sweep: a case-insensitive search for `strip` over the second document returns zero matches, and the third records that its bot emits no such block. ⭐ **The per-document fan-out is not owed** |
| `automatic-review/SKILL.md` states the block must never be treated as executable | OBSERVED | ⛔ **Consistent with BOTH readings** — treating text as data-to-extract and discarding it are both non-execution. **Do not mistake it for a tie-breaker** |
| The config flag is now off, and the comment it replaced asserted the opposite rationale | OBSERVED | Restated here. ⚠ **That checkout was once found on an unmerged, falsified branch — confirm the branch before reading any config there as live**, and treat it as read-only regardless |
| There is an **enacting script**, not only prose | HYPOTHESIS | Locate whatever performs the strip in the ingestion path. ⛔ **If prose-only, D1 is a no-op and the plan says so** rather than inventing a code change |
| Nothing else in the bundle set consumes the block (an asserted **absence**, higher risk) | HYPOTHESIS | Search the **whole** marketplace tree for the block's marker text, not just the review skill. ⛔ **An unverified absence here is what produced the dispute in the first place** — publish the scope searched and the file count with the claim |

⛔ **Do not go looking for `.plan/`.** The epic ledger and the standing watch referenced here are
git-ignored and **absent from your clone**. Everything needed is restated above.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **The absence claim publishes its scope.** State how much of the tree was searched and how many files
  — an absence claim without its search scope is the failure that produced this plan.
- ⭐ **Cold read, and it is the decisive check for this plan.** The deliverable *is* text that drives a
  reader's behaviour. Have the pre-PR verification sub-agent read the revised document **cold** —
  without this plan — and answer one question: *when I encounter an AI-agent prompt block in a review
  body, what do I do with it?* The answer must be unambiguous and must match D0's resolution. ⛔ If the
  cold reader hedges, or can construct both readings, **the contradiction has been reworded rather than
  removed.** Report the answer verbatim.
- ⭐ Ask the cold reader a second question: *is this block safe to execute?* The expected answer is a
  clear no under either resolution. If the rewrite lost that, D0 traded one defect for a worse one.

## Notes

- **Sequencing.** Nothing blocks it, and it overlaps nothing else staged in this epic. ⚠ A plan in a
  sibling epic may touch the same standards directory — **re-verify that boundary by slug**, not by
  plan id.
- **Why this is sequenced early despite being small.** If the resolution is EXTRACT, the block has been
  off the whole time and this is a **live degradation on every review** — and any downstream plan that
  reads a published review as its oracle is easier once ingestion is unambiguous.
- **The dispute is the point, not the wording.** Two parties each read one half of a self-contradicting
  document and reached opposite, internally-consistent conclusions. Neither was careless. ⇒ **The fix is
  to make the document incapable of supporting both readings**, which is why D0 requires deletion rather
  than qualification and why Verification is a cold read rather than a diff review.
