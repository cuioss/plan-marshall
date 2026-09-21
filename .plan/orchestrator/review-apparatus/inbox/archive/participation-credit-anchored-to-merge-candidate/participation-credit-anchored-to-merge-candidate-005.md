envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:18:50Z

component=plan-marshall:automatic-review
category=improvement
confidence=high
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# The in-house self-review gate outscored the entire external bot set 5-0 on one diff

## Context

This is the strongest reviewer-comparison datapoint the epic has produced, because both
sides reviewed the same diff at the same time and the outcome is unambiguous.

`pre-submission-self-review` fired twice. Its **first** firing recorded
`outcome: failed` with five real contract-drift defects in the plan's own diff
(`789b6d`, `020f5f`, `906944`, `65cb67`, `5de248`). The second firing, after the fixes,
recorded `outcome: done` with `"self-review clean: 61 candidates examined, no check
matched"` — note that it names its examined population, so the clean result is a scanned
zero rather than an unexamined one.

The external reviewer set contributed **zero** actionable findings on the same diff. The
`automatic-review` step recorded
`"0 comments - 1 empty, 1 refused, 1 refused-structural (triage pending)"`, and the
project's own review-retrospective step recorded
`"clean grade but 0/3 reviewers measurable; self-review 5 defects, bots 0"`.

So of three configured reviewers: one returned empty, one refused, one refused for
structural reasons (the diff exceeding a declared ceiling). None of the three produced a
measurable review. The PR merged with a green `merge_state` and green CI while nothing
external had actually reviewed the merge candidate.

The single most interesting defect is `906944`. The plan added a paragraph routing on
`merge_candidate_sha_resolved` without adding that field to the merge barrier's
required-input enumeration — so a truncated return that dropped the flag would have
satisfied the enumeration and proceeded. That hole sits eleven lines above prose in the
same document arguing exactly this case for `unrecognised_refusal`. A reviewer had to
hold the enumeration and the prose it contradicts in view simultaneously to see it.
That is precisely the class of defect a diff-local external reviewer is structurally
unable to find, and precisely what the in-house structural gate is for.

## Root cause

Two separate things are true and should not be conflated:

1. The in-house gate is finding a class of defect — same-document contract drift,
   enumeration-vs-prose divergence, absent-is-not-false holes — that the external bots
   do not find and arguably cannot, because the evidence spans a document rather than a
   hunk.
2. The external bots produced nothing here for reasons that are mostly *not* about
   quality: one empty, one refused, one refused-structural. A refusal is not a clean
   review, and a structural refusal on diff size cannot be cleared by re-requesting.

Reading (2) as evidence about reviewer quality would be a mistake — the population of
measurable external reviews on this PR is zero, so no quality claim about the bots is
supportable from it either way. What IS supportable is that the merge barrier let a PR
through with zero measurable external participation, and that the in-house gate was the
only thing that examined the diff.

## Proposed action

1. **Weight the in-house gate accordingly.** `pre-submission-self-review` is currently
   one step among many; on this evidence it is the highest-yield reviewer in the set.
   Consider whether its firing is unconditional and whether its candidate population
   (61 here) is wide enough.
2. **Do not spend another round on bot charter exhortation.** The failure here is
   empty/refused/refused-structural, not weak findings — a charter change addresses
   none of the three.
3. **Treat `refused_structural` as a coverage gap the merge barrier reports, not a
   silence.** The barrier already models this; the datapoint to carry forward is that
   all three reviewers were unmeasurable simultaneously and the merge still proceeded.
4. **Record the enumeration-vs-prose defect class explicitly** as something the
   self-review checks for, since `906944` is its cleanest instance to date.

## Evidence

- artifact: `status.json` — `pre-submission-self-review` `firing_count: 2`,
  `prior_firings: [failed]`, final `"self-review clean: 61 candidates examined, no
  check matched"`.
- artifact: `status.json` — `automatic-review`
  `"0 comments - 1 empty, 1 refused, 1 refused-structural (triage pending)"`.
- artifact: `status.json` — `project:finalize-step-review-retrospective`
  `"clean grade but 0/3 reviewers measurable; self-review 5 defects, bots 0"`.
- artifact: `review-retrospective.md` in the plan directory.
- defect ids: 789b6d, 020f5f, 906944, 65cb67, 5de248.
