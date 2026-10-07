envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:59:18Z

# Candidate lesson: a retirement sweep covered two documents and left two standing in the same skill

- source_signal: qgate / 6-finalize
- record_id: 6e945f
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md:428
- resolution: fixed, but re-verification found it HALF applied; remaining half allocated as TASK-021

## What happened

The sweep retiring the `validation` finalize step removed it from `output-template.md` and `ci-verify.md` but left it in `required-steps.md` (the canonical list the `phase_steps_complete` handshake enforces) and in `SKILL.md`'s worked-example output. Before the change all four agreed; after it they did not.

Sharper still: the FIX for this finding was itself only half applied. Re-verification at a later HEAD found `required-steps.md` clean but the worked-example row still rendering — because the round that verified it used a DELTA scope that did not reach that hunk.

## Candidate rule

A retirement sweep's population is every document in the skill that names the retired identity, derived by content sweep, not the subset the change happened to touch. And a verification pass scoped to the delta cannot certify a whole-surface claim — when the claim is "the identity is gone everywhere", the verification must be whole-surface too.
