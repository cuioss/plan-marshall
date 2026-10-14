# In-house reviewer efficacy — measurement result

Measure-first investigation: does the in-house reviewer (`cuioss-review-bot`,
a required reviewer on every merge) find anything under its assembled charter,
and should it stay required? This document is the **durable reasoning** the
repeat measurement supports. The dated tables behind it — per-side corpus
counts, the fixed-diff experiment rows, the appendix — live with the plan's PR
description and inbox message, not here, following the precedent of
`uncompressed-output-measurement.md`: snapshot absolutes belong to the window
they were read in, while what this project acts on must hold across windows.

## Question

Whether the reviewer change from a central charter to a run-time assembled
charter (a spine plus per-domain packs each repository opts into) changed what
the reviewer finds, and whether the measured yield keeps it as a required
reviewer while thirteen more repositories wait to be enrolled.

## Method

Two instruments, each answering the part the other cannot:

- **Repeat corpus pass (PLAN-LB-21 D1).** Every pull request opened after the
  previous pass's successor stamp, in every repository the last pass covered
  plus every repository enrolled since, split per repository at the instant
  its `cuioss-review-bot` block with `enabled: true` reached the default
  branch: before (central charter) versus after (assembled charter).
  `skip-bot-review`-labelled and Dependabot pull requests are excluded and
  counted, as before. Each side reports reviews posted; canned versus
  substantive, classified by structural rule (guide-only table versus
  focus-areas section, populated security cell, or reviewer inline findings)
  and cross-checked by body length; populated security cells; `/improve`
  outputs; paired recall against CodeRabbit on pull requests where CodeRabbit
  posted inline findings; and the four-outcome score. A reviewer run is looked
  up unfiltered by branch; a run that never started, a run whose review job
  was skipped or failed, and a diff no other reviewer covered are kept apart
  in every table. The classifier was hand-checked on a seeded random sample of
  30 reviews with full agreement; repositories with fewer than 20 reviews on a
  side are reported as coverage only, with no quality claim.
- **Fixed-diff experiment (PLAN-LB-21 D2).** The corpus compares different
  diffs under different configurations, so it cannot show what the charter
  change did. A fixed set of already-merged pull requests on which another
  reviewer found a Major defect and the bot's review was canned was re-run
  with one `/review` each; each run is scored against the known defect and
  carries the charter line observed in the reviewer log, so the configuration
  under test is observed, not assumed.

To re-run: use the approved read-only instrument — the `gh`-based pass whose
scripts live beside the plan's temp state (`task1_pop.py` for the
window/charter-split/exclusion pass, `task1_fetch.py` for the read-only
comment and run reads, `task1_classify.py`/`task1_final3.py` for the
structural classification with its run-established cause sets) — over pull
requests opened after this pass's upper-bound instant (stated in the PR
description), drawing a fresh seeded hand-check sample rather than reusing
seed 20261013.

## What the evidence supports

- **The summary surface under-reports the review, under both charters.** On
  nineteen pull requests the guide table claims "No major issues detected"
  while the same run's inline comments carry concrete findings with code
  suggestions. The guide table is therefore not a reliable record of whether
  the reviewer found anything; any yield count taken from guide bodies alone
  understates the review. This holds on every repository with an assembled
  charter and on the central-charter side alike, so it is a property of the
  reporting surface, not of either charter.
- **The dominant reason a pull request gets no review is the review job
  being skipped, not the reviewer finding nothing.** Across the whole
  population, the review job was skipped on more than a hundred candidate
  pull requests and failed on twenty, against about two hundred posted
  reviews. A skipped run is triage, not a verdict: those diffs were never
  examined. Yield ratios computed over posted reviews only describe the
  attempted share.
- **The fixed diffs stayed canned under the assembled charter.** All eight
  experiment runs triggered, all eight posted the canned table, each carrying
  the observed assembled-charter log line with the confirmed packs. On
  diffs with known Major defects — including a security Major — the charter
  change did not convert a single canned review into a found one. Because
  only this instrument holds the diff fixed, it is the one that speaks to
  what the charter change did.
- **The populated security cell is a rarity, not a practice.** One review in
  the whole pass carries a populated security cell (an open-redirect finding
  the other reviewer corroborated in the same defect area). The security row
  is otherwise always the stock "no concerns" line.
- **`/improve` produced nothing this window.** Every successful `/improve`
  generation reports no suggestions found; zero suggestions were posted
  anywhere in the population. Observed generation failures are unsuccessful
  measurements and are excluded from that claim. The one surface that
  produced suggestions in the last measurement produced none in this one.

Per-claim populations, in words: the reporting-gap claim rests on every
repository with posted reviews on either side; the skip-dominance claim rests
on the full candidate population across all eight repositories; the
fixed-diff claim rests on the eight experiment pull requests, four from the
ledger set and four drawn by the same criterion; the paired-recall figures
rest on pull requests where CodeRabbit posted inline findings, and no recall
figure is claimed for any repository side with fewer than twenty posted bot
reviews.

## What the evidence does NOT support

- **That the assembled charter is worse (or better) than the central one.**
  The corpus sides differ in diffs, and the model ladder may have moved; the
  last pass already recorded a before/after drop it could not attribute. Only
  the fixed-diff experiment holds the diff fixed, and it shows no conversion
  in either direction on its eight diffs — which does not generalise to the
  fleet.
- **That the reviewer finds nothing anywhere.** Nineteen substantive reviews
  with concrete suggestions, one corroborated security finding, and paired
  recall in the low single digits per side on the two repositories with a
  quality claim are a thin yield, not a zero. "Drop the reviewer" does not
  follow from this measurement any more than it followed from the last one.
- **Any quality claim for the quiet repositories.** TokenSheriff, cui-http,
  the module template, cui-open-rewrite, playwright-test-artifacts, and the
  post-change side of API-Sheriff have too few posted reviews for a yield
  figure; they are reported as coverage only. The after-change evidence is in
  effect this repository's and plan-marshall-mcp's.
- **That a canned guide means CodeRabbit agreed.** The deficit rows — a
  canned bot review where CodeRabbit posted findings — are flagged by rule;
  only the seeded sample and the same-file overlap check adjudicate them.
  Unadjudicated deficit rows are not corroboration of anything.

## Decision (operator)

Operator answer, recorded in the plan decision log: **keep
`cuioss-review-bot` required as is** — the first of the five options the
measurement was put to the operator with (keep required as is; make optional;
keep required only above a stated yield bar; make `/improve` the default;
stop running it). No roster change follows: `required_bots` stays
`cuioss-review-bot,coderabbit` and `optional_bots` stays `sourcery` for
`plan-marshall:automatic-review`, so `.plan/marshal.json` and the roster
contract tests are untouched by this decision.

The standing decision this touches — CodeRabbit stays required until the
in-house reviewer reaches similar quality, reopened only when measured so by
the existing comparison protocol — stands unchanged: this measurement does
not meet the reopen condition. Paired recall against CodeRabbit stays in the
low single digits per side on the two repositories with a quality claim, and
the fixed-diff experiment converted none of its eight canned reviews into a
found one.

Consumer repositories: the answer implies a roster change in no consumer
repository, so none is listed for editing — the enrolled repositories and the
thirteen deferred ones keep their current rosters. The rollout plan requires
the decision and released schema before enrolment; this repository has no
consumer-enrolment guard that enforces that condition. The
dated line goes to the plan PR description; the inbox message tells PLAN-LB-20
in one line whether to proceed with enrolment.
