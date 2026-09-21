envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:37Z

# Candidate lesson: a done record was indistinguishable from one that skipped the gate

- source_signal: qgate / 6-finalize
- record_id: 7e4a3d
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:520
- resolution: fixed in the round-6 sweep — `records_facts` declared, acceptance/may_close wired onto mark-step-done

## What happened

Step 3b's verifier acceptance and `may_close` answers were recorded only in the decision log: no `--fact` carried them onto the step record and no `records_facts` frontmatter declared them. A `done` record therefore looked identical whether the verifier gate ran and passed or was skipped entirely.

## Candidate rule

When a step adds a gate that decides its own close, the gate's ANSWER must reach the step record, not only the log. Otherwise the record asserts a close without carrying the evidence for it, and any downstream consumer reading `outcome=done` is reading an unfalsifiable claim.
