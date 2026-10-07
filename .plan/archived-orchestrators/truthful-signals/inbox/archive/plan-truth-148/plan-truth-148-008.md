envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:59:07Z

# Candidate lesson: a self-review round adjudicated its own blocking premise as REFUTED

- source_signal: qgate / 6-finalize
- record_id: 20faec
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:78
- resolution: rejected (premise refuted in round 2; rounds 3-10 ran the verifier successfully)

## What happened

Round 1 of pre-submission-self-review filed a blocking contract_drift finding asserting that the new Step 3b verifier was structurally unreachable, reasoning from `dispatch-inline-split.md` line 19 classifying `default:pre-submission-self-review` under "Dispatched steps" and therefore concluding the WHOLE step body runs inside a leaf. The premise was false: the same document places Step 1 and Step 4 inline in the dispatcher context, so Step 3b is reachable from there. Eight further loop-back rounds were spent before the contradiction was adjudicated and the finding rejected.

## Candidate rule

A roster entry that classifies a STEP as "dispatched" does not classify every STEP OF THE BODY as dispatched. Before filing a finding that a dispatch is structurally impossible, read the same document's own per-step placement statements; a roster label is a coarse classification, not a per-sub-step claim. The empirical check is cheap: a context that already issues one dispatch can issue a second.
