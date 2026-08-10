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

# A coverage shortfall is disclosed against the roster, not against the required set — and the opposite polarity is worse

**Epic:** review-apparatus
**Branch prefix:** fix

## ⛔⛔ READ THIS BEFORE THE DELIVERABLES — most of this plan's surface is the contract governing you

The primary defect lives in `cloud-plan-lane/SKILL.md` — **the skill you loaded as your first action.**
The lane forbids a run from self-approving a change to the contract that governs it, and that
prohibition binds here.

⇒ **Every deliverable below that touches `cloud-plan-lane/SKILL.md` is authored to PRODUCE A PROPOSAL,
not to apply an edit.** Write the exact replacement text, the rationale, and the tests it would need
into the run report, as a numbered proposal per deliverable. **Do not edit that file.** A prior cloud
run hit this same wall and correctly recorded three contract proposals instead of shipping them; that
is the precedent and it is the expected outcome here.

⭐ **The plan is still worth running**, because the analysis — which population, which denominator,
which polarity — is the hard part and is fully performable. What it may not do is ratify its own
answer. If a deliverable's whole content turns out to be a `cloud-plan-lane` edit, its outcome is
`proposal recorded`, and that is a **complete** result, not a partial one. Say so plainly in the report
rather than describing the run as blocked.

## Problem

A shipped review-coverage shortfall disclosure derives its expected-reviewer population from the
**registry roster** — every `author_login` in the per-bot registry documents — and fires whenever *any*
member of that roster did not review. It never reads `required_bots` / `optional_bots`. So on a PR
whose required quorum is fully satisfied, the mechanism still announces a "shortfall" the moment an
**optional** bot is silent.

⛔ **That is a false-alarm generator inside a disclosure mechanism** — the mirror image of the
vacuous-guard class this epic catalogues. Not a gate that passes having examined nothing, but a gate
that reports a gap that is not one. A disclosure that cries wolf gets tuned out, and then the real
shortfall reads as noise. **The defect is the miscalibration, never the disclosing.**

⛔⛔ **And the opposite polarity is live on the same mechanism, and it is worse.** Observed across
several PRs: the required reviewer resolved to `participated_but_empty` — it participated and filed
nothing — while an *optional* reviewer produced 16 records, 14 actionable, 11 fixed, including three
real Majors, and a second optional reviewer was size-capped and never saw the diff at all. **The
barrier passed with `participation_complete: true`.**

⭐ The sharpest available statement of the class: *not a check that was wrong — a check whose predicate
is satisfiable without the thing it exists to establish.*

⇒ **If the disclosure treats `participated_but_empty` as participation, it reports FULL COVERAGE on a
PR where nothing was reviewed.** A false alarm costs credibility; a false clean costs the review.

⛔ **A fix that only swaps the denominator from roster to required set makes the false-clean half
worse**, because it removes the incidental noise that was the only thing drawing attention to a thin
review. **Both polarities must be fixed in one pass.**

## Goal

A coverage statement says what it measured, over which population, and distinguishes four things a
reader currently cannot tell apart: the required quorum was met; the required quorum was met *by empty
participation*; an optional reviewer is accountably absent; and no required reviewers are configured at
all.

## Deliverables

Four. Under the split guard.

1. **D1 — the verdict distinguishes required from optional; the record still ranges over the roster.**
   ⛔ **Do not fix this by narrowing the population to the required set and dropping the rest.** The
   roster-wide participation record is valuable and deliberately population-derived — a hand-maintained
   reviewer list is the very defect that mechanism exists to prevent. **What is wrong is the VERDICT
   computed over the population, not the population read.** Removing optional bots from the record
   would trade a false alarm for a blind spot.
   State **both** numbers rather than replacing one with the other: *"required quorum met (1 of 1); 2
   optional reviewers silent — 1 rate-limited, 1 size-capped"*, never a bare ratio with an unstated
   denominator.
   ⭐ **Surface `participated_but_empty` distinctly**, so a green participation check resting entirely
   on empty participation is visible as such rather than indistinguishable from a substantive clean
   review.
   ⛔ **This does not justify dropping or demoting any reviewer.** Two independent reporters said so
   unprompted and this plan repeats it: the ask is to make the gate's information content legible,
   never to re-rank bots.
   *Outcome:* a **proposal** with the exact replacement text for the shortfall condition and the
   participation-record section.

2. **D2 — every emitted coverage ratio NAMES its denominator.** ⛔ **A bare "N of M" is the defect.**
   Each emission site — the merge-gate disclosure, the report's reviewer-participation table, and the
   run report's coverage line — states which population M is. This is the epic's standing
   publish-your-population rule applied to a disclosure surface.
   ⛔ **Consume the epic's counting rule; do not re-derive it.** Three plans in this epic need
   per-reviewer finding counts and one of them owns the rule for all three. If that plan has not landed
   when this one runs, **state the rule here and hand it back in the report**, so the epic still has
   exactly one.
   ⚠ **Extend the rule to the review-quality instrument itself.** On one run it recorded
   `outcome: done`, `display_detail: "0 pr-comment findings — nothing to compare"` **on precisely the
   run where reviewer coverage collapsed to zero** — the instrument reported a benign no-op in exactly
   the condition it exists to detect, because an empty population reads as *nothing to compare* rather
   than *the comparison was impossible*. ⛔ When zero findings exist it must distinguish *reviewers ran
   and found nothing* from *no reviewer produced content*, and grade the latter **`indeterminate`** —
   never `done` with a benign summary. **It must not mark itself complete on a comparison it could not
   perform.**
   *Outcome:* proposal text for the lane surfaces; a real code change for the instrument if it lives in
   `marketplace/bundles/`.

3. **D3 — the config read is resolved, not assumed — and the vacuous case is rendered as vacuous.**
   `required_bots` / `optional_bots` are read from the resolved step config, and the
   `bot_lists_provenance` field is honoured: an `answered` provenance is a deliberate operator answer,
   an unset one is not.
   ⛔ **An empty `required_bots` means the quorum is VACUOUSLY SATISFIED** per the contract — so the
   disclosure must distinguish *"required quorum met"* from *"no required bots configured"* and must
   never render the second as the first. **This is the vacuous-authority archetype and it is reachable
   by default** in any project that has not answered the question.
   ⚠ **A settled constraint that shapes this deliverable: the cloud lane runs WITHOUT the generated
   executor.** A fix that reaches the config through the executor-mediated config script would be
   **inert in the lane it is fixing.** Settle the read mechanism before designing the fix; if no
   executor-free read path exists, that finding *is* D3's result and belongs in the proposal.
   *Outcome:* the read mechanism named and settled, plus proposal text.

4. **D4 — tests, each verified to FAIL pre-fix, each proving discrimination by mutation.** At minimum:
   required-bot silent (a real shortfall — must fire); optional-bot silent with required met (must NOT
   fire as a shortfall, and must still be recorded); required bot `participated_but_empty` (must be
   visible as empty participation, not as coverage); and empty `required_bots` (must render as vacuous,
   not as met).
   ⛔ A test that passes both pre- and post-fix is vacuous — **prove each one discriminates.**
   ⚠ Where a deliverable resolved to a proposal, D4 still authors the tests and states that they are
   staged against the proposal rather than against a landed change.

## Out of scope

- **Editing `cloud-plan-lane/SKILL.md`.** See the block at the top: a run may not self-approve a change
  to the contract governing it.
- **Dropping, demoting, or re-ranking any reviewer**, including reassigning which one is `required`.
  That would move a merge verdict; this plan only makes the existing verdict legible.
- **Deriving a per-reviewer participation rate from the instances cited here.** ⛔ Pooling a
  rate-limited absence, a size-capped absence, a participation-with-zero-yield, and a
  required-present-but-empty **mis-attributes all four.** The required-vs-optional composition question
  needs a corpus and belongs to the cross-plan retrospective view — both sibling epics agree, and
  neither is staging for it.
- **Auditing other repositories for the vacuous-quorum default.** The contract defaults `required_bots`
  to empty, so any project that has not answered the question runs a vacuously-satisfied quorum. ⛔
  **Unverified beyond this repo — a lead, not a finding.** D3 makes the vacuous case *visible* where it
  occurs; auditing elsewhere belongs to whoever owns those repos.
- **The absence-cause partition** (why a bot did not review), owned by another staged plan in this
  epic. This plan owns the **denominator** (whose absence counts). ⛔ If the run finds the two converge
  on one mechanism, **say so rather than shipping two.**

## Expected surface

- `.claude/skills/cloud-plan-lane/SKILL.md` — the per-reviewer participation record, the merge-gate
  shortfall condition, and the report's coverage line. ⛔ **PROPOSAL ONLY — do not edit.**
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — **read-only
  here.** The roster parse is correct and is not the thing being changed.
- Whichever site resolves `required_bots` / `optional_bots` from the step config — see D3's
  executor-free caveat.
- The review-retrospective finalize step — the `indeterminate` grading from D2. **This one is ordinary
  source and may be changed.**
- The matching `test/plan-marshall/...` trees.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The expected-reviewer population is roster-derived | OBSERVED | `cloud-plan-lane/SKILL.md` § recording per-reviewer participation: *"Read the `author_login` of every such registry doc — that set **is** the expected reviewer population for this PR"* |
| The disclosure fires on ANY roster member | OBSERVED | Same file, the merge-gate condition: *"When **any** expected reviewer's verdict is not `reviewed`, state the shortfall"*. Neither `required_bots` nor `optional_bots` appears in it |
| An optional bot's absence never blocks | OBSERVED | `bot-participation-contract.md` — *"An optional bot resolving to any member never blocks"*, and *"whether the absence is tolerable is a required-vs-optional question, not a waiting question"* |
| `rate_limited` **is** in the shipped taxonomy and does not collapse into "did not participate" | OBSERVED | The refusal state constants in `review_completeness.py`, split by the registry `rate_limit_class`. ⛔ **Already settled — do not re-derive.** The residual question is whether the *disclosure* consumes the state |
| No other emitted coverage figure reads the roster as its denominator (an asserted **absence**) | HYPOTHESIS | Every emission site of a coverage ratio. ⛔ **The higher-risk half**: an unverified absence ships a fix that corrects one emitter while its siblings keep publishing the wrong denominator. **Publish the scope searched and the file count with the absence claim** |
| Four recomputed landings each met their required quorum at 1 of 1 | HYPOTHESIS | The stored comment bodies per PR, matched against the resolved `required_bots`. ⛔ **Do not inherit the recomputation** — it came from a message that had to retract two of its own claims. Corroborate before publishing any figure derived from it |
| The disclosure has actually fired a false shortfall on a real run | UNSETTLED | ⛔ **If no instance is found, that does NOT refute the finding** — the code path is OBSERVED. But say so plainly rather than carrying an implied incident count of zero as though it were evidence of impact |

⚠ **The per-bot states quoted in this plan are the review step's own report, not an independent
measurement.** Only reading the stored comment bodies is evidence of participation. **Re-derive before
scoping on them.** Every count here is likewise a lead.

⛔ **Do not go looking for `.plan/`.** The inbox messages and landing records behind this plan are
git-ignored and **absent from your clone**. Everything needed is restated here.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **Mutation-prove each D4 case.** The optional-silent case and the `participated_but_empty` case are
  the discriminating ones — a detector that behaves identically on them and on a real shortfall has not
  been fixed.
- **Publish the population with every ratio** the run itself emits, including in its own run report.
  A plan about unstated denominators must not state one.
- ⭐ **Cold read, and it is the central check here.** Take the proposed replacement text for the
  shortfall statement and have the pre-PR verification sub-agent read it **cold**, then answer three
  questions: (1) *was the diff reviewed?* (2) *is this a gap I must act on, or an accounted-for
  absence?* (3) *how many reviewers were required, and how do I know?* Report the answers verbatim. If
  question 2 cannot be answered from the text, the proposal has reproduced the defect it describes.
- ⭐ Run the same cold read against the **empty-`required_bots`** rendering and ask *"was a required
  review performed?"* If the cold answer is "yes", the vacuous case is still rendering as met.

## Notes

- **This is a correction to shipped work, not a rediscovery.** The disclosure it corrects was shipped
  deliberately by a plan in a sibling epic; read that landing before scoping so the correction is
  aimed at the mechanism rather than at the decision to disclose at all.
- **A recoverable refusal that is not awaited is a discarded opportunity.** On one run a reviewer was
  `refused_awaitable` while the rate-window await was **off for that plan**, so the one refusal
  convertible into real review content was dropped **silently by configuration** — and that the option
  existed appeared only in an override's prose. Surface it.
- **Sequencing.** Surface is disjoint from the participation classifier and from the merge path, so
  this can run alongside those. It **overlaps on the required-vs-optional question** with the
  absence-cause plan in this epic; the axes are genuinely different (why-absent versus whose-absence-
  counts) but converging is possible — report it if so.
