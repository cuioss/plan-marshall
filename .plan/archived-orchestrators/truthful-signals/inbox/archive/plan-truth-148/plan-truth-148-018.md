envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:27Z

# Candidate lesson: a branch-parity invariant asserted parity on the wrong field set

- source_signal: qgate / 6-finalize
- record_id: 1ef125
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:209
- resolution: fixed in the round-5 self-seeding sweep

## What happened

The Step 1b branch-parity invariant said "Step 4 reads the same acceptance either way", asserting parity over `acceptance` only while Branch A actually gates on acceptance AND `may_close`. The invariant was therefore true of a strict subset of what the branch consumes — a guard that holds while the property it is supposed to protect can still break.

## Candidate rule

A parity/equivalence invariant must quantify over the FULL set the consumer reads, derived from the consumer's own precondition. An invariant stated over a subset passes while the real divergence goes unguarded.
