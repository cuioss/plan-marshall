envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=candidate-lesson
created=2026-09-08T12:41:20Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=remediate-user-facing-sites

# Re-review the whole edited passage after a self-review fix, not only the flagged line

## Context

This plan took six finalize loop-back iterations against a ceiling of 17. Four of the six were
self-seeded: the prose a fix round wrote was itself the defect the next round caught. Three of those
four landed in the same passage, and the sequence is worth reading in order because it is the whole
argument:

1. Round 1 corrected a dependency instruction.
2. Round 2 found that the corrected instruction had no dependant-discovery step, and added one.
3. Round 3 found that the sibling option described in the same passage had never received the
   update command the first two rounds established.

Each round fixed what it was shown and shipped. Each round left the rest of the passage in a state
its own edit had made inconsistent. Nothing in the loop asked "what else in this passage does my
change now contradict?"

The cost is measurable and large: `6-finalize` consumed 4,964,821 tokens, 59% of an 8,481,783-token
plan, against a `multi_module + bug_fix` anchor whose error column is 2.0M. This is the single
largest efficiency lever the plan exposes, and it is a review-loop cost rather than an
implementation cost — the implementation phases together spent 1.9M.

The honest alternative reading is that the passage was simply dense, and three rounds is what dense
prose costs. That reading is worth testing rather than assuming: if the loop already re-reads whole
passages and still took three rounds, the fix is elsewhere.

## Root cause

The self-review fix loop is scoped to the finding, and a finding names a line. A prose edit's blast
radius is the passage, because prose carries cross-references, sibling options and worked examples
that a single-line view does not show. The loop's scope and the change's blast radius disagree.

## Proposed action

After applying a self-review fix to a prose file, re-examine the enclosing section rather than the
changed line — specifically the sibling options, the cross-references, and the worked examples that
share the section with the edit. Then measure: record whether a plan's self-seeded loop-back count
falls. If it does not, the density reading was right and the lever is somewhere else.

## Evidence

- aspect: plan_efficiency — `[BUDGET]` error against the `multi_module + bug_fix` anchor:
  8,481,783 tokens against an error column of 2.0M, and 295.4 worked minutes against an error
  column of 150. `max_phase_token_share = 0.59`, dominant phase `6-finalize=4964821`.
- aspect: logging_gap_analysis — the finalize dispatch ledger records 7 `returned_with_findings`
  rows of 26, each a productive loop-back; `pre-submission-self-review` fired 7 times and
  `automatic-review` 5 times.
- aspect: chat_history_analysis — none of the six loop-backs reached the conversation. The operator
  saw only a stalled orchestrator and asked "why did you stop?".
