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

# `post_responses` re-transmits already-sent replies, and reports the re-sends as work done

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

`github_pr post_responses` is not idempotent across rounds. On one observed run, round 2
**re-transmitted all four round-1 replies** alongside three genuinely new ones and reported
`count_responded: 7`.

**Two distinct defects, and the second is the one that matters most here:**

1. **The re-transmission itself.** Duplicate replies land on the reviewer's threads — noise on a third
   party's surface, and on a rate-limited bot it is spend against a quota this epic is separately
   fighting to conserve.
2. ⛔⛔ **The count is reported as work done.** `count_responded: 7` for three decisions is a
   **confident affirmative over an action that mostly did not need to happen**. Any consumer reading it
   as "replies this round" is wrong, and the review-retrospective's %-resolved figures are computed from
   this family of counts.

⭐ **The polarity is worth naming.** Unlike most findings in this epic the *action* is relatively
harmless and the *signal* is the defect. ⛔ **Do not scope this as "stop double-posting" and leave the
count.**

**The mechanism is settled, first-party.** `cmd_post_responses` selects **every** `pr-comment` finding
whose `resolution` is in `_RESPONDABLE_RESOLUTIONS` and whose `pr_number` matches. There is **no
transmitted/acknowledged marker anywhere in the selection predicate** — nothing records that a
disposition was already sent, so a round-1 reply re-qualifies in round 2.

⭐ **The documented rationale is inverted, which is why the gap survived.**
`verification-feedback.md` Step 8 claims *"already-responded findings are terminal and no longer
pending."* But `_RESPONDABLE_RESOLUTIONS` **is** the terminal set — terminal is the **selection**
criterion, not an exclusion criterion. ⇒ **A finding becoming terminal is what makes it eligible, and it
then stays eligible forever.** The doc reads as if a guard exists; the code has no prior-transmission
term at all.

⭐ **The verb is already careful in a neighbouring dimension, which sharpens the finding rather than
softening it.** Its `pr_number` gate exists precisely because a plan-scoped store would otherwise
misdeliver another PR's dispositions *"while the return still reports `count_untransmitted: 0` — a
confidently green report for a partly-misdelivered action"* (its own docstring). ⇒ **The author already
reasoned about a confidently-green count over a wrong row set, and closed the cross-PR case while
leaving the cross-ROUND case open.** The missing key is not an oversight of the concept; it is the same
concept not carried to the second axis.

## Goal

A reply is transmitted once per (thread, disposition) unless the disposition itself changed, and the
count a consumer reads names what it actually counted.

## Deliverables

Four.

1. **D0 — GATE, mutates nothing: derive every consumer of the returned count.**
   ⛔ **The absence question is already SETTLED — do not re-litigate whether the key is missing.** It
   is: read the selection predicate and confirm once, then move on. **D0's real job is the consumer
   derivation**, which is untouched and still owed.
   ⛔ **Derive it; do not hand-list it.** The standing rule that *a list of call sites is a sample, not
   an enumeration* has bitten this epic twice. Include the review-retrospective's %-resolved
   computation.
   ⛔ **This deliverable HALTS the plan** if the consumer set cannot be derived — changing the meaning
   of a field whose readers are unknown moves the defect rather than fixing it.
   *Done when:* the consumer set is published with its size and derivation method.

2. **D1 — transmission is idempotent per (thread, disposition).** A reply already posted for an
   unchanged disposition is not re-sent.
   ⚠ **A disposition that genuinely CHANGED between rounds must still be transmitted** — the fix is a
   **key**, not a suppression.
   ⭐⭐ **The reference implementation already exists in-tree — copy it, do not design one.** The Sonar
   provider gets this right and the GitHub provider does not:

   | Element | `workflow-integration-sonar/scripts/sonar.py` | `workflow-integration-github/scripts/github_pr.py` |
   |---|---|---|
   | imports `mark_finding_responded` | ✅ | ❌ none |
   | skips on `finding.get('responded')` | ✅ | ❌ none |
   | sets the marker after sending | ✅ | ❌ none |

   ⛔⛔ **A naive `grep responded` finds hits in BOTH files and suggests parity.** The GitHub
   occurrences are a **local output accumulator of the same name**, not a persisted per-finding marker.
   ⭐ **The discriminator is `mark_finding_responded` / `finding.get('responded')`, never the bare
   word.** This is a same-name-different-thing trap, and it is exactly why the defect survived three
   sightings.
   The predicate becomes `terminal AND NOT responded`. ⛔ **Set the marker in the SAME unit of work
   that sends the reply** — a marker written in a later step reintroduces the gap it closes.
   *Done when:* a second round over unchanged dispositions transmits nothing, and a changed disposition
   still transmits, both proven by tests.

3. **D2 — the count reports what it names.** Distinguish newly-transmitted from already-satisfied.
   ⛔ **Do not silently redefine the existing field.** D0's consumer derivation decides whether to
   narrow it or add a sibling — a narrowed field with unmigrated consumers moves the defect rather than
   fixing it.
   *Done when:* every consumer D0 found reads a field whose name matches its content, and the migration
   (or the decision not to migrate) is stated per consumer.

4. **D3 — tests, each verified to FAIL pre-fix.** (a) The observed shape: four round-1 replies plus
   three new dispositions in round 2 transmits **3** and reports **3**. (b) A disposition that changed
   between rounds **is** re-transmitted. (c) The consumer population D0 derived is
   **non-empty-asserted first** and every member covered — copy the derivation pattern from
   `test/_shared/_dispatch_roster.py`.
   *Done when:* all three hold, each proven discriminating by mutation.

## Out of scope

- **Measuring whether duplicate replies materially affect bot rate-limit consumption.** Relevant to
  severity, not to correctness. ⛔ **Do not block the fix on measuring it.**
- **Deriving a rate from the prior sightings.** ⛔ **Three observations are not a rate.**
- **Auditing every external-transmit verb across all providers** for a prior-transmission term. If D0
  or D1 shows this widens, **name the population and say the sweep was not done** — it crosses both
  providers and possibly a third, and it is a different derivation from D0's consumer question. ⛔ Do
  both or state clearly which was skipped; do not let one stand in for the other.
- **Re-litigating the missing key.** Settled. Read it once, then spend the run on the consumers.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` §
  `cmd_post_responses` and the `_RESPONDABLE_RESOLUTIONS` selection loop. ⚠ **The file was modified by a
  recent merged PR** (participation plumbing, a different function) — re-ground every line number.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py` — **read-only**,
  the reference implementation to copy.
- `marketplace/bundles/plan-marshall/skills/.../verification-feedback.md` — the inverted rationale in
  Step 8; correct the prose so it stops describing a guard that does not exist.
- The review-retrospective finalize step — a known consumer of response counts.
- `test/plan-marshall/workflow-integration-github/**`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The selection predicate has no prior-transmission term, so a round-1 reply re-qualifies in round 2 | OBSERVED | `cmd_post_responses`'s selection loop — read the predicate, not the docstring |
| The documented rationale in Step 8 is inverted (terminal is the *selection* criterion) | OBSERVED | `_RESPONDABLE_RESOLUTIONS`'s membership versus the Step 8 prose |
| The Sonar provider implements the marker and the GitHub provider does not | OBSERVED | The three-element comparison in D1. ⛔ **Check for `mark_finding_responded` / `finding.get('responded')`, never the bare word `responded`** |
| The re-transmission and the inflated count, across three sightings | OBSERVED by the filers, **re-derived by nobody here** | ⚠ Two of the three came from a consuming project at an older bundle that predates this tree. **Re-ground before scoping, and check whether any sighting postdates a change to this surface** |
| All three sightings share one root cause | HYPOTHESIS | **Three occurrences of one symptom are not three occurrences of one bug.** D0/D1 confirms or splits them |
| The consumer set of the count | HYPOTHESIS | **D0 derives it.** Do not assume the retrospective is the only reader |
| Duplicate replies materially consume bot rate limits | UNKNOWN | Out of scope — see above |

⚠ **One escape worth knowing and not over-reading**: a past PR avoided this only because its store held
exactly **one** finding. ⛔ **n=1 masked it, which is not evidence of safety.**

⛔ **Do not go looking for `.plan/`.** The inbox messages and the epic ledger entry behind this plan are
git-ignored and **absent from your clone**. Everything needed is restated here.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **Every D3 test proven discriminating by mutation**, and the consumer-population size published in the
  test output.
- **Publish the consumer derivation in the run report** with its method — this plan is about a count
  whose meaning drifted from its readers, so its own derivation must be legible.
- ⭐ **Cold read, aimed at the corrected prose and the renamed count.** Have the pre-PR verification
  sub-agent read the Step 8 text and the count field's documentation **cold** and answer: *if I run this
  verb twice on the same findings, what happens the second time, and what will the count say?* If the
  cold reading still suggests the old behaviour — or cannot answer — the wording failed.

## Notes

- **This defect had no owner for three sightings**, because each time it was recorded as a recurrence
  line under some other finding. ⭐ **That is itself the finding**: a defect recorded only as an appendix
  to other defects accumulates sightings without ever acquiring an owner. This plan exists to end that,
  so **do not fold any part of it back into another plan's appendix.**
- **Sequencing.** Touches `github_pr.py`, which several other staged plans in this epic also claim. ⛔
  **Sequence, never pair.** The functional boundary looks disjoint (`post_responses` versus
  `fetch_findings` versus the participation comparison) but that boundary is **unverified** — confirm at
  D0.
- **Adjacent to the review-retrospective**, which another staged plan also touches. **Coordinate; do not
  ship two vocabularies for one count.**
