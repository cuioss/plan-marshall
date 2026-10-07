envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:37Z

# Candidate lesson: a fact pair was wired unconditionally onto branches that had no answer to report

- source_signal: qgate / 6-finalize
- record_id: 3c7240
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:537
- resolution: fixed in the round-8 sweep — the fact pair was made conditional, mirroring the existing `--head-at-completion` omission rule

## What happened

The round-6 fix that wired `--fact acceptance` / `--fact may_close` onto `mark-step-done` applied it to ALL FOUR branch blocks — including the zero-generator fallback and the `verifier_unavailable` Branch B state, neither of which has a verifier answer. Those branches would have reported a verifier answer they never received.

## Candidate rule

When adding an evidence field to a step record, enumerate the branches that CAN produce the evidence before wiring it. A field wired on a branch that cannot populate it produces a fabricated fact — the same failure the field was added to prevent, pointed the other way. The project already had the pattern to copy: the `head-at-completion` omission rule.
