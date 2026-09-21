envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:08:21Z

component=plan-marshall:phase-6-finalize
category=improvement
disposition=reinforcement
related_lesson=2026-08-27-16-004
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369

# Five internal self-review passes reported the diff clean; an external reviewer then found 31.3% of the total defect set

## The measurement

`pre-submission-self-review` ran **five passes** on this plan (2 full-surface, 3 delta) across
**3 loop-back iterations of a ceiling of 5**. It surfaced **11 findings**, resolved all of them
(8 fixed, 3 taken_into_account), and closed with the diff reported clean. The gates agreed:
`pre-push-quality-gate` green, `project:finalize-step-plugin-doctor` green, `ci-verify` all checks green.

CodeRabbit then found **five more** on the same tree. Every one was real. Four were fixed; the
fifth was an instrument artefact (see the caveat below).

| Population | Count | Share of total discovered |
|---|---|---|
| Internal (`pre-submission-self-review`, 5 passes) | 11 | 68.8% |
| External (CodeRabbit, post-gate) | 5 | **31.3%** |
| Total discovered defect set | 16 | 100% |

**Caveat, stated because the number is the point.** One of the five (`0e5217`) is a contentless
run summary admitted to the actionable set by the empty-`body` defect this same plan filed as
`5c47c6`. Excluding it gives **4 of 15 = 26.7%**. The honest range is therefore **a quarter to a
third**, and the headline figure is itself slightly inflated by an instrument defect the plan
discovered — which is exactly the kind of contamination that makes a single-number recall claim
untrustworthy without its denominator.

## Why this is a recall datum and not an anecdote

The two populations are disjoint by construction: the external review ran against a tree the
internal review had already declared clean, at a `gate_head_sha` the gates had passed
(`fcab7d1c`). There is no double-counting and no ordering ambiguity. This is a genuine
false-negative rate for the internal pass on one plan.

Two of the five external findings were the **vacuous-guard** archetype, and one of those
(`e40f03`) was *introduced by the fix for another* (`d10934`) — see the sibling proposal L2. So
internal review did not merely miss pre-existing defects; it also failed to catch defects its own
remediation created, within the same run.

## What it implies about relying on internal review

State it plainly: **`pre-submission-self-review` at five passes is not a substitute for external
review, and should not be treated as one.** On this plan it caught roughly two-thirds of the
discoverable defect set and reported the remaining third as clean. Its output is a floor on the
defect count, never a verdict on the absence of defects.

Two consequences follow, and both are decisions for the epic rather than claims:

1. **A clean self-review must not be able to authorise a merge on its own.** On this plan it very
   nearly did — the required-bot quorum passed on a contentless pr-agent Guide while both
   substantive reviewers had declined (finding `7bbc84`), and only an operator condition
   ("was there at least one CodeRabbit review? if yes, proceed") held the merge.
2. **Diminishing returns are visible within the pass itself.** Five passes produced 11 findings;
   passes 3, 4 and 5 produced 1, 4 and 1 respectively, and pass 3's single finding was an
   incomplete-deletion residue of pass 2's own edit. The marginal pass is largely re-reading the
   run's own prose. Budget spent on a sixth internal pass would plausibly buy less than budget
   spent on making one external review reliably arrive.

## Relationship to lesson 2026-08-27-16-004

`2026-08-27-16-004` ("12 of 19 bot findings are one archetype the in-house self-review had already
passed") records the same failure from the *archetype* angle on a different plan. This is a second,
independent measurement of the same phenomenon from the *recall* angle. Treat it as reinforcement:
two plans, two measurement methods, the same conclusion — the in-house pass systematically misses
a substantial, non-random fraction, concentrated in the vacuous-guard family.
