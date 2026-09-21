envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:02Z

# Candidate lesson: a carried claim was STALE and re-applying its fix would have created the drift

- source_signal: qgate / 5-execute (D1 gate verdict)
- record_id: 6df41e
- component: plan-marshall:phase-6-finalize
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md
- resolution: taken_into_account — verdict recorded, NO source edit, and that was the COMPLETE outcome

## What happened

The deliverable carried a claim that `push.md` and `lessons-capture.md` disagreed about whether lessons-capture mutates source. Both read at HEAD: `lessons-capture.md` declares `mutates_source: false`, and `push.md`'s single mention says exactly that. They AGREE. The contingency edit path was not triggered.

## Candidate rule

Re-ground every carried claim at HEAD before acting on it. And when the claim is stale, closing with no edit is a COMPLETE outcome, not a skipped one — re-applying a fix to an already-correct document is precisely how a second, drifting statement of the same fact gets introduced.
