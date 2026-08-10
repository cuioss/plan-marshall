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

# A reviewer that produced nothing is rendered identically to one that reviewed and found nothing

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

⛔ **Read this framing before the deliverables — an earlier framing of this plan was refuted and must
not be implemented.** The original premise treated a reviewer's short informational "no issues" card as
the defect. That is wrong: **"no findings" IS a result.** A card reporting no issues satisfies the
must-always-provide-a-result rule and is not a defect on its own. A detector that flags it as
non-participation would flag a legitimate outcome.

There are two real defects, and the second is sharper and cheaper than the first.

**1. The deficit is comparative.** Producing structurally fewer findings than the other reviewers *on
the same diff* is a bug in itself, even though each individual "no findings" result is legitimate.
Measured across five PRs:

| PR | Reviewer B | Reviewer C | Required reviewer | Verdict |
|---|---|---|---|---|
| A | **4 findings** | rate-limited | 0 | ⛔ deficit 4 : 0 |
| B | **2 findings**, one Major | rate-limited | 0 | ⛔ deficit 2 : 0 |
| C | rate-limited | rate-limited | 0 | no baseline — **not assessable** |
| D | rate-limited | rate-limited | 0 | no baseline — **not assessable** |
| E | reviewed, **0 findings** | rate-limited | 0 | ✅ clean 0 : 0, with a real baseline |

⭐ Row B is the sharpest: the required reviewer positively asserted *"No major issues detected"* on a
diff where another reviewer posted a finding it classified **Major** — a direct contradiction of a
specific claim on the same input, not a difference of threshold. ⭐ Row E is the necessary
counter-example: **the detector must not fire there.** Two deficits, one corroborated clean, two
unassessable — a detector that scores four of five as bad is wrong.

⚠ **The deficit is only assessable against a baseline.** When every other reviewer refused, nothing
reviewed the diff besides the required bot, and the run is evidence **neither way**.

**2. Our own rendering collapses the distinction — and this is the title condition, located in our
code rather than in the reviewer's output.** On a run where **no reviewer produced any content**, the
step recorded `outcome: done` and
`display_detail: "0 comment(s) found (unified triage pending)"` — **textually identical to what a
clean 27-file review produces.** That string is what a later reader, a PR body, and a status render
actually see. The only artefact stating the truth was a warning line in the work log — *"Zero
actionable comments here means NO REVIEWER PRODUCED CONTENT, not that the diff is clean"* — written by
the run's own judgement, produced by no gate, reaching no field.

⭐ **The taxonomy already exists** (the refusal states are split by a registry `rate_limit_class`); it
simply never reaches the field a reader sees. This is plumbing, not design.

## Goal

A reader can tell *reviewed-and-clean* from *nobody-reviewed* from every surface that reports a review,
and a required reviewer that under-produces against a real baseline is reported as a reviewer-quality
bug — without that report touching any merge verdict.

## Deliverables

Five. ⛔ At the split threshold: if D1's derivation widens the change materially, **split rather than
absorbing.**

1. **D0 — GATE, mutates nothing: the counting rule, stated as a reusable contract.** Per PR, derive
   each reviewer's finding count and whether it **reviewed at all**.
   ⭐⭐ **This rule is the epic's single source of truth, and two other staged plans consume it.** State
   it as a contract — the counting rule, the reviewed-at-all predicate, and the required-vs-optional
   denominator, each named, each with its population published — not as an internal step. If another
   plan lands the rule first, **consume it rather than restating it**; the ownership is on the rule,
   not on this plan.
   ⚠ **Counting is the whole difficulty.** One reviewer's four findings arrived across two review
   bodies ("Actionable comments posted: 3", then "1"), and its inline threads carry its own
   acknowledgement replies. **A naive comment count is wrong in both directions.** State the rule
   explicitly.
   ⛔ **Partition the absence corpus by CAUSE before computing any rate.** The corpus blends at least
   two mechanisms with different remedies — a **quota** refusal needs retry or backoff, a **diff-size**
   refusal needs a smaller diff. A per-reviewer participation rate computed across the pooled corpus
   **mis-attributes both**. Diff sizes are recoverable from merge commits, so this is cheaply
   derivable. ⛔ **Do not report a participation rate until the partition exists.**
   ⛔ **This deliverable HALTS the plan** if the partition cannot be derived from the tree and git.
   *Done when:* the contract is written with each population published, and the absence corpus is
   partitioned by cause.

2. **D1 — the reviewer-state vocabulary, agreed once.** Adopt **`reviewed-clean` ·
   `reviewed-with-findings` · `did-not-review`**, extended by the refusal *reason*, because
   `did-not-review` is too coarse — the reason is the actionable part. The vocabulary must carry these
   states as distinct members, each of which has been observed and each of which scores differently:
   - `participated_but_empty` — looked, found nothing. **A successful review with a count of zero**;
     must never collapse into "did not review".
   - `refused` by **quota** versus by **diff size** — the second is the only *deterministic* axis of
     the five known false-green axes (rate-limit, wrong-HEAD, force-push, never-ran, diff-size), which
     makes it the one a plan can predict at outline rather than merely detect afterwards.
   - `not-invited` — never asked. ⛔ Distinct from both `refused` and `absent`; **scoring it as either
     corrupts the rate in opposite directions**, and it is the state most likely to be *ours* rather
     than the bot's, so it is the one with an actionable remedy.
   - `unknown` — the registry declares ignorance. ⛔ Today a binary `== 'awaitable_window'` test over a
     **three-valued** field collapses `unknown` into the hard-refusal branch, so an operator is shown
     *"refused_hard (hard quota)"* for a bot whose registry says *we do not know*. **A declared unknown
     rendered as a positive finding** steers an operator toward "waiting is futile, force it" when
     waiting might have worked.
   ⚠ **This vocabulary spans another staged plan in this epic. Agree it once and use it in both** — two
   plans inventing two vocabularies for one distinction is the duplication this epic exists to fix.
   *Done when:* one vocabulary is defined in one place, and every consumer named in D2/D3 uses it.

3. **D2 — the deficit signal, computed only when a baseline exists.** A required reviewer returning
   materially fewer findings than a reviewer that actually reviewed the same diff is reported.
   ⛔ **It must not fire when every other reviewer refused, and must not fire on `0 : 0`.**
   ⛔ **The signal names what it is: a bug report about the reviewer.** Not a merge verdict and not a
   participation verdict — the reviewer *did* provide a result, so participation and the merge decision
   are unaffected. **Do not gate the merge on this**; it is an observability signal about reviewer
   quality, and turning it into a gate would block merges on a third party's output.
   ⚠ **Do not pool measurements across the instruction-generation boundary.** A recent landing changed
   the reviewer's *instructions* (domain-scoped charter packs, and an agent-instructions file reaching
   two repositories where it previously did not resolve at all). Every row in the table above predates
   it. A deficit measured before and one measured after are **not the same quantity**. D0 must
   establish, per PR in the corpus, which charter the reviewer was running.
   *Done when:* the signal fires on the two deficit rows, stays silent on the clean row, and reports
   the two baseline-less rows as unassessable.

4. **D3 — `display_detail` carries the reviewer-state distribution, not just a comment count.**
   `"0 comment(s) found"` and `"0 comment(s) found — 1 empty, 2 refused, 0 proven"` are different facts
   and must not share a rendering. ⭐ **Cheapest real improvement in the epic** — the states already
   exist; they do not reach the field.
   Extend to the review-retrospective surface, which has the same blind spot from the other direction:
   it represents *"produced no comments"* and *"never ran"* identically **by having no row**, and has
   no representation for *"enabled, invoked, and refused"*. ⭐ **Emit a row per ENABLED reviewer, not
   per RESPONDING reviewer.** ⛔ Deriving rows from the responding set makes the detector's population a
   strict subset of its own domain — the vacuous-set archetype in a new place.
   ⚠ Confirm at D0 whether one vocabulary change serves both surfaces; **if it splits the change
   materially, split the plan.**
   *Done when:* no surface renders "nobody reviewed" and "reviewed clean" as the same string, proven by
   a test per surface.

5. **D4 — tests, each verified to FAIL pre-fix**, using the real corpus shapes: (a) the two deficit
   rows report a deficit; (b) the `0 : 0`-with-a-real-baseline row does **not**; (c) the two
   baseline-less rows are reported **unassessable** — not clean and not deficits.
   ⛔ **(b) and (c) are load-bearing.** A detector that fires on them is worse than no detector, because
   it manufactures reviewer-quality bugs out of rate limiting we already accept as normal.
   *Done when:* all five behave as specified, each proven to fail before the change.

## Out of scope

- **Judging whether a reviewer's prose is "substantive".** The operator ruling stands: *"no findings"
  is a result.* A detector that starts scoring prose quality contradicts it; a detector that counts
  findings against a baseline does not.
- **Reassigning which reviewer is `required` based on measured yield.** Recorded as an open question,
  deliberately not built: D2 already forbids this signal from moving a merge verdict, and reassigning
  `required` would do exactly that.
- **Scoring finding correctness.** One observed reviewer raised two focus areas that were **both
  refuted against live code** — one would have turned a documented fail-safe into a fail-quiet clean
  verdict if applied. ⇒ *"Participated"* and *"produced value"* are different predicates and only the
  first is measurable here. Report counts and their dispositions separately; correctness needs a human
  verdict per finding and is not automatable in this plan.
- **Splitting large PRs to stay under a reviewer's size limit.** A plan-shape change with its own
  costs, explicitly declined.
- **Re-opening the which-kind-of-zero discriminator shipped elsewhere.** Reuse the shape; do not redo
  the work.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the
  binary-over-three-valued `rate_limit_class` test and the state constants.
- `marketplace/bundles/plan-marshall/skills/automatic-review/` — the `display_detail` composition site.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/` — the per-bot registry
  documents carrying `rate_limit_class` and any declared size limits.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the
  refusal pre-filter in `fetch_findings`.
- The review-retrospective finalize step — the per-reviewer row emission.
- The matching `test/plan-marshall/...` trees.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `display_detail` renders "no reviewer produced content" identically to a clean review | OBSERVED | The `display_detail` composition site in `automatic-review` — read what it interpolates |
| The refusal taxonomy exists but does not reach `display_detail` | OBSERVED | The state constants in `review_completeness.py` versus the fields the step emits |
| A binary `== 'awaitable_window'` test collapses a three-valued `rate_limit_class` | OBSERVED | The comparison in `review_completeness.py` and the three registry documents that declare the field |
| All three registry documents now declare `rate_limit_class` (an earlier claim that only one did is **refuted**) | OBSERVED | The three per-bot standards documents. ⛔ Do not carry the older wording forward |
| The refusal pre-filter leaks **within a single bot** — three sibling refusal bodies filtered, a fourth stored as a pending finding | OBSERVED | The refusal predicate in `fetch_findings`: it enumerates known refusal shapes rather than positively testing what a review body must contain |
| The review-retrospective surface has no row for "enabled, invoked, refused" | OBSERVED | The row-emission site — check whether it iterates the enabled set or the responding set |
| A diff-size refusal threshold of 150,000 characters | HYPOTHESIS | Reported by the run that hit it — **first-party to that run, second-hand here.** ⛔ **Re-derive before pinning a test to the number** |
| One vocabulary change serves both the participation classifier and the retrospective surface | HYPOTHESIS | Read both consumers at D0. If it splits the change materially, split the plan |
| The share of past absences that were **size** rather than **quota** | UNDERIVED | D0's partition produces it. ⛔ Do not state a rate before then |

⚠ **Every count in this plan is a lead**: five PRs, four findings, three recurrences, 150,000
characters. **Re-derive anything you assert.** The corpus rows describe past runs, not the tree you
clone.

⛔ **Do not go looking for `.plan/`.** The per-run finding analyses, inbox messages, and landing records
behind this plan are git-ignored and **absent from your clone**. Everything needed is restated here.

## Verification

- Full verify; read the payload's `status` / `errors[]` rather than the exit code.
- **Every D4 case proven to fail pre-fix.** The two negative cases (b) and (c) matter most: confirm
  that a naive detector *does* fire on them today, so the test is discriminating rather than decorative.
- **Publish each population size** the rule computes over, in the artifact itself. A rate whose
  denominator is invisible is the defect this plan is about.
- ⭐ **Cold read, aimed at the rendered strings.** D3 changes what a reader is told. Have the pre-PR
  verification sub-agent read the new `display_detail` outputs **cold** — without this plan — for two
  scenarios (nobody reviewed; one reviewer reviewed and found nothing) and report **what it concludes
  about whether the diff was reviewed** in each. If the two readings are the same, D3 failed however
  different the strings look.
- ⭐ Also cold-read D2's deficit report and ask: *does this block a merge?* The intended answer is **no**
  — it is a reviewer-quality signal. If the cold reading treats it as a gate, the wording failed.

## Notes

- **A generalised rule already in the corpus — reuse it, do not re-derive.** *"A fail-closed consumer
  folded a dispatched producer's ERROR payload into an observed clean verdict (zero findings) — a false
  green inside a fail-closed feature, because it did not branch on producer status before folding the
  payload."* ⇒ **Branch on producer STATUS before folding its payload.** Same defect, different
  producer.
- **The artifact that looks like participation is the one that proves the review did not happen.** A
  persistent summary card and a trigger acknowledgement (*"Review finished. Note: … incremental review
  system…"*) both consumed a triage decision to conclude there was nothing to decide — and in one case
  that acknowledgement was the **only** record the reviewer produced at the final HEAD. ⛔ **Coordinate
  this discriminator with the currency plan in this epic; do not ship two.** ⚠ This does not conflict
  with the operator ruling: a contentless card should not consume a triage decision and its presence
  must not be read as review evidence — neither of which is a judgement about prose quality.
- **A cheap acceptance signal already collected.** When a `pr-comment` finding recurrently resolves as
  `taken_into_account` rather than being actioned, suspect the **producer**, not the triage: several
  recurring comment classes are not reviewer feedback at all (a refusal notice, an "already reviewed"
  status reply, the plan's own PR-body supplement). One plan saw that tuple three times, and **all
  three were non-feedback classes**. ⇒ Use the `taken_into_account` share as the acceptance metric
  rather than inventing a new one.
- **Candidate remedy for the pre-filter, not yet applied:** restate it **positively** — a stored
  `pr-comment` finding must positively look like review feedback, rather than merely not matching a
  list of known refusal phrasings. The same enumeration-versus-positive-validation defect was raised
  independently against another file in the same run.
- **An owed architecture insight this plan should record** (the prior filer could not, for a
  push-path reason that does not apply here): *a review bot's persistent summary card and its trigger
  acknowledgement are participation artifacts, not diff-derived claims — dispose of them as accepted
  without opening a fix task, and never read their presence as evidence the bot reviewed the current
  HEAD; check for a review object stamped with the live reviewed-commit SHA instead.*
- **Sequencing.** Shares `review_completeness.py` and `github_pr.py` with other staged plans in this
  epic. Sequence, never pair. The pre/post instruction-boundary measurement is **the same question
  another staged plan asks by re-review — coordinate, do not run two independent measurements of one
  effect.**
