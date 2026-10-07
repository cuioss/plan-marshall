envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:21Z

# Candidate lesson: the roles table defined the verifier without the obligation just added to it

- source_signal: qgate / 6-finalize
- record_id: 0131de
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:76
- resolution: fixed in the round-5 sweep (a self-seeding round) by deletion/pointer

## What happened

The Verifier row of the roles table still defined the role as accepts-or-refuses only, omitting the stop question the same change had just made part of the role. This was one of four same-document contradictions found in a single round — all of them introduced or left by the immediately preceding round's fix.

## Candidate rule

Self-seeding: a round that fixes a contradiction by RESTATING the corrected rule in a second place manufactures the next round's finding. The terminating move is to replace the restatement with a pointer at its source. Definition tables are a high-frequency restatement site — when a role's obligations change, the table row is part of the change, and the durable form is a pointer rather than a second definition.
