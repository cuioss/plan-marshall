envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:42:21Z

# Derive self-review cohort_size from a class-closure sweep, not from the candidate list

component: pm-plugin-development:ext-self-review-plan-marshall
category: bug
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356

## Context

`pre-submission-self-review` fired 12 times across this finalize. Nine of its ten
recorded Q-Gate findings carried the marker
`[defect_class {X}: 1 finding(s) in this class this round]`; the tenth carried 2.
Three consecutive rounds each found exactly ONE member of the same
`contract_drift` class and reported cohort_size 1. A directed exhaustive
class-closure sweep, run only after a human noticed the pattern, then found FOUR
members of that class at once — and those four are 14 of the 17 scope-creep files
in this plan's shipped footprint.

## Root cause

`cohort_size` counts how many members of the class appeared in **this round's
candidate list**. It is published under a name, and in a sentence, that reads as a
property of the tree. A per-round cohort of 1 is therefore indistinguishable from
a genuinely singular class, so each round closed one member, reported the class
closed, and re-opened on the next round when the surfacer's candidate list
happened to include a different member.

## Proposed action

After a finding is assigned a `defect_class`, run a class-closure pass:
`architecture search --content` for the matched signature across the inventory,
and report `cohort_size` as the size of that derived population, with the
candidate-list hit count reported separately. A count that can be 1 because the
sampler only looked at one file must publish the population it was computed over —
this is the population-derived-detector rule applied to the review instrument
itself.

## Evidence

- aspect: logging_gap_analysis — 12 firings of `pre-submission-self-review`, 5 with outcome `failed`
- aspect: llm_to_script_opportunities — candidate 1, repetition_count 10
- Q-Gate findings ced26f, 380282, aa1040, 9dae3f, be6078 — all `contract_drift`, each reporting 1
- Q-Gate finding eadf9e — records the recurrence in its own resolution text
- aspect: request_result_alignment — 14 of 17 scope-creep paths are the class-closure sweep
